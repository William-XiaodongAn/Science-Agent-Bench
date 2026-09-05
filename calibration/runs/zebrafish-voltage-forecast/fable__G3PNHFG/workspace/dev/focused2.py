import numpy as np, sys, json
sys.path.insert(0, '/workspace/dev')
from harness import score
rng = np.random.default_rng(int(sys.argv[1])); N = int(sys.argv[2]); seeds = tuple(int(x) for x in sys.argv[3].split(','))
def lu(lo, hi): return float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
def sample():
    nl = int(rng.choice([2, 3, 3, 3, 4, 4, 5]))
    # chain with a tendency to grow: sample weights
    w = np.sort(rng.uniform(0.3, 1.0, nl)) if rng.random() < 0.6 else rng.uniform(0.3, 1.0, nl)
    sizes = np.maximum(16, np.round(368 * w / w.sum() / 8) * 8).astype(int); sizes[-1] += 368 - sizes.sum()
    layers = tuple(int(x) for x in sizes)
    cfg = dict(layers=layers, voltage_feedback=False, spectral_radius=round(lu(0.85, 1.3), 3), connectivity=round(lu(0.03, 0.5), 3),
               ridge=lu(1e-7, 1e-4), input_to_output=bool(rng.random() < 0.5), all_layers_to_output=True,
               input_to_all_layers=bool(rng.random() < 0.3), inter_scale=round(lu(0.2, 2.0), 3))
    r = rng.random()
    if r < 0.35: cfg['leak'] = round(lu(0.06, 0.3), 4)
    elif r < 0.6: cfg['leak'] = tuple(round(lu(0.03, 0.5), 4) for _ in layers)
    else:
        lo = lu(0.005, 0.06); cfg['leak'] = (round(lo, 4), round(lu(0.15, 0.6), 3))
        if nl == 2: cfg['leak'] = (round(lo, 4), round(lu(0.15, 0.6), 3))
    cfg['input_scale'] = dict(bias=round(lu(0.03, 1.0), 3), stimulus=round(lu(0.5, 5.0), 3))
    if rng.random() < 0.15: cfg['readout_halflife'] = int(rng.choice([4000, 8000]))
    return cfg
cfgs = [sample() for _ in range(N)]
res = score(cfgs, seeds=seeds, verbose=False); res.sort(key=lambda x: x[1])
for cfg, m, ps in res[:30]: print(f'{m:.4f} {ps} {json.dumps(cfg, default=str)}')
print('median', np.median([r[1] for r in res]))
