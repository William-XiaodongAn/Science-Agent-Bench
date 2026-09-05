exec(open('/workspace/work/fit_explore.py').read().split('bounds=')[0])
from scipy.optimize import least_squares
from scipy.special import ndtr
sig=.01976
def fn(q):
 o=sim(q)
 if o is None:return np.ones(y.size)*10
 m=o*ndtr(o/sig)+sig/np.sqrt(2*np.pi)*np.exp(-.5*(o/sig)**2)
 return (m-y).ravel()
x=np.array([.4,.96,.396,.808,1.31,.8,1.62,1.116])
res=least_squares(fn,x,bounds=([0,0,0,0,.3,.3,.3,.3],[5,3,3,3,4,4,4,4]),max_nfev=100,ftol=1e-9,xtol=1e-8,x_scale='jac',verbose=1)
print(res.x,res.cost,np.sqrt(np.mean(fn(res.x)**2)))
np.save('/workspace/work/q_expected.npy',res.x)
