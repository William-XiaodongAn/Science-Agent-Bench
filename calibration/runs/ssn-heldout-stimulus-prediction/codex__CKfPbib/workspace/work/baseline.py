import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr
p='/workspace/data/';y=np.load(p+'train_r_obs.npy').astype(float);I=np.load(p+'train_I.npy').astype(float);ts=np.arange(61)*2
mx=(I[:,::200]-.18).max(0)
use=(mx<1e-6)&(ts>0)
Y=y[:,use];pos=Y>0
print('times',ts[use],Y.shape,'means',Y.mean(), 'zeros',np.mean(~pos))
def obj(z):
 mu=z[:49];s=z[-1];rr=(Y-mu[:,None])/s
 return .5*np.sum(rr[pos]**2)+pos.sum()*np.log(s)-np.sum(log_ndtr(np.broadcast_to(-mu[:,None]/s,Y.shape)[~pos]))
x=np.r_[np.full(49,.015),.02]
res=minimize(obj,x,method='L-BFGS-B',bounds=[(0,.1)]*49+[(.005,.06)],options={'maxiter':2000,'ftol':1e-12,'maxls':50})
print(res.success,res.fun,res.x[-1],res.nit)
print('mu',np.round(res.x[:49],4),'mean/std',res.x[:49].mean(),res.x[:49].std())
np.save('/workspace/work/baseline_mu.npy',res.x[:49])
