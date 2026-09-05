"""Pseudo-test: run the search with an evaluator whose origins lie before 8227, then score the returned config (and fixed anchors)
on the unseen window 12341:16454 (the last 4113 training samples). Development only."""
import sys, json, time; sys.path.insert(0,'/workspace/baseline')
import numpy as np, search_api, esn, causal_runner
from multiprocessing import Pool
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
O=12341; H=4113; MOD=sys.argv[1]
def score(cfg, seed):
    f=esn.Forecaster(seed, **cfg); p=causal_runner.rollout(f, v[:O], s[:O], s[O:O+H]); return float(np.sqrt(np.mean((p-v[O:O+H])**2)))
def one(seed):
    search=search_api.load_search(MOD, ['/workspace','/workspace/submission'])
    ev=search_api.Evaluator(v, s, seed=seed, budget=60, origins=(4114, 6170, 8227))
    t0=time.time(); cfg=search(ev, seed); dt=time.time()-t0
    anchor=dict(layers=(368,), voltage_feedback=False, leak=(0.02,0.3), input_scale=dict(bias=0.1,stimulus=50.0), ridge=1e-7)
    return seed, dt, ev.n_evaluated, ev.best()[1], score(cfg, seed), score(anchor, seed), score(dict(layers=(368,)), seed), json.dumps(cfg, default=str)
if __name__=='__main__':
    with Pool(4) as p: res=p.map(one, [0,1,2,3,4])
    for sd,dt,n,dev,st,sa,sdef,cfg in res: print(f"seed {sd}: {n} evals {dt:.0f}s dev(early origins) {dev:.4f} | pseudo-test searched {st:.4f} anchor {sa:.4f} default {sdef:.4f}\n   {cfg}")
    a=np.array([[r[4],r[5],r[6]] for r in res]); print('MEAN pseudo-test: searched %.4f anchor %.4f default %.4f'%tuple(a.mean(0)))
