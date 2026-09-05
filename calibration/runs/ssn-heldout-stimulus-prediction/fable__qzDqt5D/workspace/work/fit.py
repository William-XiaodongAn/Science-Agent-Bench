import numpy as np, torch, time, sys, argparse, json
from ssn import *
torch.set_num_threads(1)

p = argparse.ArgumentParser()
p.add_argument('--holdout', type=int, default=-1, help='pulse index 0-3 to hold out (-1 none)')
p.add_argument('--iters', type=int, default=400)
p.add_argument('--sub', type=int, default=5)
p.add_argument('--lam', type=float, default=-1, help='L2 weight on log-deviations; <0 -> no deviations')
p.add_argument('--init', type=str, default='')
p.add_argument('--out', type=str, default='fitA.npz')
p.add_argument('--seed', type=int, default=0)
p.add_argument('--lr', type=float, default=0.03)
p.add_argument('--kernel', type=str, default='gauss')
args = p.parse_args()
torch.manual_seed(args.seed); np.random.seed(args.seed)

# pulses: centre times 15, 43, 70, 98 -> hold out windows of obs columns
pulse_windows = [(8, 22), (36, 50), (60, 80), (90, 106)]
mask = np.ones((N, len(t_obs)), bool)
if args.holdout >= 0:
    a, b = pulse_windows[args.holdout]
    mask[:, (t_obs >= a) & (t_obs <= b)] = False
mask_t = torch.tensor(mask)
obs = torch.tensor(r_obs); I = torch.tensor(I_tr)
Dt = torch.tensor(Dmat); sgn = torch.tensor(sign)
typ = torch.tensor((~isE).astype(int))  # 0=E,1=I
offdiag = 1.0 - torch.eye(N)

class Model(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.logJ = torch.nn.Parameter(torch.log(torch.full((2, 2), 0.3)) + 0.3*torch.randn(2, 2))
        self.logsig = torch.nn.Parameter(torch.zeros(2, 2) + 0.2*torch.randn(2, 2))
        self.delta = torch.nn.Parameter(torch.zeros(N, N))
        self.logr0 = torch.nn.Parameter(torch.tensor(np.log(0.005)))
        self.lognoise = torch.nn.Parameter(torch.tensor(np.log(0.02)))
    def W(self, use_delta=True):
        J = torch.exp(self.logJ)[typ[:, None], typ[None, :]]
        sig = torch.exp(self.logsig)[typ[:, None], typ[None, :]]
        if args.kernel == 'gauss':
            ker = torch.exp(-Dt**2/(2*sig**2))
        else:
            ker = torch.exp(-Dt/sig)
        W = J*ker
        if use_delta:
            W = W*torch.exp(self.delta)
        return W*sgn[None, :]*offdiag
    def forward(self, Iin, sub=1, use_delta=True, obs_only=True):
        r0 = torch.exp(self.logr0)*torch.ones(N)
        return simulate(self.W(use_delta), Iin, r0, sub=sub, obs_only=obs_only)

m = Model()
if args.init:
    sd = np.load(args.init)
    with torch.no_grad():
        for k_ in ['logJ', 'logsig', 'logr0', 'lognoise']:
            getattr(m, k_).copy_(torch.tensor(sd[k_]))
        if 'delta' in sd and args.lam >= 0:
            m.delta.copy_(torch.tensor(sd['delta']))
use_delta = args.lam >= 0
params = [m.logJ, m.logsig, m.logr0, m.lognoise] + ([m.delta] if use_delta else [])
opt = torch.optim.Adam(params, lr=args.lr)
t0 = time.time()
for it in range(args.iters):
    opt.zero_grad()
    pred = m(I, sub=args.sub, use_delta=use_delta)
    sigma = torch.exp(m.lognoise)
    nll = tobit_nll(pred[mask_t], obs[mask_t], sigma)
    pen = args.lam*(m.delta**2).sum() if use_delta else torch.tensor(0.0)
    loss = nll + pen
    if not torch.isfinite(loss):
        print('non-finite loss; stopping'); break
    loss.backward()
    torch.nn.utils.clip_grad_norm_(params, 10.0)
    opt.step()
    if it % 25 == 0 or it == args.iters-1:
        with torch.no_grad():
            rm = np.sqrt(((pred - obs)**2)[mask_t].mean().item())
            ho = np.sqrt(((pred - obs)**2)[~mask_t].mean().item()) if args.holdout >= 0 else float('nan')
        print(f'it {it} loss {loss.item():.2f} nll {nll.item():.2f} pen {pen.item():.2f} rmse_fit {rm:.4f} rmse_holdout {ho:.4f} '
              f'J {np.exp(m.logJ.detach().numpy()).round(3).tolist()} sig {np.exp(m.logsig.detach().numpy()).round(3).tolist()} '
              f'r0 {np.exp(m.logr0.item()):.4f} noise {sigma.item():.4f} t {time.time()-t0:.0f}s', flush=True)
W = m.W(use_delta).detach().numpy()
ev = np.linalg.eigvals(W)
print('spectral radius of W', np.abs(ev).max())
np.savez(args.out, W=W, logJ=m.logJ.detach().numpy(), logsig=m.logsig.detach().numpy(), delta=m.delta.detach().numpy(),
         logr0=m.logr0.item(), lognoise=m.lognoise.item(), holdout=args.holdout, lam=args.lam)
