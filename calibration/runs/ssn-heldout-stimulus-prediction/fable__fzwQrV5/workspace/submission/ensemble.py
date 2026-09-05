"""Assemble the final prediction: average eval simulations of all stable ensemble members (full-data fits at 3 lambdas + bagged fits)."""
import glob; from fit import *
members = []
for f in sorted(glob.glob('W_final*.npy')) + sorted(glob.glob('W_bag*.npy')):
    W = np.load(f); Re = simulate_np(W, I_ev, r0=np.full(N,0.01))
    ok = np.isfinite(Re).all() and Re.max() < 1.5
    print(f, 'eval max %.3f' % np.nanmax(Re), 'ok', ok)
    if ok: members.append(Re)
M = np.array(members); R = M.mean(0)
print('members', len(members), 'ensemble max', R.max(), 'mean', R.mean())
print('between-member spread: rms std %.4f, relative to ensemble std %.3f' % (M.std(0).mean(), M.std(0).mean()/R.std()))
# per-member distance to the ensemble mean, in nRMSE units of the ensemble
for i in range(len(members)): print('  member', i, 'nRMSE vs ensemble %.3f' % (np.sqrt(((M[i]-R)**2).mean())/R.std()))
np.save('/workspace/submission/r_pred.npy', np.clip(R, 0, None).astype(np.float64)); print('wrote r_pred.npy')
