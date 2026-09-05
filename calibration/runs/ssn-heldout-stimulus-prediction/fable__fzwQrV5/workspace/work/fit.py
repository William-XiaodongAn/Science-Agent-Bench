"""Fit W by gradient descent through the forward simulation, matching noisy observed rates."""
import numpy as np, torch, time, sys, math
from ssn import *

PULSE_WIN = {1:(4,12), 2:(18,24), 3:(29,41), 4:(46,53)}  # obs-column windows (inclusive) of the four training pulses

def make_mask(hold_pulse=None, hold_neurons=None):
    m = np.ones((N, 61)); m[:,0] = 0  # ignore t=0 (initial transient)
    if hold_pulse is not None:
        a,b = PULSE_WIN[hold_pulse]; m[:, a:b+1] = 0
    if hold_neurons is not None: m[hold_neurons,:] = 0
    return m

def fit(mask, lam=1.0, free_dev=True, sub=2, iters=150, init=None, r0val=0.01, verbose=True, sig=SIG_OBS, seed=0, eval_guard=True, cap=2.0, guard_sub=4, margin=1.0):
    torch.manual_seed(seed)
    m = WModel(free_dev=free_dev) if init is None else init
    I = torch.tensor(I_tr[:, ::sub]); dt = DT*sub; obs = (t_obs/dt).round().astype(int)
    Ie = torch.tensor(0.18 + margin*(I_ev[:, ::guard_sub]-0.18)); dte = DT*guard_sub; obs_e = np.arange(0, Ie.shape[1], 25)
    r0 = torch.full((N,), r0val); Y = torch.tensor(r_obs); Mk = torch.tensor(mask)
    opt = torch.optim.LBFGS(m.parameters(), lr=1, max_iter=iters, history_size=30, line_search_fn='strong_wolfe', tolerance_grad=1e-9, tolerance_change=1e-12)
    hist = []
    def closure():
        opt.zero_grad()
        W = m(); R = simulate_torch(W, I, r0, dt, obs)
        fitl = ((Mk*(expected_clipped(R, sig)-Y))**2).sum()/sig**2/Mk.sum()
        pen = lam*(m.dev**2).sum() if free_dev else torch.zeros(())
        guard = 1e3*torch.clamp(R-cap, min=0).pow(2).sum()
        if eval_guard:
            Re = simulate_torch(W, Ie, r0, dte, obs_e); guard = guard + 1e3*torch.clamp(Re-cap, min=0).pow(2).sum()
        loss = fitl + pen + guard
        loss.backward(); hist.append((fitl.item(), pen.item()))
        return loss
    t0 = time.time(); opt.step(closure)
    if verbose: print(f'  fit done {len(hist)} evals {time.time()-t0:.0f}s  fit={hist[-1][0]:.4f} pen={hist[-1][1]:.4f}  w1={np.exp(m.logJ.detach().numpy()).round(3)} sig={m.sigmas().detach().numpy().round(3)}', flush=True)
    return m, hist

def predict_obs(m, r0val=0.01):
    W = m().detach().numpy(); R = simulate_np(W, I_tr, r0=np.full(N, r0val)); return R[:, ::200]

def nrmse(pred, true, mask):
    e = (pred-true)[mask>0]; return np.sqrt((e**2).mean())/true[mask>0].std()
