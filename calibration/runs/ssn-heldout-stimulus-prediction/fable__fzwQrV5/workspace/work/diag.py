from fit import *
np.set_printoptions(linewidth=220, precision=3, suppress=True)
rng = np.random.RandomState(0); perm = rng.permutation(N); held = perm[2::3]
m, h = fit(make_mask(hold_neurons=held), lam=0, free_dev=False, iters=120, verbose=True)
R = predict_obs(m); R0 = simulate_np(np.zeros((N,N)), I_tr, r0=np.full(N,0.01))[:, ::200]
d = np.linalg.norm(xy-xy[40],axis=1)
print('held neurons:', sorted(held))
for i in sorted(held, key=lambda i: d[i]):
    cols=[7,8,21,35,49]
    print(i, 'E' if i<29 else 'I', 'd=%.2f'%d[i], 'obs', r_obs[i,cols], 'struct', R[i,cols], 'ff', R0[i,cols])
W = m().detach().numpy(); np.save('W_diag_fold2.npy', W)
