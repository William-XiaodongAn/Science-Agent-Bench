import numpy as np, time
from scipy.optimize import minimize
from scipy.special import ndtr

R=np.load('data/train_r_obs.npy').astype(float); I=np.load('data/train_I.npy').astype(float)
xy=np.load('data/xy.npy'); typ=np.r_[np.zeros(29,int),np.ones(20,int)]
dx=xy[:,None,0]-xy[None,:,0];dy=xy[:,None,1]-xy[None,:,1]
SIG=.026
def om(x):
 z=x/SIG;return x*ndtr(z)+SIG/np.sqrt(2*np.pi)*np.exp(-z*z/2)

def Wmake(p,variant):
 J=np.exp(p[:4]).reshape(2,2); sig=np.exp(p[4:8]).reshape(2,2)
 dd=dx*dx+dy*dy
 if 'torus' in variant:
  dd=np.minimum(abs(dx),7-abs(dx))**2+np.minimum(abs(dy),7-abs(dy))**2
 S=np.empty((49,49))
 for a in range(2):
  for b in range(2):
   ix=np.ix_(typ==a,typ==b)
   if 'expdist' in variant:S[ix]=np.exp(-np.sqrt(dd[ix])/sig[a,b])
   else:S[ix]=np.exp(-dd[ix]/(2*sig[a,b]**2))
   if 'rownorm' in variant:
    # normalize each postsynaptic row within this presyn population
    ss=S[ix]; S[ix]=ss/ss.sum(1,keepdims=True)
   elif 'colnorm' in variant:
    ss=S[ix]; S[ix]=ss/ss.sum(0,keepdims=True)
 W=J[typ[:,None],typ[None,:]]*S;W[:,typ==1]*=-1;np.fill_diagonal(W,0)
 return W

def sim(W,step=2,cols=None):
 r=np.zeros(49);out=np.empty((49,61));out[:,0]=r;qi=1;h=.02*step # dt*step/tau
 for q in range(step,12001,step):
  r += h*(-r+.5*np.maximum(W@r+I[:,q],0)**2)
  if not np.isfinite(r).all() or r.max()>10:return None
  if q%200==0:out[:,qi]=r;qi+=1
 return out

def obj(p,v,step=2,cols=None):
 P=sim(Wmake(p,v),step)
 if P is None:return 100
 if cols is None:cols=np.arange(61)
 return np.mean((om(P[:,cols])-R[:,cols])**2)+1e-7*np.mean(np.exp(p[:4])**2)

if __name__=='__main__':
 p0=np.load('/tmp/p.npy')
 variants=['plain','rownorm','colnorm','torus','expdist','expdist_rownorm']
 for v in variants:
  # normalization changes magnitude, compensate approximate count
  pp=p0.copy()
  if 'norm' in v: pp[:4]+=np.log([3,2,3,2])
  if 'expdist' in v:pp[4:8]-=.3
  st=time.time()
  z=minimize(lambda p:obj(p,v,step=2),pp,method='Nelder-Mead',options={'maxiter':350,'fatol':2e-10,'xatol':2e-3})
  z2=minimize(lambda p:obj(p,v,step=1),z.x,method='Nelder-Mead',options={'maxiter':180,'fatol':1e-11,'xatol':3e-4})
  print(v,z2.fun,np.exp(z2.x),'success',z2.success,'sec',time.time()-st,flush=True)
  np.save('/tmp/'+v+'_p.npy',z2.x);np.save('/tmp/'+v+'_W.npy',Wmake(z2.x,v))
