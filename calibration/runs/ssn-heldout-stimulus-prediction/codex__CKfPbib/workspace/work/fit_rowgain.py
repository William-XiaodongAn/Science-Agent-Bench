import numpy as np,time
from scipy.optimize import least_squares
p='/workspace/data/'; y=np.load(p+'train_r_obs.npy').astype(float); I=np.load(p+'train_I.npy').astype(float); xy=np.load(p+'xy.npy');N=49;typ=np.arange(N)>=29;D2=((xy[:,None]-xy[None,:])**2).sum(2)
q=np.array([2,.61597,.40716,.63598,.62286,.97403,1.50573,1.11749])
B=np.zeros((N,N))
for a in range(2):
 for b in range(2):
  z=2*a+b;m=(typ[:,None]==a)&(typ[None,:]==b);B[m]=q[z]*np.exp(-D2[m]/(2*q[4+z]**2))*(-1 if b else 1)
np.fill_diagonal(B,0)
def sim(g):
 W=g[:,None]*B;r=np.zeros(N);o=np.zeros((N,61));oi=1
 for z in range(12000):
  r+=.02*(-r+.5*np.maximum(W@r+I[:,z],0)**2);r=np.maximum(r,0)
  if r.max()>10:return None
  if (z+1)%200==0:o[:,oi]=r;oi+=1
 return o
for lam in [.1,.03,.01,.003]:
 def fn(g):
  o=sim(g)
  if o is None:return np.full(y.size+N,10.)
  return np.r_[(o-y).ravel(),np.sqrt(lam)*(g-1)]
 st=time.time();res=least_squares(fn,np.ones(N),bounds=(.2,2.5),max_nfev=25,ftol=1e-8,xtol=1e-7,verbose=0)
 o=sim(res.x);np.save('/workspace/work/gain_'+str(lam)+'.npy',res.x)
 print(lam,'time',time.time()-st,'nfev',res.nfev,'data rmse',np.sqrt(np.mean((o-y)**2)),'range',res.x.min(),res.x.max(),'sd',res.x.std(),'cost',res.cost)
 print(np.round(res.x,2))
