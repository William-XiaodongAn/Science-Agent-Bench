import numpy as np,time
from scipy.optimize import least_squares
p='/workspace/data/';y=np.load(p+'train_r_obs.npy').astype(float);I=np.load(p+'train_I.npy').astype(float);xy=np.load(p+'xy.npy');N=49;typ=np.arange(N)>=29;D2=((xy[:,None]-xy[None,:])**2).sum(2)
q=np.load('/workspace/work/q_refit3.npy');pcol=np.load('/workspace/work/pcol.npy')
B=np.zeros((N,N))
for a in range(2):
 for b in range(2):
  z=2*a+b;m=(typ[:,None]==a)&(typ[None,:]==b);B[m]=q[z]*np.exp(-D2[m]/(2*q[4+z]**2))*(-1 if b else 1)
np.fill_diagonal(B,0); BE=B.copy();BE[:,typ]=0; BI=B.copy();BI[:,~typ]=0
def matrix(g):
 ge,gi,le,li=g[:N],g[N:2*N],g[2*N:3*N],g[3*N:]
 return BE*ge[:,None]*(1+(le[:,None]-1)*pcol[None,:])+BI*gi[:,None]*(1+(li[:,None]-1)*pcol[None,:])
def sim(g):
 W=matrix(g);r=np.zeros(N);o=np.zeros((N,61));oi=1
 for z in range(12000):
  r+=.02*(-r+.5*np.maximum(W@r+I[:,z],0)**2);r=np.maximum(r,0)
  if r.max()>10:return None
  if (z+1)%200==0:o[:,oi]=r;oi+=1
 return o
# penalties validated separately
lg=.05; ll=.015
def fn(g):
 o=sim(g)
 if o is None:return np.full(y.size+4*N,10.)
 return np.r_[(o-y).ravel(),np.sqrt(lg)*(g[:2*N]-1),np.sqrt(ll)*(g[2*N:]-1)]
st=time.time();res=least_squares(fn,np.ones(4*N),bounds=(.1,3),max_nfev=12,ftol=2e-8,xtol=1e-7,verbose=1)
o=sim(res.x);np.save('/workspace/work/combined.npy',res.x)
print('time',time.time()-st,'nfev',res.nfev,'rmse',np.sqrt(np.mean((o-y)**2)),'cost',res.cost,'sd',*[res.x[j*N:(j+1)*N].std() for j in range(4)])
