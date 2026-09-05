import numpy as np,time
from scipy.optimize import minimize
from scipy.special import log_ndtr
import compare_models as c

SIG=.020
Y=c.R
def nll(p,variant='plain',step=2,cols=None,reg=1e-3):
 P=c.sim(c.Wmake(p,variant),step)
 if P is None:return 1e5
 if cols is not None:P=P[:,cols]; y=Y[:,cols]
 else:y=Y
 pos=y>0
 ll=np.empty_like(y)
 ll[pos]=-.5*((y[pos]-P[pos])/SIG)**2-np.log(SIG)-.5*np.log(2*np.pi)
 ll[~pos]=log_ndtr(-P[~pos]/SIG)
 # mean NLL; weak penalty on actual matrix, to select stable member
 W=c.Wmake(p,variant)
 return -ll.mean()+reg*np.mean(W*W)

if __name__=='__main__':
 starts=[np.load('/tmp/p.npy'),np.load('/tmp/plain_p.npy')]
 # plus sensible starts in terms of J and sig
 for sig in [.5,.75,1.,1.5]:starts.append(np.log([3,.8,3,2,sig,sig,sig,sig]))
 for reg in [0,1e-3,1e-2]:
  best=None
  for si,p in enumerate(starts):
   st=time.time();z=minimize(lambda x:nll(x,'plain',2,reg=reg),p,method='Nelder-Mead',options={'maxiter':350,'fatol':2e-5,'xatol':2e-3})
   print('reg',reg,'start',si,z.fun,np.exp(z.x),'sec',time.time()-st,flush=True)
   if best is None or z.fun<best.fun:best=z
  z=minimize(lambda x:nll(x,'plain',1,reg=reg),best.x,method='Nelder-Mead',options={'maxiter':250,'fatol':2e-6,'xatol':3e-4})
  print('BEST',reg,z.fun,np.exp(z.x),flush=True)
  np.save(f'/tmp/lik_p_{reg}.npy',z.x);np.save(f'/tmp/lik_W_{reg}.npy',c.Wmake(z.x,'plain'))
