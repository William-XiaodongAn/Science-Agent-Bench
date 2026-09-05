import sys; from fit import *
lam = float(sys.argv[1]); free = sys.argv[2]=='free'; eg = sys.argv[3]=='guard'
mask = make_mask()
m,h = fit(mask, lam=lam, free_dev=free, iters=200, eval_guard=eg)
R = predict_obs(m); print('train nRMSE (all obs)', nrmse(R, r_obs, mask), 'peak', nrmse(R, r_obs, mask*(r_obs>0.1)))
W = m().detach().numpy(); print('spectral radius', np.abs(np.linalg.eigvals(W)).max(), 'dev rms', m.dev.detach().numpy().std())
tag=f'{sys.argv[2]}_{lam}_{sys.argv[3]}'; np.save(f'W_exp2_{tag}.npy', W); torch.save(m.state_dict(), f'm_exp2_{tag}.pt')
Re = simulate_np(W, I_ev); print('eval sim max', np.nanmax(Re), 'finite', np.isfinite(Re).all(), 'mean', np.nanmean(Re))
