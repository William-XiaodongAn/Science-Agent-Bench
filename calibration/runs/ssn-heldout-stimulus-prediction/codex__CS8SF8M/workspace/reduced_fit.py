import numpy as np,time
from scipy.optimize import minimize
from scipy.special import log_ndtr
import compare_models as c
SIG=.02;Y=c.R

def expand(p,mode):
 if mode=='common': return np.r_[p[:4],np.repeat(p[4],4)]
 if mode=='pre': return np.r_[p[:4],p[4],p[5],p[4],p[5]]
 if mode=='post': return np.r_[p[:4],p[4],p[4],p[5],p[5]]
 raise ValueError
def nll(p,mode,cols=None,step=2):
 W=c.Wmake(expand(p,mode),'plain');P=c.sim(W,step)
 if P is None:return 1e5
 if cols is None:cols=np.arange(61)
 y=Y[:,cols];P=P[:,cols];pos=y>0
 ll=np.empty_like(y);ll[pos]=-.5*((y[pos]-P[pos])/SIG)**2-np.log(SIG)-.5*np.log(2*np.pi);ll[~pos]=log_ndtr(-P[~pos]/SIG)
 return -ll.mean()+.001*np.mean(W*W)
if __name__=='__main__':
 p8=np.load('/tmp/lik_p_0.001.npy')
 pulses=[np.arange(4,12),np.arange(19,24),np.arange(31,40),np.arange(47,53)]
 for mode in ['common','pre','post']:
  p=np.log([1,.5,1,1]+([.6] if mode=='common' else [.6,.6]))
  z=minimize(lambda x:nll(x,mode,step=2),p,method='Nelder-Mead',options={'maxiter':600,'fatol':1e-6,'xatol':3e-4})
  z=minimize(lambda x:nll(x,mode,step=1),z.x,method='Nelder-Mead',options={'maxiter':250,'fatol':1e-6,'xatol':2e-4})
  print('FULL',mode,z.fun,np.exp(z.x),flush=True);np.save('/tmp/red_'+mode+'.npy',z.x)
  for qi,val in enumerate(pulses):
   tr=np.setdiff1d(np.arange(61),val)
   zz=minimize(lambda x:nll(x,mode,tr,2),z.x,method='Nelder-Mead',options={'maxiter':300,'fatol':2e-5,'xatol':1e-3})
   print('CV',mode,qi,'tr',zz.fun,'val',nll(zz.x,mode,val,1),np.exp(zz.x),flush=True)
