import numpy as np, time, sys
from scipy.optimize import minimize
from sim import simulate, loss_grad
from fit_kernel import W_of_theta, dist2, fixed_point, objective, I, Ie, Y, obs_idx, N, NE, sign
D2=dist2(False); t_obs=np.load('/workspace/data/t_obs.npy')
mode=sys.argv[1]
if mode=='cv':
    tr=obs_idx[t_obs<84]; te=obs_idx[t_obs>=84]; Ytr=Y[:,t_obs<84]; Yte=Y[:,t_obs>=84]
else:
    tr=obs_idx; Ytr=Y; te=None
th0=np.load('theta_kernel_0.npy')
res=minimize(objective, th0, args=(D2,tr,Ytr), jac=True, method='L-BFGS-B', options=dict(maxiter=200))
th=res.x; W0,_=W_of_theta(th,D2); W0=W0.detach().numpy(); A0=np.abs(W0)
mask=1-np.eye(N)
def build(z): return sign*A0*np.exp(np.clip(z,-6,3))*mask
def obj(zf, lam):
    z=zf.reshape(N,N); W=build(z)
    r0=fixed_point(W,I[:,0],1500)
    if not np.isfinite(r0).all() or r0.max()>1e3: return 1e6, np.zeros_like(zf)
    L,dW,r=loss_grad(W,I,tr,Ytr,r0=r0)
    if not np.isfinite(L) or r.max()>1e3: return 1e6, np.zeros_like(zf)
    g=dW*W + 2*lam*z
    return L+lam*(z**2).sum(), g.ravel()
def evaluate(W):
    r0=fixed_point(W,I[:,0]); r=simulate(W,I,r0)
    out={'train_rmse':np.sqrt(((r[:,tr]-Ytr)**2).mean())}
    if te is not None: out['test_rmse']=np.sqrt(((r[:,te]-Yte)**2).mean())
    e=simulate(W,Ie,r0); out['eval_max']=e.max(); out['eval_finite']=bool(np.isfinite(e).all())
    return out,e
print('kernel-only:',evaluate(W0)[0], flush=True)
lams=[float(x) for x in sys.argv[2:]]
for lam in lams:
    t0=time.time()
    r=minimize(obj, np.zeros(N*N), args=(lam,), jac=True, method='L-BFGS-B', options=dict(maxiter=600))
    W=build(r.x.reshape(N,N)); ev,e=evaluate(W)
    print('lam',lam,'nit',r.nit,'z rms %.3f'%r.x.std(),ev,'time %.0f'%(time.time()-t0), flush=True)
    np.save(f'W_mult_{mode}_{lam}.npy',W); np.save(f'eval_mult_{mode}_{lam}.npy',e)
