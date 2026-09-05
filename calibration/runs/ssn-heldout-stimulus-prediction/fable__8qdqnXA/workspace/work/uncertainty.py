import numpy as np, torch, sys
from sim import simulate
from fit_kernel import W_of_theta, dist2, fixed_point, I, Ie, Y, obs_idx, N
rng=np.random.default_rng(1)
for periodic in [0,1]:
    th=np.load(f'theta_kernel_{periodic}.npy'); D2=dist2(bool(periodic))
    def pred(theta):
        W,_=W_of_theta(theta,D2); Wn=W.detach().numpy(); r0=fixed_point(Wn,I[:,0],1500)
        return simulate(Wn,I,r0)[:,obs_idx].ravel(), Wn, r0
    p0,Wn,r0=pred(th); res=Y.ravel()-p0; s2=(res**2).mean()
    Jm=np.zeros((p0.size,8)); eps=1e-4
    for j in range(8):
        t2=th.copy(); t2[j]+=eps; Jm[:,j]=(pred(t2)[0]-p0)/eps
    H=Jm.T@Jm/s2; C=np.linalg.inv(H); sd=np.sqrt(np.diag(C))
    print('periodic',periodic,'theta',th.round(3)); print(' post sd (log units)',sd.round(3))
    print(' J', np.exp(th[:4]).round(3),' sigma',np.exp(th[4:]).round(3))
    ev0=simulate(Wn,Ie,r0)
    preds=[]
    for s in range(12):
        ts=rng.multivariate_normal(th,C)
        W,_=W_of_theta(ts,D2); Ws=W.detach().numpy(); r0s=fixed_point(Ws,I[:,0],1500)
        e=simulate(Ws,Ie,r0s)
        if np.isfinite(e).all() and e.max()<50: preds.append(e)
        else: print('  sample diverged')
    preds=np.array(preds)
    sd_ev=np.sqrt(((preds-ev0[None])**2).mean(0))
    print(' eval: std of true-like traj %.4f ; rms spread of posterior samples %.4f ; nRMSE-equivalent %.3f'%(ev0.std(), sd_ev.mean(), np.sqrt((sd_ev**2).mean())/ev0.std()))
    print(' eval max over samples',preds.max(axis=(1,2)).round(3))
    np.save(f'eval_kernel_{periodic}.npy',ev0)
e0=np.load('eval_kernel_0.npy'); e1=np.load('eval_kernel_1.npy')
print('open vs periodic eval difference nRMSE-equiv',np.sqrt(((e0-e1)**2).mean())/e0.std())
