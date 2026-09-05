import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr
import compare_models as c
from row_correct import simfull,nll
SIG=.02;active=np.where(c.I.max(1)>.3)[0]
def fit(base,lam=.2,cols=None):
 if cols is None:cols=np.arange(61)
 def fun(x):
  W=base.copy();W[:,active]*=np.exp(x)[None,:];P=c.sim(W,2)
  if P is None:return 1e5
  y=c.R[:,cols];mu=P[:,cols];pos=y>0;ll=np.empty_like(y)
  ll[pos]=-.5*((y[pos]-mu[pos])/SIG)**2-np.log(SIG)-.5*np.log(2*np.pi);ll[~pos]=log_ndtr(-mu[~pos]/SIG)
  return -ll.mean()+lam*np.mean(x*x)
 z=minimize(fun,np.zeros(len(active)),method='Nelder-Mead',options={'maxiter':700,'fatol':2e-6,'xatol':5e-4})
 W=base.copy();W[:,active]*=np.exp(z.x)[None,:]
 return W,z
if __name__=='__main__':
 base=np.load('/tmp/joint_plain_combined.npy');val=np.arange(47,53);tr=np.setdiff1d(np.arange(61),val)
 for lam in [.05,.2,.8]:
  W,z=fit(base,lam);P=simfull(W);print('FULL',lam,z.fun,nll(P,np.arange(61)),np.exp(z.x),P.max(),flush=True);np.save('/tmp/colcorr_'+str(lam)+'.npy',W)
  W,z=fit(base,lam,tr);P=simfull(W);print('CV',lam,nll(P,val),np.exp(z.x),flush=True)
