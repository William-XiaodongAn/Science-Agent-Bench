import numpy as np,time
from scipy.optimize import minimize
from scipy.special import log_ndtr
import compare_models as c
SIG=.02;Y=c.R
def factors(base,corr):
 f=np.ones((49,2))
 for i in range(49):
  for b,sl in enumerate([slice(0,29),slice(29,49)]):
   z=np.abs(base[i,sl])>1e-12
   if z.any():f[i,b]=np.median(corr[i,sl][z]/base[i,sl][z])
 return f
def getW(p,v,f):
 W=c.Wmake(p,v);W[:,:29]*=f[:,0,None];W[:,29:]*=f[:,1,None];return W
def obj(p,v,f,step):
 W=getW(p,v,f);P=c.sim(W,step)
 if P is None:return 1e5
 y=Y;pos=y>0;ll=np.empty_like(y);ll[pos]=-.5*((y[pos]-P[pos])/SIG)**2-np.log(SIG)-.5*np.log(2*np.pi);ll[~pos]=log_ndtr(-P[~pos]/SIG)
 return -ll.mean()+.001*np.mean(W*W)
if __name__=='__main__':
 for v,pf,bf,cf in [('plain','/tmp/lik_p_0.001.npy','/tmp/lik_W_0.001.npy','/tmp/row_plain_0.1.npy'),('colnorm','/tmp/lik_col_p.npy','/tmp/lik_col_W.npy','/tmp/row_col_0.1.npy')]:
  p=np.load(pf);f=factors(np.load(bf),np.load(cf));st=time.time()
  for step,it in [(2,600),(1,250)]:
   z=minimize(lambda x:obj(x,v,f,step),p,method='Nelder-Mead',options={'maxiter':it,'fatol':1e-6,'xatol':2e-4});p=z.x;print(v,step,z.fun,np.exp(p),time.time()-st,flush=True)
  np.save('/tmp/joint_'+v+'_base.npy',c.Wmake(p,v));np.save('/tmp/joint_'+v+'_p.npy',p)
