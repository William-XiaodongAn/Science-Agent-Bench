import numpy as np, sys, json
sys.path.insert(0, '/workspace/dev')
from harness import score
rng = np.random.default_rng(int(sys.argv[1])); N = int(sys.argv[2]); seeds = tuple(int(x) for x in sys.argv[3].split(','))
def lu(lo, hi): return float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
def sample():
    nl = int(rng.choice([1, 2, 3, 3]))
    if nl == 1: layers = (368,)
    else:
        cuts = np.sort(rng.choice(np.arange(40, 368 - 40, 8), nl - 1, replace=False)); layers = tuple(int(p) for p in np.diff(np.r_[0, cuts, 368]))
    cfg = dict(layers=layers, voltage_feedback=False, spectral_radius=round(lu(0.9, 1.6), 3), connectivity=round(lu(0.03, 0.6), 3),
               ridge=lu(1e-7, 3e-2), input_to_output=bool(rng.random() < 0.5))
    r = rng.random()
    if r < 0.4: cfg['leak'] = round(lu(0.05, 0.5), 4)
    elif nl > 1 and r < 0.7: cfg['leak'] = tuple(round(lu(0.02, 0.6), 4) for _ in layers)
    else: cfg['leak'] = (round(lu(0.005, 0.1), 4), round(lu(0.15, 0.8), 3))
    cfg['input_scale'] = dict(bias=round(lu(0.02, 1.0), 3), stimulus=round(lu(0.05, 5.0), 3))
    if nl > 1:
        cfg['inter_scale'] = float(rng.choice([0.1, 0.3, 1.0, 1.0, 2.0])); cfg['input_to_all_layers'] = bool(rng.random() < 0.5); cfg['all_layers_to_output'] = bool(rng.random() < 0.85)
    if rng.random() < 0.2: cfg['readout_halflife'] = int(rng.choice([3000, 5000, 8000]))
    return cfg
cfgs = [sample() for _ in range(N)]
res = score(cfgs, seeds=seeds, verbose=False); res.sort(key=lambda x: x[1])
for cfg, m, ps in res[:30]: print(f'{m:.4f} {ps} {json.dumps(cfg, default=str)}')
print('median', np.median([r[1] for r in res]))
