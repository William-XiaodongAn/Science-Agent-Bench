import numpy as np,time
from scipy.optimize import minimize
from scipy.special import log_ndtr
import compare_models as c
SIG=.02;Y=c.R
pulses=[np.arange(4,12),np.arange(19,24),np.arange(31,40),np.arange(47,53)]
def score(p,variant,cols,step=2,pen=.001):
 P=c.sim(c.Wmake(p,variant),step)
 if P is None:return 1e5
 y=Y[:,cols];P=P[:,cols];pos=y>0
 ll=np.empty_like(y);ll[pos]=-.5*((y[pos]-P[pos])/SIG)**2-np.log(SIG)-.5*np.log(2*np.pi);ll[~pos]=log_ndtr(-P[~pos]/SIG)
 return -ll.mean()+pen*np.mean(c.Wmake(p,variant)**2)
if __name__=='__main__':
 for v,pfile in [('plain','/tmp/lik_p_0.001.npy'),('colnorm','/tmp/colnorm_p.npy'),('torus','/tmp/torus_p.npy')]:
  p0=np.load(pfile)
  for q,val in enumerate(pulses):
   tr=np.setdiff1d(np.arange(61),val)
   st=time.time();z=minimize(lambda p:score(p,v,tr),p0,method='Nelder-Mead',options={'maxiter':450,'fatol':1e-5,'xatol':1e-3})
   print(v,q,'train',z.fun,'val',score(z.x,v,val,1,0),'pars',np.exp(z.x),'sec',time.time()-st,flush=True)
   np.save(f'/tmp/cv_{v}_{q}.npy',z.x)
