import sys, os; os.environ["OMP_NUM_THREADS"]="1"
sys.path.insert(0,'/workspace/baseline'); sys.path.insert(0,'/workspace')
import numpy as np, json
from esn import Forecaster
import causal_runner
from multiprocessing import Pool
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
cfg=dict(layers=(368,), voltage_feedback=False, leak=(0.03,0.3), ridge=1e-8, input_scale=dict(bias=0.1, stimulus=5.0))
H=4113
def job(a):
    o,L,seed=a
    f=Forecaster(seed, **cfg); p=causal_runner.rollout(f, v[o-L:o], s[o-L:o], s[o:o+H])
    return o,L,seed,float(np.sqrt(np.mean((p-v[o:o+H])**2)))
jobs=[(o,L,sd) for o in (10284,12341) for L in (3000,4500,6000,8000,10284) if L<=o for sd in (0,1)]
with Pool(4) as p:
    for o,L,sd,r in p.imap(job, jobs): print(f'origin {o} trainlen {L} seed {sd} rmse {r:.4f}', flush=True)
