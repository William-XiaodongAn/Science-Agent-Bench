import numpy as np, sys, json
sys.path.insert(0, '/workspace/dev')
from harness import score
rng = np.random.default_rng(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
N = int(sys.argv[2]) if len(sys.argv) > 2 else 100
seeds = tuple(int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else '0,1').split(','))
def lu(lo, hi): return float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
def sample():
    nl = int(rng.choice([1, 2, 2, 3]))
    if nl == 1: layers = (368,)
    else:
        cuts = np.sort(rng.choice(np.arange(40, 368 - 40, 8), nl - 1, replace=False)); parts = np.diff(np.r_[0, cuts, 368]); layers = tuple(int(p) for p in parts)
    fb = bool(rng.random() < 0.6)
    cfg = dict(layers=layers, voltage_feedback=fb,
               spectral_radius=round(lu(0.3, 1.4), 3), connectivity=round(lu(0.03, 1.0), 3),
               ridge=lu(1e-7, 1e-1), input_to_output=bool(rng.random() < 0.7))
    r = rng.random()
    if r < 0.4: cfg['leak'] = round(lu(0.01, 1.0), 4)
    elif r < 0.7: cfg['leak'] = tuple(round(lu(0.005, 1.0), 4) for _ in layers) if nl > 1 else (round(lu(0.002, 0.1), 4), round(lu(0.2, 1.0), 3))
    else:
        lo = lu(0.002, 0.1); cfg['leak'] = (round(lo, 4), round(lu(max(lo * 3, 0.1), 1.0), 3)) if nl != 2 else (round(lo, 4), round(lu(0.1, 1.0), 3))
    cfg['input_scale'] = dict(bias=round(lu(0.01, 1.0), 3), voltage=round(lu(0.02, 1.0), 3), stimulus=round(lu(0.05, 5.0), 3))
    if nl > 1:
        cfg['inter_scale'] = float(rng.choice([0.0, 0.01, 0.1, 0.3, 1.0])); cfg['input_to_all_layers'] = bool(rng.random() < 0.6); cfg['all_layers_to_output'] = bool(rng.random() < 0.7)
    if rng.random() < 0.25: cfg['readout_halflife'] = int(rng.choice([1500, 3000, 5000, 8000]))
    return cfg
cfgs = [sample() for _ in range(N)]
res = score(cfgs, seeds=seeds, verbose=False)
res.sort(key=lambda x: x[1])
for cfg, m, ps in res[:25]: print(f'{m:.4f} {ps} {json.dumps(cfg, default=str)}')
print('median', np.median([r[1] for r in res]))
