"""Average eval predictions over an ensemble of fitted models, dropping members that are
locally unstable along their own eval trajectory. Usage: ensemble.py out.npy fit1.npz fit2.npz ..."""
import numpy as np, sys
from ssn import *
out = sys.argv[1]; fits = sys.argv[2:]
# optional per-member weight: "file.npz:0.25" (defaults 1). Weights of kept members are renormalised.
weights = [float(f.split(':')[1]) if ':' in f else 1.0 for f in fits]
fits = [f.split(':')[0] for f in fits]
def maxre(W, r, I, step=100):
    worst = -np.inf
    for s in range(0, I.shape[1], step):
        u = np.maximum(W @ r[:, s] + I[:, s], 0.0)
        Jm = (-np.eye(N) + (K*NPOW*u)[:, None]*W)/TAU
        worst = max(worst, np.linalg.eigvals(Jm).real.max())
    return worst
keep = []; kw = []
for f, w in zip(fits, weights):
    d = np.load(f); W = d['W']; r0 = np.exp(float(d['logr0']))*np.ones(N)
    r_ev = simulate_np(W, I_ev, r0); r_tr = simulate_np(W, I_tr, r0)
    ok = np.isfinite(r_ev).all()
    mre = maxre(W, r_ev, I_ev) if ok else np.inf
    rm = np.sqrt(((r_tr[:, ::STRIDE]-r_obs)**2).mean())
    print(f'{f}: train rmse {rm:.4f} | eval max {r_ev.max() if ok else np.nan:.3f} mean {r_ev.mean() if ok else np.nan:.4f} maxRe(J) eval {mre:.3f}', end='')
    if ok and mre < 0.0:
        keep.append(r_ev); kw.append(w); print('  KEEP')
    else:
        print('  DROP')
P = np.array(keep); kw = np.array(kw)/np.sum(kw); mean = np.tensordot(kw, P, axes=1)
print('weights', kw.round(4))
for i, p in enumerate(P):
    print(f'member {i}: nrmse vs ensemble mean {np.sqrt(((p-mean)**2).mean())/mean.std():.3f}')
print('ensemble of', len(keep), 'members; mean pred: max %.3f mean %.4f std %.4f' % (mean.max(), mean.mean(), mean.std()))
np.save(out, np.clip(mean, 0, None))
print('saved', out)
