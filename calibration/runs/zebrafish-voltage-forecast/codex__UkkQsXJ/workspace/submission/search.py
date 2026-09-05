"""Budgeted search for a stimulus-reset, multi-timescale ESN."""

import copy
import numpy as np


def _anchors():
    p = dict(layers=(74, 74, 74, 73, 73), voltage_feedback=False,
             input_to_all_layers=True, all_layers_to_output=True,
             inter_scale=0.0, input_to_output=True, readout_halflife=None)
    f = dict(layers=(368,), voltage_feedback=False, input_to_output=True,
             readout_halflife=None)
    out = []

    def add(base, **kw):
        c = dict(base); c.update(kw); out.append(c)

    add(p, spectral_radius=.9751142238451121, connectivity=.030854588051763814,
        leak=(.45784546127878056, .1516604198425067, .044645881359243,
              .2779710432967935, .06343280403081282),
        input_scale={'bias': .12418299369459748, 'stimulus': 1.1947949305905488},
        ridge=1.6723102778648208e-9, washout=1000)
    add(p, spectral_radius=.9751142238451121, connectivity=.030854588051763814,
        leak=(.45784546127878056, .1516604198425067, .044645881359243,
              .2779710432967935, .06343280403081282),
        input_scale={'bias': .1, 'stimulus': 1.1947949305905488},
        ridge=1e-9, washout=1000)
    add(p, spectral_radius=.8202288683915362, connectivity=.1785374529199306,
        leak=(.6016890448301291, .2550579795178623, .5822473363411206,
              .03722579924032839, .03875585252735811),
        input_scale={'bias': .2083893464389161, 'stimulus': .9763628411373245},
        ridge=1.3589921707888723e-11, washout=1000)
    add(p, spectral_radius=.9218197608151778, connectivity=.08229858786629084,
        leak=(.09683136010214365, .061278532857321606, .14374779149586345,
              .03970175860211274, .10532940739660823),
        input_scale={'bias': .11485717972056046, 'stimulus': 3.9520933387215558},
        ridge=8.263663288110423e-8, washout=300)
    add(p, spectral_radius=.9707902255010203, connectivity=.17446955320738144,
        leak=(.1844568048330077, .5576779310581741, .08097752095055558,
              .04302207542374283, .2207984088443655),
        input_scale={'bias': .2343472036871118, 'stimulus': 1.9253585658070511},
        ridge=7.465404451725223e-10, washout=2500)
    add(f, spectral_radius=.9779845446780765, connectivity=.1396483754864222,
        leak=.1843670995008745,
        input_scale={'bias': .09915952112854916, 'stimulus': 4.098882835107174},
        ridge=1.4555188247975735e-8, washout=1500)
    add(f, spectral_radius=.9356121729982958, connectivity=.07722209415346953,
        leak=.15545761894102034,
        input_scale={'bias': .07363203732327193, 'stimulus': 4.349851161579297},
        ridge=8.387864810210989e-8, washout=700)
    add(f, spectral_radius=.8598820173471546, connectivity=.041103856474607244,
        leak=.08430851926458317,
        input_scale={'bias': .05964299319371115, 'stimulus': 3.961427020731568},
        ridge=1.6580748831077058e-10, washout=1500)
    return out


def _partition(rng, n, total=368):
    raw = rng.dirichlet(np.full(n, 10.0))
    sizes = np.maximum(35, (raw * total).astype(int))
    while int(sizes.sum()) > total:
        sizes[int(np.argmax(sizes))] -= 1
    while int(sizes.sum()) < total:
        sizes[int(np.argmin(sizes))] += 1
    return tuple(int(x) for x in sizes)


def _parallel(rng, random_sizes=False):
    layers = _partition(rng, 5) if random_sizes else (74, 74, 74, 73, 73)
    return dict(
        layers=layers, voltage_feedback=False, input_to_all_layers=True,
        all_layers_to_output=True, inter_scale=0.0,
        input_to_output=bool(rng.random() < .9),
        spectral_radius=float(rng.uniform(.80, 1.04)),
        connectivity=float(np.exp(rng.uniform(np.log(.025), np.log(.22)))),
        leak=tuple(float(x) for x in np.exp(
            rng.uniform(np.log(.035), np.log(.70), 5))),
        input_scale={
            'bias': float(np.exp(rng.uniform(np.log(.025), np.log(.30)))),
            'stimulus': float(np.exp(rng.uniform(np.log(.65), np.log(4.5)))),
        },
        ridge=float(10 ** rng.uniform(-10.5, -7.0)),
        washout=int(rng.choice([0, 300, 700, 1000, 1500, 2500])),
        readout_halflife=None,
    )


def _flat(rng):
    return dict(
        layers=(368,), voltage_feedback=False, input_to_output=True,
        spectral_radius=float(rng.uniform(.82, 1.04)),
        connectivity=float(np.exp(rng.uniform(np.log(.025), np.log(.20)))),
        leak=float(np.exp(rng.uniform(np.log(.06), np.log(.23)))),
        input_scale={
            'bias': float(np.exp(rng.uniform(np.log(.025), np.log(.25)))),
            'stimulus': float(np.exp(rng.uniform(np.log(.65), np.log(5.0)))),
        },
        ridge=float(10 ** rng.uniform(-10.5, -7.0)),
        washout=int(rng.choice([0, 300, 700, 1000, 1500, 2500])),
        readout_halflife=None,
    )


def _mutate(config, rng):
    c = copy.deepcopy(config)
    c['spectral_radius'] = float(np.clip(
        c['spectral_radius'] * np.exp(rng.normal(0, .055)), .75, 1.10))
    c['connectivity'] = float(np.clip(
        c['connectivity'] * np.exp(rng.normal(0, .28)), .015, .35))
    if isinstance(c['leak'], tuple):
        c['leak'] = tuple(float(np.clip(x * np.exp(rng.normal(0, .18)), .02, .9))
                          for x in c['leak'])
    else:
        c['leak'] = float(np.clip(c['leak'] * np.exp(rng.normal(0, .18)), .025, .5))
    c['input_scale'] = {
        'bias': float(np.clip(c['input_scale']['bias'] * np.exp(rng.normal(0, .25)), .01, .6)),
        'stimulus': float(np.clip(c['input_scale']['stimulus'] * np.exp(rng.normal(0, .25)), .25, 8.0)),
    }
    c['ridge'] = float(np.clip(c['ridge'] * np.exp(rng.normal(0, .65)), 1e-12, 1e-5))
    return c


def search(evaluator, seed: int) -> dict:
    """Use at most 60 causal three-origin evaluations and return one evaluated config."""
    rng = np.random.default_rng(271828 + 1009 * int(seed))
    candidates = _anchors()
    candidates += [_parallel(rng, random_sizes=(i >= 24)) for i in range(32)]
    candidates += [_flat(rng) for _ in range(10)]

    for config in candidates:
        if evaluator.remaining <= 0:
            break
        evaluator.evaluate(config)

    # With the full budget, spend the final ten trials near this seed's best basin.
    while evaluator.remaining > 0:
        ranked = sorted(evaluator.history, key=lambda h: h[1])
        parent = ranked[int(rng.integers(0, min(3, len(ranked))))][0]
        evaluator.evaluate(_mutate(parent, rng))

    return evaluator.best()[0]
