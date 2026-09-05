import numpy as np
from scipy.optimize import differential_evolution, minimize
from scipy.special import ndtr
import time

R=np.load('data/train_r_obs.npy').astype(float)
I0=np.load('data/train_I.npy').astype(float)
xy=np.load('data/xy.npy')
types=np.r_[np.zeros(29,int),np.ones(20,int)]
d2=((xy[:,None,:]-xy[None,:,:])**2).sum(2)
obs_idx=np.arange(61)*200
tau=.5; k=.5

def makeW(p, mode=0):
    # p: log positive magnitudes, log widths
    J=np.exp(np.asarray(p[:4])).reshape(2,2)
    if mode==0:
        sig=np.exp(p[4:6]) # by presyn type
        S=np.empty((49,49))
        for b in range(2): S[:,types==b]=np.exp(-d2[:,types==b]/(2*sig[b]**2))
    else:
        sig=np.exp(p[4:8]).reshape(2,2)
        S=np.empty((49,49))
        for a in range(2):
          for b in range(2):
            ix=np.ix_(types==a,types==b); S[ix]=np.exp(-d2[ix]/(2*sig[a,b]**2))
    W=J[types[:,None],types[None,:]]*S
    W[:,types==1]*=-1
    np.fill_diagonal(W,0)
    return W

def simulate(W, I=I0, step=2):
    # coarsen safely for fitting; return obs
    h=.01*step/.5
    r=np.zeros(49); out=np.empty((49,61)); out[:,0]=r
    qi=1
    for q in range(step,12001,step):
        z=W@r+I[:,q]
        r += h*(-r+.5*np.maximum(z,0)**2)
        if not np.all(np.isfinite(r)) or r.max()>20: return None
        if q%200==0: out[:,qi]=r; qi+=1
    return out

SIG=.026
def obsmean(mu):
    z=mu/SIG
    return mu*ndtr(z)+SIG/np.sqrt(2*np.pi)*np.exp(-z*z/2)

calls=0
def objective(p, mode=0, train_cols=None, step=2):
    global calls
    calls+=1
    pred=simulate(makeW(p,mode),step=step)
    if pred is None: return 1e3
    pm=obsmean(pred)
    cols=np.arange(61) if train_cols is None else train_cols
    # ordinary MSE; signal naturally dominates but noise expectation corrected
    loss=np.mean((pm[:,cols]-R[:,cols])**2)
    # slight spatial weight decay discourages unstable large W
    loss += 1e-7*np.mean(np.exp(p[:4])**2)
    return loss

if __name__=='__main__':
  mode=1
  bounds=[(-4,2)]*4 + [(np.log(.3),np.log(5))]* (4 if mode else 2)
  st=time.time()
  res=differential_evolution(lambda p:objective(p,mode,step=2),bounds,popsize=12,maxiter=50,workers=1,polish=False,seed=3,updating='immediate',disp=True)
  print('DE',res.fun,res.x,np.exp(res.x),'calls',calls,'sec',time.time()-st)
  rr=minimize(lambda p:objective(p,mode,step=1),res.x,method='Nelder-Mead',options={'maxiter':500,'xatol':1e-4,'fatol':1e-10,'disp':True})
  print('FINAL',rr.fun,rr.x,np.exp(rr.x),'calls',calls,'sec',time.time()-st)
  W=makeW(rr.x,mode); P=simulate(W,step=1)
  np.save('/tmp/W.npy',W);np.save('/tmp/P.npy',P);np.save('/tmp/p.npy',rr.x)
  print('latent rmse',np.sqrt(np.mean((P-R)**2)),'obsmean rmse',np.sqrt(np.mean((obsmean(P)-R)**2)), 'W range/eigs',W.min(),W.max(),max(abs(np.linalg.eigvals(W))))
