import numpy as np, sys, json
sys.path.insert(0,'/workspace/work')
from sim import simulate
from fit_kernel import W_of_theta, dist2, fixed_point, I, Ie
th=np.load(sys.argv[1]); periodic=int(sys.argv[2]) if len(sys.argv)>2 else 0
W,_=W_of_theta(th,dist2(bool(periodic))); Wn=W.detach().numpy()
r0=fixed_point(Wn,I[:,0]); re=simulate(Wn,Ie,r0)
re=np.clip(re,0,None)
assert re.shape==(49,12001) and np.isfinite(re).all()
import os; os.makedirs('/workspace/submission',exist_ok=True)
np.save('/workspace/submission/r_pred.npy',re)
np.save('/workspace/submission/W_est.npy',Wn)
print('saved; max',re.max(),'mean',re.mean())
