"""Per-entry W fit around Gaussian-kernel prior, with Dale's law, eval-boundedness barrier.
usage: fit_v2.py <prior:add|mult> <mode:cv|full> lam1 lam2 ..."""
import numpy as np, time, sys, os
from scipy.optimize import minimize
from sim import simulate, loss_grad, a, k
from fit_kernel import W_of_theta, dist2, fixed_point, objective, I, Ie, Y, obs_idx, N, NE, sign
PER=os.environ.get('PERIODIC','0')=='1'
D2=dist2(PER); t_obs=np.load('/workspace/data/t_obs.npy')
prior=sys.argv[1]; mode=sys.argv[2]; lams=[float(x) for x in sys.argv[3:]]
RMAX=1.5; MU=50.0
TOBIT=0.019 if os.environ.get('TOBIT','0')=='1' else None
TAG=('_tobit' if TOBIT else '')+('_per' if PER else '')   # barrier: penalise eval rates above RMAX
mask=1-np.eye(N)
def barrier_grad(W, r0):
    """penalty MU*sum relu(r_eval-RMAX)^2 and its gradient wrt W (adjoint)."""
    T=Ie.shape[1]; r=np.zeros((N,T)); U=np.zeros((N,T-1)); r[:,0]=r0
    for t in range(T-1):
        u=W@r[:,t]+Ie[:,t]; U[:,t]=u; up=np.maximum(u,0); r[:,t+1]=(1-a)*r[:,t]+a*k*up*up
    if not np.isfinite(r).all(): return 1e6, np.zeros((N,N)), r
    ex=np.maximum(r-RMAX,0); P=MU*(ex**2).sum(); G=2*MU*ex
    if P==0: return 0.0, np.zeros((N,N)), r
    lam=np.zeros(N); dW=np.zeros((N,N))
    for t in range(T-2,-1,-1):
        lam=lam+G[:,t+1]; g=lam*(2*k*a*np.maximum(U[:,t],0)); dW+=np.outer(g,r[:,t]); lam=(1-a)*lam+W.T@g
    return P,dW,r
def run(tr,Ytr,te,Yte,lam):
    res=minimize(objective, np.load('theta_kernel_1.npy' if PER else 'theta_kernel_0.npy'), args=(D2,tr,Ytr), jac=True, method='L-BFGS-B', options=dict(maxiter=200))
    W0,_=W_of_theta(res.x,D2); W0=W0.detach().numpy(); A0=np.abs(W0)
    if prior=='add':
        build=lambda p: sign*np.maximum(A0+p,0)*mask
        dWdp=lambda p,W: sign*((A0+p)>0)*mask
    else:
        build=lambda p: sign*A0*np.exp(np.clip(p,-6,3))*mask
        dWdp=lambda p,W: W
    def obj(pf):
        p=pf.reshape(N,N); W=build(p); r0=fixed_point(W,I[:,0],1500)
        if not np.isfinite(r0).all() or r0.max()>1e3: return 1e6, np.zeros_like(pf)
        L,dW,r=loss_grad(W,I,tr,Ytr,r0=r0,tobit_sigma=TOBIT)
        if not np.isfinite(L) or r.max()>1e3: return 1e6, np.zeros_like(pf)
        P,dWb,_=barrier_grad(W,r0)
        if P>=1e6: return 1e6, np.zeros_like(pf)
        g=(dW+dWb)*dWdp(p,W)+2*lam*p
        return L+P+lam*(p**2).sum(), g.ravel()
    r=minimize(obj, np.zeros(N*N), jac=True, method='L-BFGS-B', options=dict(maxiter=500))
    W=build(r.x.reshape(N,N)); r0=fixed_point(W,I[:,0]); rs=simulate(W,I,r0); e=simulate(W,Ie,r0)
    out=dict(nit=r.nit, train=np.sqrt(((rs[:,tr]-Ytr)**2).mean()), eval_max=e.max(), finite=bool(np.isfinite(e).all()))
    if te is not None: out['test']=np.sqrt(((rs[:,te]-Yte)**2).mean())
    return out,W,e,W0
if mode=='cv':
    folds={'p4':(t_obs>=84),'p2':(t_obs>=34)&(t_obs<54)}
    for lam in lams:
        t0=time.time(); tests=[]
        for name,m in folds.items():
            out,W,e,W0=run(obs_idx[~m],Y[:,~m],obs_idx[m],Y[:,m],lam); tests.append(out['test'])
            print(prior,'lam',lam,name,{k_:(round(float(v),5) if not isinstance(v,bool) else v) for k_,v in out.items()},flush=True)
        # kernel-only reference on same folds
        print(prior,'lam',lam,'MEAN test %.5f'%np.mean(tests),'time %.0f'%(time.time()-t0),flush=True)
else:
    for lam in lams:
        t0=time.time(); out,W,e,W0=run(obs_idx,Y,None,None,lam)
        print(prior,'full lam',lam,out,'time %.0f'%(time.time()-t0),flush=True)
        np.save(f'v2_W_{prior}_{lam}{TAG}.npy',W); np.save(f'v2_eval_{prior}_{lam}{TAG}.npy',e); np.save('v2_W0.npy',W0)
