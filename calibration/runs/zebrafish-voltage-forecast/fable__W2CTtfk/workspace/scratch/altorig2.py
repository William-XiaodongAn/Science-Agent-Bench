import sys, os, json; os.environ["OMP_NUM_THREADS"]="1"
sys.path.insert(0,'/workspace/baseline'); sys.path.insert(0,'/workspace')
import numpy as np
from esn import Forecaster
import causal_runner
from multiprocessing import Pool
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
D={}
for sd in range(5):
    c=json.load(open(f'/workspace/scratch/full_seed{sd}.json'))['config']; c['layers']=tuple(c['layers']); c['feedback_clip']=tuple(c['feedback_clip'])
    if isinstance(c['leak'],list): c['leak']=tuple(c['leak'])
    D[('returned',sd)]=c
    D[('shortlist0',sd)]=dict(layers=(368,), voltage_feedback=False, ridge=1e-8, leak=(0.03,0.3), input_scale=dict(bias=0.1, stimulus=5.0))
H=2500; origins=(5000,7000,9000,11000,13000,13954)
def job(a):
    key,o=a; name,sd=key
    f=Forecaster(sd, **D[key]); p=causal_runner.rollout(f, v[:o], s[:o], s[o:o+H])
    return key,o,float(np.sqrt(np.mean((p-v[o:o+H])**2)))
res={}
with Pool(4) as p:
    for key,o,r in p.imap_unordered(job, [(k,o) for k in D for o in origins]): res[(key,o)]=r
for name in ('returned','shortlist0'):
    rows=np.array([[res[((name,sd),o)] for o in origins] for sd in range(5)])
    print(name, 'per-origin mean over seeds', np.round(rows.mean(0),4), 'overall', rows.mean().round(4))
    for sd in range(5): print('   seed',sd, np.round(rows[sd],4), rows[sd].mean().round(4))
