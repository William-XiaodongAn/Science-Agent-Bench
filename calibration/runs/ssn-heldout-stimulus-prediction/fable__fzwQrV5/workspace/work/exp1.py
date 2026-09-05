import sys; from fit import *
lam = float(sys.argv[1]); free = sys.argv[2]=='free'
mask = make_mask()
m,h = fit(mask, lam=lam, free_dev=free, iters=200)
R = predict_obs(m); print('train nRMSE (all obs)', nrmse(R, r_obs, mask))
W = m().detach().numpy(); print('spectral radius', np.abs(np.linalg.eigvals(W)).max())
np.save(f'W_exp1_{sys.argv[2]}_{lam}.npy', W); torch.save(m.state_dict(), f'm_exp1_{sys.argv[2]}_{lam}.pt')
Re = simulate_np(W, I_ev); print('eval sim max', Re.max(), 'finite', np.isfinite(Re).all())
