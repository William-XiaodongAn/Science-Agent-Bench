import numpy as np
from scipy.optimize import least_squares
p='/workspace/data/'
y=np.load(p+'train_r_obs.npy').astype(float); I=np.load(p+'train_I.npy').astype(float); xy=np.load(p+'xy.npy');
N=49; typ=np.arange(N)>=29; DD=np.abs(xy[:,None]-xy[None,:]); D2=(np.minimum(DD,7-DD)**2).sum(2)
obsidx=np.arange(0,12001,200)
# selected times: all, weight response time mean
wt=np.ones(61)

def mkW(q):
    # q amplitudes then widths
    W=np.empty((N,N))
    for a in range(2):
      for b in range(2):
        z=2*a+b; mask=(typ[:,None]==a)&(typ[None,:]==b)
        s=q[4+z]; W[mask]=q[z]*np.exp(-D2[mask]/(2*s*s)) * (-1 if b else 1)
    np.fill_diagonal(W,0)
    return W

def sim(q, retfull=False, drive=I):
 W=mkW(q); rr=np.zeros(N); out=np.zeros((N,61)); oi=1
 for z in range(12000):
   x=W@rr+drive[:,z]
   target=.5*np.maximum(x,0)**2
   rr += .02*(-rr+target)
   rr=np.maximum(rr,0)
   if not np.all(np.isfinite(rr)) or rr.max()>10: return None
   if (z+1)%200==0: out[:,oi]=rr; oi+=1
 return out

def fun(q):
 out=sim(q)
 if out is None: return np.full(y.size,10.)
 return ((out-y)*np.sqrt(wt)[None,:]).ravel()

bounds=([0,0,0,0,.3,.3,.3,.3],[3,3,3,3,5,5,5,5])
starts=[np.array([2,.62,.407,.636,.623,.974,1.506,1.117])]
for x0 in starts:
 res=least_squares(fun,x0,bounds=bounds,verbose=1,max_nfev=300,xtol=1e-8,ftol=1e-9,x_scale='jac')
 out=sim(res.x)
 print('RESULT',res.cost,res.optimality,res.nfev,np.round(res.x,5))
 print('rmse',np.sqrt(np.mean((out-y)**2)),'active',np.sqrt(np.mean((out[:,y.mean(0)>.03]-y[:,y.mean(0)>.03])**2)),'max',out.max())
 print('W stats',mkW(res.x).min(),mkW(res.x).max(),np.linalg.eigvals(mkW(res.x)).real.max(),max(abs(np.linalg.eigvals(mkW(res.x)))))
