import numpy as np
from scipy.optimize import least_squares
p='/workspace/data/'; y=np.load(p+'train_r_obs.npy').astype(float); I=np.load(p+'train_I.npy').astype(float);xy=np.load(p+'xy.npy');g=np.load('/workspace/work/twogain_alt2_0.03.npy');N=49;typ=np.arange(N)>=29;D2=((xy[:,None]-xy[None,:])**2).sum(2)
def sim(q,retW=False):
 B=np.zeros((N,N))
 for a in range(2):
  for b in range(2):
   z=2*a+b;m=(typ[:,None]==a)&(typ[None,:]==b);B[m]=q[z]*np.exp(-D2[m]/(2*q[4+z]**2))*(-1 if b else 1)
 np.fill_diagonal(B,0); W=g[:N,None]*B*(~typ)[None,:]+g[N:,None]*B*typ[None,:]
 if retW:return W
 r=np.zeros(N);o=np.zeros((N,61));oi=1
 for z in range(12000):
  r+=.02*(-r+.5*np.maximum(W@r+I[:,z],0)**2);r=np.maximum(r,0)
  if r.max()>10:return None
  if (z+1)%200==0:o[:,oi]=r;oi+=1
 return o
def fn(q):
 o=sim(q)
 if o is None:return np.ones(y.size)*10
 return (o-y).ravel()
x=np.array([2,.61597,.40716,.63598,.62286,.97403,1.50573,1.11749])
res=least_squares(fn,x,bounds=([0,0,0,0,.3,.3,.3,.3],[5,3,3,3,4,4,4,4]),max_nfev=100,ftol=1e-9,xtol=1e-8,x_scale='jac',verbose=1)
print(res.x,res.cost,np.sqrt(np.mean(fn(res.x)**2)))
np.save('/workspace/work/q_refit3.npy',res.x)
