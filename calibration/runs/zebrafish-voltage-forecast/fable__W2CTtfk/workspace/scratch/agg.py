import json, numpy as np, collections, sys
d=collections.defaultdict(list)
for fn in sys.argv[1:]:
    for l in open(fn):
        r=json.loads(l); d[json.dumps(r['config'],sort_keys=True)].append(r['dev'])
rows=sorted(((np.mean(v),np.std(v),len(v),k) for k,v in d.items() if len(v)>=5))
for m,s,n,k in rows: print(f'{m:.4f} sd {s:.4f} n={n} {k}')
