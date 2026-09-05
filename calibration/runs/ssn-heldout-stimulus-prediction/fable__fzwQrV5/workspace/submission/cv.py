"""Cross-validation: hold out one pulse window or a set of neurons; compare lam values and structured-only."""
import sys; from fit import *
mode = sys.argv[1]; lam = float(sys.argv[2]); free = sys.argv[3]=='free'; iters = int(sys.argv[4]) if len(sys.argv)>4 else 120
rng = np.random.RandomState(0)
res = []
if mode == 'pulse':
    folds = [(make_mask(hold_pulse=p), 1-make_mask(hold_pulse=p)) for p in (1,3,4)]
else:  # neuron holdout: 3 folds of ~16 neurons, test mask = held neurons during all pulses
    perm = rng.permutation(N); folds = []
    for f in range(3):
        held = perm[f::3]; m = make_mask(hold_neurons=held); tm = np.zeros((N,61)); tm[held,1:] = 1; folds.append((m, tm))
for (m, tm) in folds:
    mod, h = fit(m, lam=lam, free_dev=free, iters=iters, verbose=False)
    R = predict_obs(mod); res.append(nrmse(R, r_obs, tm))
    # peak region on held-out: obs > 0.1
    pk = tm*(r_obs>0.1); res.append(nrmse(R, r_obs, pk) if pk.sum()>0 else np.nan)
print(f'{mode} lam={lam} free={free}: fold nRMSE (all, peak) = {np.round(res,3)}  mean all={np.mean(res[0::2]):.3f} mean peak={np.nanmean(res[1::2]):.3f}', flush=True)
