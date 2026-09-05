exec(open('/workspace/work/fit_explore.py').read().split('bounds=')[0])
from scipy.optimize import least_squares
# pulse window assignment, centers
centers=np.array([15,42,70,98]); ts=np.arange(61)*2
fold=np.argmin(abs(ts[:,None]-centers),axis=1); near=np.min(abs(ts[:,None]-centers),axis=1)<=8
# use baseline too in all folds; pulse windows heldout
base_x=np.array([.7,.7,.4,.65,.9,.9,1.5,1.1])
bounds=([0,0,0,0,.35,.35,.35,.35],[2,2,2,2,4,4,4,4])
for f in range(4):
 use=~(near & (fold==f)); val=near&(fold==f)
 # emphasize all training active; no ad hoc obs selection
 def fn(q):
  o=sim(q)
  if o is None:return np.full(N*use.sum(),10.)
  return (o[:,use]-y[:,use]).ravel()
 res=least_squares(fn,base_x,bounds=bounds,max_nfev=120,ftol=2e-9,xtol=1e-8,x_scale='jac')
 o=sim(res.x)
 def rm(m):return np.sqrt(np.mean((o[:,m]-y[:,m])**2))
 print(f,'q',np.round(res.x,4),'cost',res.cost,'train',rm(use),'val',rm(val),'val high',rm(val&(y.mean(0)>.027)))
