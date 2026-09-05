import numpy as np, sys, json
sys.path.insert(0, '/workspace/dev')
from harness import score
rng = np.random.default_rng(int(sys.argv[1])); N = int(sys.argv[2]); seeds = tuple(int(x) for x in sys.argv[3].split(','))
def lu(lo, hi): return float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
def sample():
    nl = int(rng.choice([2, 3, 3, 3, 4, 4]))
    w = rng.uniform(0.3, 1.0, nl)
    sizes = np.maximum(24, np.round(368 * w / w.sum() / 8) * 8).astype(int); sizes[-1] += 368 - sizes.sum()
    layers = tuple(int(x) for x in sizes)
    cfg = dict(layers=layers, voltage_feedback=False, spectral_radius=round(lu(0.8, 1.15), 3), connectivity=round(lu(0.05, 0.6), 3),
               ridge=lu(3e-7, 3e-5), input_to_output=bool(rng.random() < 0.5), all_layers_to_output=True,
               input_to_all_layers=bool(rng.random() < 0.5), inter_scale=round(lu(0.4, 1.6), 3))
    r = rng.random()
    if r < 0.6:
        lo = lu(0.006, 0.03); cfg['leak'] = (round(lo, 4), round(lu(0.2, 0.5), 3))
    elif r < 0.8: cfg['leak'] = tuple(round(lu(0.03, 0.4), 4) for _ in layers)
    else: cfg['leak'] = round(lu(0.06, 0.2), 4)
    cfg['input_scale'] = dict(bias=round(lu(0.05, 1.0), 3), stimulus=round(lu(1.0, 5.0), 3))
    if rng.random() < 0.3: cfg['washout'] = int(rng.choice([200, 500]))
    return cfg
cfgs = [sample() for _ in range(N)]
res = score(cfgs, seeds=seeds, verbose=False); res.sort(key=lambda x: x[1])
for cfg, m, ps in res[:30]: print(f'{m:.4f} {ps} {json.dumps(cfg, default=str)}')
print('median', np.median([r[1] for r in res]))
