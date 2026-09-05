import numpy as np,time
from scipy.optimize import least_squares
p='/workspace/data/';y=np.load(p+'train_r_obs.npy').astype(float);I=np.load(p+'train_I.npy').astype(float);xy=np.load(p+'xy.npy');N=49;typ=np.arange(N)>=29;D2=((xy[:,None]-xy[None,:])**2).sum(2)
q=np.load('/workspace/work/q_refit3.npy')
B=np.zeros((N,N))
for a in range(2):
 for b in range(2):
  z=2*a+b;m=(typ[:,None]==a)&(typ[None,:]==b);B[m]=q[z]*np.exp(-D2[m]/(2*q[4+z]**2))*(-1 if b else 1)
np.fill_diagonal(B,0)
# base model activity identifies observable presynaptic columns
r=np.zeros(N);mx=np.zeros(N)
for z in range(12000):
 r+=.02*(-r+.5*np.maximum(B@r+I[:,z],0)**2);r=np.maximum(r,0);mx=np.maximum(mx,r)
# subtract approximate baseline, normalize separately by population
pcol=np.maximum(mx-.015,0)
for b in [False,True]:pcol[typ==b]/=pcol[typ==b].max()
print('pcol',np.round(pcol,2))
BE=B.copy();BE[:,typ]=0; BI=B.copy();BI[:,~typ]=0
def sim(g):
 # learned correction tapers with source observability
 W=BE*(1+(g[:N,None]-1)*pcol[None,:])+BI*(1+(g[N:,None]-1)*pcol[None,:])
 r=np.zeros(N);o=np.zeros((N,61));oi=1
 for z in range(12000):
  r+=.02*(-r+.5*np.maximum(W@r+I[:,z],0)**2);r=np.maximum(r,0)
  if r.max()>10:return None
  if (z+1)%200==0:o[:,oi]=r;oi+=1
 return o
for lam in [.03,.01]:
 def fn(g):
  o=sim(g)
  if o is None:return np.full(y.size+2*N,10.)
  return np.r_[(o-y).ravel(),np.sqrt(lam)*(g-1)]
 st=time.time();res=least_squares(fn,np.ones(2*N),bounds=(.01,4),max_nfev=20,ftol=2e-8,xtol=1e-7)
 o=sim(res.x);np.save('/workspace/work/localgain_'+str(lam)+'.npy',res.x);np.save('/workspace/work/pcol.npy',pcol)
 print(lam,time.time()-st,res.nfev,np.sqrt(np.mean((o-y)**2)),res.cost,res.x.std(),res.x.min(),res.x.max(),flush=True)
