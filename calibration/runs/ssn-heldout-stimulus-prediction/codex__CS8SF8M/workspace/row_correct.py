import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr
import compare_models as c

I=c.I;Y=c.R;SIG=.02; obs=np.arange(61)*200

def simfull(W,drive=I):
 r=np.zeros(49);P=np.empty((49,12001));P[:,0]=r
 for q in range(1,12001):
  r += .02*(-r+.5*np.maximum(W@r+drive[:,q],0)**2)
  if not np.isfinite(r).all() or r.max()>10:return None
  P[:,q]=r
 return P

def fit_rows(Wbase,lam=1.,cols=None,threshold=.3):
 P=simfull(Wbase); new=Wbase.copy()
 if cols is None:cols=np.arange(61)
 qset=obs[cols]
 active=np.where(I.max(1)>threshold)[0]
 pars=np.zeros((49,2))
 for i in active:
  e=Wbase[i,:29]@P[:29]; h=Wbase[i,29:]@P[29:]
  def one(x, ret=False):
   a,b=np.exp(x);r=0.;out=np.empty(61);out[0]=r;qi=1
   for q in range(1,12001):
    z=a*e[q]+b*h[q]+I[i,q];r += .02*(-r+.5*max(z,0)**2)
    if q%200==0:out[qi]=r;qi+=1
   yy=Y[i,cols];mu=out[cols];pos=yy>0
   ll=np.empty_like(yy);ll[pos]=-.5*((yy[pos]-mu[pos])/SIG)**2-np.log(SIG)-.5*np.log(2*np.pi);ll[~pos]=log_ndtr(-mu[~pos]/SIG)
   val=-ll.mean()+lam*np.mean(x*x)
   return (val,out) if ret else val
  z=minimize(one,[0,0],method='Nelder-Mead',options={'maxiter':150,'xatol':1e-3,'fatol':1e-5})
  pars[i]=z.x;new[i,:29]*=np.exp(z.x[0]);new[i,29:]*=np.exp(z.x[1])
  print(i,np.exp(z.x),z.fun,flush=True)
 return new,pars

def nll(P,cols):
 y=Y[:,cols];mu=P[:,obs[cols]];pos=y>0;ll=np.empty_like(y);ll[pos]=-.5*((y[pos]-mu[pos])/SIG)**2;ll[~pos]=log_ndtr(-mu[~pos]/SIG);return -ll.mean()

if __name__=='__main__':
 pulses=[np.arange(4,12),np.arange(19,24),np.arange(31,40),np.arange(47,53)]
 for basefile,name in [('/tmp/lik_col_W.npy','col'),('/tmp/lik_W_0.001.npy','plain')]:
  base=np.load(basefile)
  for lam in [.1,.5]:
   print('RUN',name,lam)
   W,p=fit_rows(base,lam)
   P=simfull(W);print('FULL',nll(P,np.arange(61)),'max',P.max())
   vals=[]
   # Strongest-pulse holdout is the most stringent extrapolation check.
   for val in [pulses[3]]:
    tr=np.setdiff1d(np.arange(61),val);Wc,pc=fit_rows(base,lam,tr);Pc=simfull(Wc);vals.append(nll(Pc,val))
   print('CVRESULT',name,lam,vals,np.mean(vals),flush=True)
   np.save(f'/tmp/row_{name}_{lam}.npy',W)
