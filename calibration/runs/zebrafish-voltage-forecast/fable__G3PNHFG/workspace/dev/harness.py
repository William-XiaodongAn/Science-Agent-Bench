"""Offline development harness: scores configurations with the evaluator's own protocol (3 dev origins x 4113 samples)
for several seeds, in parallel. Results are appended to a JSONL cache."""
import json, os, sys, time, hashlib
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, '/workspace')
from baseline import esn, causal_runner, search_api

V = np.load('/workspace/data/train_data.npy'); S = np.load('/workspace/data/train_stim.npy')
CACHE = '/workspace/dev/cache.jsonl'

def key(cfg, seed, origins):
    return hashlib.md5(json.dumps([cfg, seed, list(origins)], sort_keys=True, default=str).encode()).hexdigest()

def _one(args):
    cfg, seed, origins = args
    per = []
    for o in origins:
        try:
            f = esn.Forecaster(seed, **cfg)
            p = causal_runner.rollout(f, V[:o], S[:o], S[o:o + 4113])
            per.append(float(np.sqrt(np.mean((p - V[o:o + 4113]) ** 2))) if np.all(np.isfinite(p)) else float('inf'))
        except Exception as e:
            per.append(float('nan'))
    return (cfg, seed, list(origins), per)

def load_cache():
    d = {}
    if os.path.exists(CACHE):
        for line in open(CACHE):
            r = json.loads(line); d[r['key']] = r
    return d

def score(configs, seeds=(0, 1, 2, 3, 4), origins=search_api.DEV_ORIGINS, procs=4, verbose=True):
    """Returns list of (cfg, mean_over_seeds_of_dev_rmse, per_seed) aligned with configs."""
    cache = load_cache(); jobs = []
    for cfg in configs:
        for sd in seeds:
            if key(cfg, sd, origins) not in cache:
                jobs.append((cfg, sd, origins))
    t0 = time.time()
    if jobs:
        with Pool(procs) as pool, open(CACHE, 'a') as fh:
            for cfg, sd, org, per in pool.imap_unordered(_one, jobs):
                r = dict(key=key(cfg, sd, org), cfg=cfg, seed=sd, origins=org, per=per)
                fh.write(json.dumps(r, default=str) + '\n'); cache[r['key']] = r
    out = []
    for cfg in configs:
        ps = [np.mean(cache[key(cfg, sd, origins)]['per']) for sd in seeds]
        out.append((cfg, float(np.mean(ps)), [round(float(x), 4) for x in ps]))
    if verbose:
        print(f'{len(jobs)} jobs in {time.time()-t0:.0f}s')
        for cfg, m, ps in sorted(out, key=lambda x: x[1]):
            print(f'{m:.4f}  {ps}  {json.dumps(cfg, default=str)}')
    return out
