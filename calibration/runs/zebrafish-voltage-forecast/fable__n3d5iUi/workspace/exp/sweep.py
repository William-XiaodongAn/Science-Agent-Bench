#!/usr/bin/env python3
"""Offline sweep helper (development only): evaluates configs with the shipped Evaluator protocol, in parallel worker processes."""
import sys, json, time, os
sys.path.insert(0, '/workspace/baseline')
import numpy as np
from multiprocessing import Pool

def _eval(args):
    cfg, seed = args
    import search_api
    v = np.load('/workspace/data/train_data.npy'); s = np.load('/workspace/data/train_stim.npy')
    ev = search_api.Evaluator(v, s, seed=seed, budget=10**6)
    try:
        r = ev.evaluate(cfg); per = ev.history[-1][2]
    except Exception as e:
        r, per = float('nan'), str(e)[:100]
    return cfg, seed, r, per

def run(configs, seeds=(0,), procs=4, tag=''):
    jobs = [(c, sd) for c in configs for sd in seeds]
    t0 = time.time()
    with Pool(procs) as p:
        res = p.map(_eval, jobs, chunksize=1)
    out = {}
    for cfg, sd, r, per in res:
        out.setdefault(json.dumps(cfg, sort_keys=True, default=str), []).append((sd, r, per))
    rows = []
    for k, lst in out.items():
        m = np.mean([r for _, r, _ in lst])
        rows.append((m, k, lst))
    rows.sort(key=lambda x: x[0])
    for m, k, lst in rows:
        print(f"{m:.4f}  {k}  per-seed {[round(r,4) for _,r,_ in lst]}")
    print(f"[{tag}] {len(jobs)} evals in {time.time()-t0:.0f}s", flush=True)
    return rows

if __name__ == '__main__':
    configs = json.load(open(sys.argv[1]))
    seeds = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else [0]
    run(configs, seeds, tag=sys.argv[1])
