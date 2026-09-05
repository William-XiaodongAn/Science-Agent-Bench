import sys, os; os.environ["OMP_NUM_THREADS"]="1"
sys.path.insert(0,'/workspace/baseline'); sys.path.insert(0,'/workspace')
import numpy as np, json
from esn import Forecaster
import causal_runner
from multiprocessing import Pool
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
base=dict(voltage_feedback=False, ridge=1e-8, input_scale=dict(bias=0.1, stimulus=5.0))
D={'flat_range':dict(base, layers=(368,), leak=(0.03,0.3)),
   'flat_range_c1':dict(base, layers=(368,), leak=(0.03,0.3), connectivity=1.0),
   'flat_015':dict(base, layers=(368,), leak=0.15),
   'bank2':dict(base, layers=(184,184), leak=(0.2,0.05), inter_scale=0.0, input_to_all_layers=True, all_layers_to_output=True),
   'bank3':dict(base, layers=(123,123,122), leak=(0.25,0.1,0.04), inter_scale=0.0, input_to_all_layers=True, all_layers_to_output=True),
   's20_r7':dict(base, layers=(368,), leak=(0.03,0.3), input_scale=dict(bias=0.1, stimulus=20.0), ridge=1e-7),
   'default':dict(layers=(368,))}
H=2500
origins=(5000,7000,9000,11000,13000,13954)
def job(a):
    name,o,seed=a
    f=Forecaster(seed, **D[name]); p=causal_runner.rollout(f, v[:o], s[:o], s[o:o+H])
    return name,o,seed,float(np.sqrt(np.mean((p-v[o:o+H])**2)))
jobs=[(n,o,sd) for n in D for o in origins for sd in (0,1)]
res={}
with Pool(4) as p:
    for n,o,sd,r in p.imap_unordered(job, jobs): res[(n,o,sd)]=r
for n in D:
    row=[np.mean([res[(n,o,sd)] for sd in (0,1)]) for o in origins]
    print(f'{n:14s}', ' '.join(f'{x:.4f}' for x in row), ' mean', f'{np.mean(row):.4f}')
