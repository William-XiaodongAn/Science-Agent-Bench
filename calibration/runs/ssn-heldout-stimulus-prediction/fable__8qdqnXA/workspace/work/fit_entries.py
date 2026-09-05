import numpy as np, torch, time, sys
from scipy.optimize import minimize
from sim import simulate, loss_grad
from fit_kernel import W_of_theta, dist2, fixed_point, objective, I, Ie, Y, obs_idx, N, NE, sign
periodic=0; D2=dist2(False)
t_obs=np.load('/workspace/data/t_obs.npy')
mode=sys.argv[1]  # 'cv' or 'full'
if mode=='cv':
    tr=obs_idx[t_obs<84]; te=obs_idx[t_obs>=84]; Ytr=Y[:,t_obs<84]; Yte=Y[:,t_obs>=84]
else:
    tr=obs_idx; Ytr=Y; te=None
# kernel fit on training portion
th0=np.load('theta_kernel_0.npy')
res=minimize(objective, th0, args=(D2,tr,Ytr), jac=True, method='L-BFGS-B', options=dict(maxiter=200))
th=res.x; W0,_=W_of_theta(th,D2); W0=W0.detach().numpy(); A0=np.abs(W0)
mask=1-np.eye(N)
def build(delta): return sign*np.maximum(A0+delta,0)*mask
def obj(d, lam):
    delta=d.reshape(N,N); W=build(delta)
    r0=fixed_point(W,I[:,0],1500)
    if not np.isfinite(r0).all() or r0.max()>1e3: return 1e6, np.zeros_like(d)
    L,dW,r=loss_grad(W,I,tr,Ytr,r0=r0)
    if not np.isfinite(L) or r.max()>1e3: return 1e6, np.zeros_like(d)
    g=dW*sign*((A0+delta)>0)*mask + 2*lam*delta
    return L+lam*(delta**2).sum(), g.ravel()
def evaluate(W):
    r0=fixed_point(W,I[:,0]); r=simulate(W,I,r0)
    out={'train_rmse':np.sqrt(((r[:,tr]-Ytr)**2).mean())}
    if te is not None: out['test_rmse']=np.sqrt(((r[:,te]-Yte)**2).mean())
    e=simulate(W,Ie,r0); out['eval_max']=e.max(); out['eval_finite']=bool(np.isfinite(e).all())
    return out,e
print('kernel-only:',evaluate(W0)[0], flush=True)
lams=[float(x) for x in sys.argv[2:]] if len(sys.argv)>2 else [0.02,0.1,0.5,2.0]
for lam in lams:
    t0=time.time()
    r=minimize(obj, np.zeros(N*N), args=(lam,), jac=True, method='L-BFGS-B', options=dict(maxiter=400))
    W=build(r.x.reshape(N,N)); ev,e=evaluate(W)
    print('lam',lam,'nit',r.nit,'|delta| rms %.4f'%r.x.std(),ev,'time %.0f'%(time.time()-t0), flush=True)
    np.save(f'W_entries_{mode}_{lam}.npy',W); np.save(f'eval_entries_{mode}_{lam}.npy',e)
