import copy
import numpy as np

from baseline.search_api import Evaluator


v = np.load('/workspace/data/train_data.npy')
s = np.load('/workspace/data/train_stim.npy')
ev = Evaluator(v, s, seed=0, budget=60)

configs = []
labels = []


def add(label, **cfg):
    labels.append(label)
    configs.append(cfg)


add('default', layers=(368,))

# Flat reservoirs: broad dynamical sweep for feedback and stimulus-only models.
for fb in (True, False):
    for rho, leak in [(0.1, .1), (0.1, .3), (0.1, .7),
                      (0.5, .1), (0.5, .3), (0.5, .7),
                      (0.9, .05), (0.9, .1), (0.9, .2), (0.9, .3), (0.9, .7),
                      (1.2, .05), (1.2, .1), (1.2, .2), (1.2, .4)]:
        add(f'flat fb={fb} rho={rho} leak={leak}', layers=(368,), voltage_feedback=fb,
            spectral_radius=rho, leak=leak)

# Input and regularisation around promising plausible flat regimes.
for fb in (True, False):
    for scale in (.01, .03, .3, 1.0):
        add(f'scale fb={fb} s={scale}', layers=(368,), voltage_feedback=fb,
            spectral_radius=.9, leak=.1, input_scale=scale)
    for ridge in (1e-7, 1e-5, 1e-2, 1e-1):
        add(f'ridge fb={fb} r={ridge}', layers=(368,), voltage_feedback=fb,
            spectral_radius=.9, leak=.1, ridge=ridge)

# Heterogeneous timescales in one reservoir.
for fb in (True, False):
    for lr in ((.01, .3), (.02, .8), (.05, 1.0)):
        add(f'leakrange fb={fb} {lr}', layers=(368,), voltage_feedback=fb,
            spectral_radius=.9, leak=lr)

# Parallel banks and serial hierarchies.
for fb in (True, False):
    for leaks in ((.03,.08,.2,.5,1.0), (.05,.1,.2,.4,.8)):
        add(f'parallel fb={fb} leaks={leaks}', layers=(74,74,74,73,73), voltage_feedback=fb,
            input_to_all_layers=True, all_layers_to_output=True, inter_scale=0,
            leak=leaks, spectral_radius=.9)
    add(f'deep fb={fb}', layers=(184,184), voltage_feedback=fb,
        input_to_all_layers=True, all_layers_to_output=True, inter_scale=.3,
        leak=(.1,.5), spectral_radius=.9)

assert len(configs) == 59, len(configs)
for i, (label, cfg) in enumerate(zip(labels, configs)):
    score = ev.evaluate(cfg)
    print(f'{i:02d} {score:.6f} {np.round(ev.history[-1][2], 5).tolist()} {label}', flush=True)

print('BEST', ev.best(), flush=True)
