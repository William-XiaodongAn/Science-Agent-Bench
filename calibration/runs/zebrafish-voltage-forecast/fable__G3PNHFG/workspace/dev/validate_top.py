import json, sys, numpy as np
sys.path.insert(0, '/workspace/dev')
from harness import score, load_cache
# collect the best configs (by seeds 0,1 mean) from the cache
cache = load_cache(); by = {}
for r in cache.values():
    k = json.dumps(r['cfg'], sort_keys=True, default=str); by.setdefault(k, {})[r['seed']] = np.mean(r['per'])
cands = [(np.mean([d[0], d[1]]), json.loads(k)) for k, d in by.items() if 0 in d and 1 in d]
cands.sort(key=lambda x: x[0])
top = [c for _, c in cands[:int(sys.argv[1])]]
for c in top:
    if isinstance(c.get('layers'), list): c['layers'] = tuple(c['layers'])
    if isinstance(c.get('leak'), list): c['leak'] = tuple(c['leak'])
res = score(top, seeds=(0, 1, 2, 3, 4), verbose=False); res.sort(key=lambda x: x[1])
for cfg, m, ps in res: print(f'{m:.4f} sd {np.std(ps):.4f} {ps} {json.dumps(cfg, default=str)}')
