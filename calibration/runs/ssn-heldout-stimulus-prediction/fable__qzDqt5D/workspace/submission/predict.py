"""Produce /workspace/submission/r_pred.npy from a fitted model file (npz with W, logr0)."""
import numpy as np, sys, os
from ssn import *
fit = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else '/workspace/submission/r_pred.npy'
f = np.load(fit); W = f['W']; r0 = np.exp(float(f['logr0']))*np.ones(N)
r_ev = simulate_np(W, I_ev, r0)
r_tr = simulate_np(W, I_tr, r0)
# stability diagnostic: Jacobian (-1 + diag(2 k u) W)/tau along eval trajectory
def maxre(r, I):
    worst = -np.inf
    for s in range(0, I.shape[1], 100):
        u = np.maximum(W @ r[:, s] + I[:, s], 0.0)
        Jm = (-np.eye(N) + (K*NPOW*u)[:, None]*W)/TAU
        worst = max(worst, np.linalg.eigvals(Jm).real.max())
    return worst
print('eval: max rate %.3f mean %.4f std %.4f finite %s' % (r_ev.max(), r_ev.mean(), r_ev.std(), np.isfinite(r_ev).all()))
print('train: max rate %.3f ; rmse vs obs %.4f' % (r_tr.max(), np.sqrt(((r_tr[:, ::STRIDE]-r_obs)**2).mean())))
print('max Re(eig Jacobian) along eval %.3f, along train %.3f (negative = locally stable)' % (maxre(r_ev, I_ev), maxre(r_tr, I_tr)))
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
np.save(out, np.clip(r_ev, 0, None).astype(np.float64))
print('saved', out, r_ev.shape)
