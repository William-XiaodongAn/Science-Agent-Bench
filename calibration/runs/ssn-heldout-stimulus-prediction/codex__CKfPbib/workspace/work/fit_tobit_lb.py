exec(open('/workspace/work/fit_explore.py').read().split('bounds=')[0])
from scipy.optimize import minimize
from scipy.special import log_ndtr
# redefine sim starting code inherited
pos=y>0
count=0
def obj(z):
 global count
 q=z[:8]; sig=z[8]
 o=sim(q)
 if o is None:return 1e9
 # exclude t0? include, assuming r0=0
 resid=(y[pos]-o[pos])/sig
 ll=.5*np.sum(resid**2)+pos.sum()*np.log(sig)
 ll-=np.sum(log_ndtr(-o[~pos]/sig))
 count+=1
 if count%100==0: print(count,ll,np.round(z,4),flush=True)
 return ll
x=np.r_[ [4.85,.573,.4355,1.94,.489,.993,1.323,.719], .0226]
b=[(.01,5),(.01,3),(.01,3),(.01,3),(.3,4),(.3,4),(.3,4),(.3,4),(.005,.06)]
res=minimize(obj,x,method='L-BFGS-B',bounds=b,options={'maxiter':100,'ftol':1e-10,'disp':True,'maxls':30})
print(res.fun,res.nfev,res.x)
o=sim(res.x[:8]); print('rmse',np.sqrt(np.mean((o-y)**2)), 'max',o.max())
