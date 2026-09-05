"""One bagged fit: per-neuron random (exponential) loss weights, lam given, guard on. Saves W and eval prediction."""
import sys, time; from fit import *
seed = int(sys.argv[1]); lam = float(sys.argv[2]); cap = float(sys.argv[3]) if len(sys.argv)>3 else 2.0
rng = np.random.RandomState(1000+seed); wts = rng.exponential(1.0, N); wts /= wts.mean()
mask = make_mask()*wts[:,None]; t0=time.time()
m,h = fit(mask, lam=lam, free_dev=True, iters=150, eval_guard=True, cap=cap, sub=2, verbose=True, guard_sub=2, margin=1.1)
W = m().detach().numpy(); np.save(f'W_bag2_{seed}_{lam}.npy', W)
Re = simulate_np(W, I_ev, r0=np.full(N,0.01)); np.save(f'Re_bag2_{seed}_{lam}.npy', Re.astype(np.float32))
print('bag', seed, lam, 'train nRMSE (unweighted)', nrmse(predict_obs(m), r_obs, make_mask()), 'eval max', np.nanmax(Re), 'finite', np.isfinite(Re).all(), 'time', time.time()-t0, flush=True)
