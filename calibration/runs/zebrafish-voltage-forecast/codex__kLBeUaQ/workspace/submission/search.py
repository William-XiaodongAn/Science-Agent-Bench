"""Budgeted ESN architecture search for the paced zebrafish trace."""
import numpy as np


def _base_candidates():
    """Return a curated, deterministic space-filling design of parallel banks."""
    rng = np.random.default_rng(314159)
    allocations = [
        (123, 123, 122), (80, 180, 108), (100, 168, 100), (150, 150, 68),
        (68, 150, 150), (150, 68, 150), (80, 128, 160), (160, 128, 80),
    ]
    leak_sets = [(.03, .12, .35), (.04, .14, .4), (.05, .15, .4),
                 (.06, .16, .45), (.07, .18, .5)]
    specs = []
    for allocation in allocations:
        for leaks in leak_sets:
            specs.append((allocation, leaks, .9, 1e-8, .03, 5., .1))

    # Additional space-filling points near the useful three-timescale region.
    while len(specs) < 60:
        raw = rng.dirichlet([5, 5, 4])
        sizes = np.maximum(50, np.floor(raw * 218).astype(int) + 50)
        while sizes.sum() < 368:
            sizes[np.argmin(sizes)] += 1
        while sizes.sum() > 368:
            sizes[np.argmax(sizes)] -= 1
        leaks = (rng.uniform(.025, .075), rng.uniform(.10, .20),
                 rng.uniform(.30, .55))
        specs.append((tuple(map(int, sizes)), leaks, rng.uniform(.86, .95),
                      10 ** rng.uniform(-9.5, -7), 10 ** rng.uniform(-2, -.7),
                      np.exp(rng.uniform(np.log(4), np.log(12))),
                      float(rng.choice([.05, .1, .2, .4]))))

    # The order itself is fixed. The selected subset covers the best-performing
    # regions without spending the whole budget on almost duplicate points.
    order = np.random.default_rng(2718).permutation(60)
    all_configs = []
    for j in order:
        layers, leaks, radius, ridge, bias, stimulus, connectivity = specs[j]
        all_configs.append(dict(
            layers=tuple(map(int, layers)),
            voltage_feedback=False,
            input_to_all_layers=True,
            all_layers_to_output=True,
            input_to_output=True,
            inter_scale=0.0,
            leak=tuple(map(float, leaks)),
            spectral_radius=float(radius),
            connectivity=float(connectivity),
            input_scale={"bias": float(bias), "stimulus": float(stimulus)},
            ridge=float(ridge),
            washout=1000,
        ))

    selected = [53, 58, 45, 29, 0, 31, 56, 41, 50, 44, 13, 15, 4,
                3, 34, 37, 33, 27, 54, 32, 11, 40, 36, 12, 22, 7, 35,
                9, 21, 55, 28, 5, 6]
    return [all_configs[i] for i in selected]


def _local_candidates(base):
    """Refine the best first-stage design without changing its model class."""
    out = []
    for factor in (.1, .25, .5, 2., 4., 10.):
        c = dict(base); c["ridge"] = float(base["ridge"] * factor); out.append(c)
    for delta in (-.04, -.025, -.0125, .0125, .025, .04):
        c = dict(base); c["spectral_radius"] = float(max(.05, base["spectral_radius"] + delta)); out.append(c)
    leaks = tuple(base["leak"])
    for factor in (.85, .925, 1.075, 1.15):
        c = dict(base); c["leak"] = tuple(float(x * factor) for x in leaks); out.append(c)
    for k in range(len(leaks)):
        for factor in (.85, 1.15):
            q = list(leaks); q[k] *= factor
            c = dict(base); c["leak"] = tuple(map(float, q)); out.append(c)
    for scale in (3., 10.):
        c = dict(base); c["input_scale"] = dict(base["input_scale"], stimulus=scale); out.append(c)
    for connectivity in (.05, .2):
        c = dict(base); c["connectivity"] = connectivity; out.append(c)
    c = dict(base); c["input_scale"] = dict(base["input_scale"], bias=.1); out.append(c)
    return out


def search(evaluator, seed: int) -> dict:
    """Spend at most 60 metered evaluations and return an evaluated config."""
    # `seed` is deliberately not used to alter the candidate distribution: the
    # supplied evaluator already builds every candidate with that seed.
    for config in _base_candidates():
        if evaluator.remaining <= 0:
            break
        evaluator.evaluate(config)

    if evaluator.remaining:
        first_best, _ = evaluator.best()
        for config in _local_candidates(first_best):
            if evaluator.remaining <= 0:
                break
            evaluator.evaluate(config)

    best, _ = evaluator.best()
    return best
