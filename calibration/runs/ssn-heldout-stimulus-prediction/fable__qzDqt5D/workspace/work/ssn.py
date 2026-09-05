import numpy as np, torch, json, time
torch.set_num_threads(4)
torch.set_default_dtype(torch.float64)
D = '/workspace/data/'
C = json.load(open(D+'constants.json'))
TAU, K, NPOW, DT = C['tau'], C['k'], C['n'], C['dt']
NE, N = C['NE'], C['N']
r_obs = np.load(D+'train_r_obs.npy').astype(np.float64)
I_tr = np.load(D+'train_I.npy').astype(np.float64)
I_ev = np.load(D+'eval_I.npy').astype(np.float64)
t = np.load(D+'t.npy'); t_obs = np.load(D+'t_obs.npy'); xy = np.load(D+'xy.npy').astype(np.float64)
STRIDE = C['stride']
sign = np.ones(N); sign[NE:] = -1.0          # column signs (Dale)
isE = np.zeros(N, bool); isE[:NE] = True
Dmat = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=2)

def simulate(W, I, r0, dt=DT, sub=1, obs_only=True, stride=STRIDE):
    """W: (N,N) torch, I: (N,T) torch, r0: (N,) torch. Forward Euler, rates clipped at 0.
    sub: integrate with dt*sub using every sub-th drive sample (for fast fitting)."""
    T = I.shape[1]
    h = dt*sub
    r = r0.clone()
    outs = [r]
    steps = (T-1)//sub
    for s in range(steps):
        Iin = I[:, s*sub]
        u = torch.clamp(W @ r + Iin, min=0.0)
        rss = K*u**NPOW
        r = torch.clamp(r + (h/TAU)*(-r + rss), min=0.0)
        if obs_only:
            if ((s+1)*sub) % stride == 0:
                outs.append(r)
        else:
            outs.append(r)
    return torch.stack(outs, 1)

def simulate_np(W, I, r0, dt=DT):
    T = I.shape[1]; r = r0.copy(); out = np.empty((N, T)); out[:, 0] = r
    for s in range(T-1):
        u = np.maximum(W @ r + I[:, s], 0.0)
        r = np.maximum(r + (dt/TAU)*(-r + K*u**NPOW), 0.0)
        out[:, s+1] = r
    return out

def tobit_nll(pred, obs, sigma):
    sigma = torch.as_tensor(sigma)
    """Censored-at-zero Gaussian NLL, summed."""
    z = (pred - obs)/sigma
    normal = torch.distributions.Normal(0.0, 1.0)
    ll_pos = -0.5*z**2 - torch.log(sigma) - 0.5*np.log(2*np.pi)
    ll_zero = normal.cdf(-pred/sigma).clamp_min(1e-12).log()
    ll = torch.where(obs > 0, ll_pos, ll_zero)
    return -ll.sum()

if __name__ == '__main__':
    W = torch.zeros(N, N, requires_grad=True)
    I = torch.tensor(I_tr); r0 = torch.zeros(N)
    for sub in [1, 5]:
        t0 = time.time(); out = simulate(W, I, r0, sub=sub); l = (out**2).sum(); l.backward(); print('sub', sub, 'fwd+bwd', time.time()-t0, out.shape)
    # drive-only prediction quality vs obs
    out = simulate(W.detach(), I, r0).numpy()
    print('drive-only rmse vs obs', np.sqrt(((out - r_obs)**2).mean()), 'obs std', r_obs.std())
