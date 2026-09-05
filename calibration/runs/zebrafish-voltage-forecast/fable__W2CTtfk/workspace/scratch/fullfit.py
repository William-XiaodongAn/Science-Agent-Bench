import sys, os, json; os.environ["OMP_NUM_THREADS"]="4"
sys.path.insert(0,'/workspace/baseline'); sys.path.insert(0,'/workspace')
import numpy as np
from esn import Forecaster
import causal_runner
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
for sd in range(5):
    c=json.loads(json.dumps(json.load(open(f'/workspace/scratch/full_seed{sd}.json'))['config']))   # lists, as the verifier will pass them
    f=Forecaster(sd, **c)
    # full-data fit as the verifier does, then a synthetic causal roll-out on a replay of the last 4113 training stimuli
    p=causal_runner.rollout(f, v, s, s[-4113:])
    F=np.abs(f.Wout)
    print(f"seed {sd}: train_rmse {f.train_rmse:.4f} |Wout| max {F.max():.3g} mean {F.mean():.3g} | synthetic rollout finite {np.all(np.isfinite(p))} range [{p.min():.3f}, {p.max():.3f}] mean {p.mean():.3f} (train mean {v.mean():.3f})")
    # also a stress roll-out: a stimulus every 100 ms (shorter than anything seen) and every 200 ms
    for iv in (95,200):
        st=np.zeros(4113); st[::iv]=0.2; f2=Forecaster(sd, **c); f2.warmup(v,s); q=np.array([f2.step(x) for x in st])
        print(f"      stress interval {iv} ms: finite {np.all(np.isfinite(q))} range [{q.min():.3f}, {q.max():.3f}]")
