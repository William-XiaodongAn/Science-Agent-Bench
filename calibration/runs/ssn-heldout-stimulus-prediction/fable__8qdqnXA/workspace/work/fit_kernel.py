import numpy as np, torch, time, sys, os
TOBIT_K=0.019 if os.environ.get('TOBIT','0')=='1' else None
from scipy.optimize import minimize
from sim import simulate, loss_grad, a, k
I=np.load('/workspace/data/train_I.npy').astype(float)
Ie=np.load('/workspace/data/eval_I.npy').astype(float)
Y=np.load('/workspace/data/train_r_obs.npy').astype(float)
xy=np.load('/workspace/data/xy.npy').astype(float)
N=49; NE=29
obs_idx=np.arange(0,12001,200)
typ=np.array([0]*NE+[1]*(N-NE))
def dist2(periodic):
    d=xy[:,None,:]-xy[None,:,:]
    if periodic: d=(d+3.5)%7-3.5
    return (d**2).sum(-1)
sign=np.where(typ==0,1.0,-1.0)[None,:]  # column sign
def W_of_theta(theta, D2):
    # theta: logJ (2x2 by [post,pre]), log sigma (2x2)
    th=torch.as_tensor(theta,dtype=torch.float64).requires_grad_(True)
    J=torch.exp(th[:4]).reshape(2,2); S=torch.exp(th[4:8]).reshape(2,2)
    Jm=J[typ][:,typ]; Sm=S[typ][:,typ]
    D2t=torch.as_tensor(D2)
    W=Jm*torch.exp(-D2t/(2*Sm**2))*torch.as_tensor(sign)
    W=W*(1-torch.eye(N,dtype=torch.float64))
    return W, th
def fixed_point(W, Ib, iters=4000):
    r=np.full(N,0.016)
    for _ in range(iters):
        u=W@r+Ib; r=(1-a)*r+a*k*np.maximum(u,0)**2
    return r
def objective(theta, D2, idx, Yfit):
    W,th=W_of_theta(theta,D2); Wn=W.detach().numpy()
    if np.abs(Wn).max()>50: return 1e6, np.zeros_like(theta)
    r0=fixed_point(Wn, I[:,0], 1500)
    if not np.isfinite(r0).all() or r0.max()>1e3: return 1e6, np.zeros_like(theta)
    L,dW,r=loss_grad(Wn,I,idx,Yfit,r0=r0,tobit_sigma=TOBIT_K)
    if not np.isfinite(L) or r.max()>1e3: return 1e6, np.zeros_like(theta)
    W.backward(torch.as_tensor(dW))
    return L, th.grad.numpy().copy()
if __name__=='__main__':
    for periodic in [False, True]:
        D2=dist2(periodic)
        best=None
        for init in [np.array([np.log(0.3),np.log(0.3),np.log(0.3),np.log(0.3),0,0,0,0]),
                     np.array([np.log(0.1),np.log(0.2),np.log(0.2),np.log(0.1),np.log(1.5),np.log(1.5),np.log(1.5),np.log(1.5)]),
                     np.array([np.log(0.5),np.log(0.6),np.log(0.6),np.log(0.4),np.log(0.7),np.log(0.7),np.log(0.7),np.log(0.7)])]:
            t0=time.time()
            res=minimize(objective, init, args=(D2,obs_idx,Y), jac=True, method='L-BFGS-B', options=dict(maxiter=300))
            print('periodic',periodic,'init',init[:1].round(2),'loss',res.fun,'nit',res.nit,'time',time.time()-t0)
            if best is None or res.fun<best.fun: best=res
        th=best.x; print(' J=',np.exp(th[:4]).reshape(2,2).round(4),' sigma=',np.exp(th[4:]).reshape(2,2).round(3))
        np.save(f'theta_kernel_{int(periodic)}.npy',th)
        W,_=W_of_theta(th,D2); Wn=W.detach().numpy()
        r0=fixed_point(Wn,I[:,0]); r=simulate(Wn,I,r0)
        resid=r[:,obs_idx]-Y; print(' rmse fit',np.sqrt((resid**2).mean()),' resid std at rest cols', resid.std())
        re=simulate(Wn,Ie,r0); print(' eval max',re.max(),' finite',np.isfinite(re).all(), 'r0 mean',r0.mean())
        # Jacobian spectral radius at rest
        Jac=(-np.eye(N)+ (2*k*np.maximum(Wn@r0+I[:,0],0))[:,None]*Wn)/0.5
        print(' max real eig of Jacobian at rest',np.max(np.linalg.eigvals(Jac).real))
