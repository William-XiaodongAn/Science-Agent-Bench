"""Core model: SSN forward simulation (torch, differentiable) and W parametrization."""
import numpy as np, torch, json, math
torch.set_default_dtype(torch.float64)
D = '/workspace/data/'
C = json.load(open(D+'constants.json'))
TAU, K, NPOW, DT = C['tau'], C['k'], C['n'], C['dt']
NE, N = C['NE'], C['N']
xy = np.load(D+'xy.npy'); t = np.load(D+'t.npy'); t_obs = np.load(D+'t_obs.npy')
r_obs = np.load(D+'train_r_obs.npy').astype(np.float64)
I_tr = np.load(D+'train_I.npy').astype(np.float64); I_ev = np.load(D+'eval_I.npy').astype(np.float64)
dist = np.linalg.norm(xy[:,None,:]-xy[None,:,:], axis=2)
isE = np.arange(N) < NE
sign = np.where(isE, 1.0, -1.0)  # column sign (presynaptic type)
# block index: 0=EE(post E,pre E),1=EI(post E, pre I),2=IE(post I, pre E),3=II
blk = (~isE[:,None]).astype(int)*2 + (~isE[None,:]).astype(int)
SIG_OBS = 0.02

def simulate_np(W, I, dt=DT, r0=None, sub=1):
    """Forward Euler at the simulation grid (numpy), returns (N, T) rates. sub: use every sub-th input step with dt*sub."""
    T = I.shape[1]; r = np.zeros(N) if r0 is None else r0.copy(); out = np.empty((N, T)); out[:,0] = r
    a = dt/TAU
    for s in range(1, T):
        u = W @ r + I[:, s-1]
        r = r + a*(-r + K*np.maximum(u, 0)**NPOW)
        r = np.maximum(r, 0.0); out[:, s] = r
    return out

def simulate_torch(W, I, r0, dt, obs_steps):
    """Simulate with torch; I is (N,T) tensor at step size dt; return rates at obs_steps (list of step indices) -> (N, len)."""
    a = dt/TAU; r = r0; outs = {}
    want = set(int(s) for s in obs_steps)
    if 0 in want: outs[0] = r
    T = I.shape[1]
    for s in range(1, T):
        u = W @ r + I[:, s-1]
        r = r + a*(-r + K*torch.clamp(u, min=0)**NPOW)
        r = torch.clamp(r, min=0, max=10.0)
        if s in want: outs[s] = r
    return torch.stack([outs[int(s)] for s in obs_steps], 1)

def expected_clipped(mu, sig=SIG_OBS):
    z = mu/sig
    Phi = 0.5*(1+torch.erf(z/math.sqrt(2))); phi = torch.exp(-0.5*z*z)/math.sqrt(2*math.pi)
    return mu*Phi + sig*phi

class WModel(torch.nn.Module):
    """W_ij = sign_j * w1_ab * exp(-(d_ij^2-1)/(2 sigma_ab^2)) * exp(Dev_ij), zero diagonal. w1 = |weight| at unit distance."""
    def __init__(self, free_dev=True, logw0=(-1.5,-1.5,-1.5,-1.5), s0=(0.0,0.0,0.0,0.0)):
        super().__init__()
        self.logJ = torch.nn.Parameter(torch.tensor(logw0))
        self.logsig = torch.nn.Parameter(torch.tensor(s0))
        self.dev = torch.nn.Parameter(torch.zeros(N, N), requires_grad=free_dev)
        self.register_buffer('d2', torch.tensor(dist**2)); self.register_buffer('blk', torch.tensor(blk))
        self.register_buffer('sign', torch.tensor(sign)); self.register_buffer('offdiag', torch.tensor(1.0-np.eye(N)))
    def sigmas(self): return 0.5 + 3.0*torch.sigmoid(self.logsig)
    def mean(self):
        w1 = torch.exp(self.logJ)[self.blk]; sig = self.sigmas()[self.blk]
        return w1*torch.exp(-(self.d2-1.0)/(2*sig**2))
    def forward(self):
        M = self.mean()*torch.exp(self.dev)
        return M*self.sign[None,:]*self.offdiag
