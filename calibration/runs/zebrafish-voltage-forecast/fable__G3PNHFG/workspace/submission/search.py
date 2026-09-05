"""Search procedure for baseline.esn.Forecaster configurations (zebrafish cardiac voltage, stimulus-driven forecasting).

Two phases inside the 60-evaluation budget:
  1. PORTFOLIO (~30 evaluations): a fixed list of designs from one family found during offline development with the
     evaluator's own protocol -- stimulus-driven (no voltage feedback) chains of 2-4 reservoirs, all read out, spectral
     radius near 1, leaks around 0.1 (or a per-neuron log-uniform range), small ridge.  Each seed picks its own best.
  2. LOCAL REFINEMENT (remaining budget): a seeded (1+1) hill climb that perturbs the best portfolio member's continuous
     hyperparameters (and occasionally re-partitions the units between layers) and keeps improvements.
The returned configuration is always one the evaluator scored (evaluator.best()).  A wall-clock guard stops the search
early if evaluations turn out slow.  Nothing here trains a reservoir outside evaluator.evaluate().
"""
import math, time
import numpy as np

try:
    from portfolio import PORTFOLIO
except ImportError:  # pragma: no cover
    PORTFOLIO = [dict(layers=(72, 48, 248), voltage_feedback=False, all_layers_to_output=True, input_to_all_layers=False,
                      input_to_output=True, inter_scale=1.0, leak=(0.0116, 0.338), ridge=1.3e-6, spectral_radius=0.972,
                      connectivity=0.1, input_scale=dict(bias=0.927, stimulus=4.191))]

N_PORTFOLIO = 30          # evaluations spent on the fixed portfolio
TIME_LIMIT = 600.0        # seconds; stop evaluating beyond this (the verifier allows 900)
SR_RANGE = (0.6, 1.3)     # spectral radii above ~1.3 were seen to diverge for some seeds


def _clean(cfg):
    """Plain python types, tuples for layers/leaks (what the Forecaster expects)."""
    out = {}
    for k, v in cfg.items():
        if isinstance(v, (list, tuple)):
            out[k] = tuple(float(x) if k != "layers" else int(x) for x in v)
        elif isinstance(v, dict):
            out[k] = {a: float(b) for a, b in v.items()}
        elif isinstance(v, (np.floating,)):
            out[k] = float(v)
        elif isinstance(v, (np.integer,)):
            out[k] = int(v)
        else:
            out[k] = v
    return out


def _perturb(cfg, rng):
    """One local move: log-normal jitter of the continuous hyperparameters, sometimes a structural tweak."""
    c = _clean(cfg)
    def jit(x, s, lo=None, hi=None):
        y = float(x) * math.exp(rng.normal(0.0, s))
        if lo is not None: y = max(lo, y)
        if hi is not None: y = min(hi, y)
        return y
    which = rng.random()
    if which < 0.55:                                   # small joint jitter of everything continuous
        c["spectral_radius"] = round(jit(c.get("spectral_radius", 0.9), 0.04, *SR_RANGE), 4)
        lk = c.get("leak", 0.5)
        c["leak"] = tuple(round(jit(a, 0.2, 0.002, 1.0), 4) for a in lk) if isinstance(lk, tuple) else round(jit(lk, 0.2, 0.002, 1.0), 4)
        if isinstance(c["leak"], tuple) and len(c["leak"]) == 2 and len(c["layers"]) != 2:
            lo, hi = sorted(c["leak"]); c["leak"] = (lo, max(hi, lo * 1.5))
        sc = dict(c.get("input_scale", {"bias": 0.1, "stimulus": 0.1})) if isinstance(c.get("input_scale"), dict) else {"bias": float(c.get("input_scale", 0.1)), "stimulus": float(c.get("input_scale", 0.1))}
        sc["stimulus"] = round(jit(sc.get("stimulus", 0.1), 0.25, 0.02, 10.0), 4); sc["bias"] = round(jit(sc.get("bias", 0.1), 0.3, 0.005, 2.0), 4)
        c["input_scale"] = sc
        if len(c["layers"]) > 1: c["inter_scale"] = round(jit(c.get("inter_scale", 0.1), 0.25, 0.02, 3.0), 4)
        c["ridge"] = jit(c.get("ridge", 1e-3), 0.8, 1e-9, 1e-1)
        c["connectivity"] = round(jit(c.get("connectivity", 0.1), 0.25, 0.02, 1.0), 4)
    elif which < 0.7:                                  # single-parameter larger move
        p = rng.choice(["spectral_radius", "stimulus", "ridge", "inter_scale", "leak"])
        if p == "spectral_radius": c["spectral_radius"] = round(jit(c.get("spectral_radius", 0.9), 0.08, *SR_RANGE), 4)
        elif p == "stimulus":
            sc = dict(c["input_scale"]) if isinstance(c.get("input_scale"), dict) else {"bias": 0.1, "stimulus": 0.1}
            sc["stimulus"] = round(jit(sc.get("stimulus", 0.1), 0.6, 0.02, 10.0), 4); c["input_scale"] = sc
        elif p == "ridge": c["ridge"] = jit(c.get("ridge", 1e-3), 2.0, 1e-9, 1e-1)
        elif p == "inter_scale" and len(c["layers"]) > 1: c["inter_scale"] = round(jit(c.get("inter_scale", 0.1), 0.6, 0.02, 3.0), 4)
        else:
            lk = c.get("leak", 0.5)
            c["leak"] = tuple(round(jit(a, 0.4, 0.002, 1.0), 4) for a in lk) if isinstance(lk, tuple) else round(jit(lk, 0.4, 0.002, 1.0), 4)
            if isinstance(c["leak"], tuple) and len(c["leak"]) == 2 and len(c["layers"]) != 2:
                lo, hi = sorted(c["leak"]); c["leak"] = (lo, max(hi, lo * 1.5))
    elif which < 0.85 and len(c["layers"]) > 1:        # move a block of units between two layers
        L = list(c["layers"]); i, j = rng.choice(len(L), 2, replace=False); blk = int(rng.choice([8, 16, 24]))
        if L[i] - blk >= 16:
            L[i] -= blk; L[j] += blk; c["layers"] = tuple(int(x) for x in L)
            if isinstance(c.get("leak"), tuple) and len(c["leak"]) == len(L) and len(L) != 2:
                pass
    else:                                              # readout wiring toggles
        p = rng.choice(["input_to_output", "input_to_all_layers", "halflife"])
        if p == "halflife": c["readout_halflife"] = None if c.get("readout_halflife") else int(rng.choice([3000, 6000, 10000]))
        else: c[p] = not bool(c.get(p, False))
    if sum(c["layers"]) > 368 or len(c["layers"]) > 5: return _clean(cfg)
    return c


def search(evaluator, seed):
    t0 = time.time(); rng = np.random.default_rng(12345 + int(seed))
    scores = []                                        # (score, cfg) for everything we evaluated

    def ev(cfg):
        """Score one configuration. None = budget or time exhausted; inf = rejected by the framework or diverged."""
        if evaluator.remaining <= 0 or time.time() - t0 > TIME_LIMIT: return None
        try:
            s = evaluator.evaluate(cfg)
        except Exception:                              # a config the framework refuses (not counted) or BudgetExhausted
            return None if evaluator.remaining <= 0 else float("inf")
        s = float(s) if np.isfinite(s) else float("inf")
        scores.append((s, cfg)); return s

    # ---- phase 1: portfolio -----------------------------------------------------------------------------------
    for cfg in PORTFOLIO[:N_PORTFOLIO]:
        if ev(_clean(cfg)) is None: break

    # ---- phase 2: (1+1) local refinement from the best portfolio member -----------------------------------------
    rejected = 0
    while evaluator.remaining > 0 and time.time() - t0 < TIME_LIMIT and scores and rejected < 25:
        finite = [sc for sc in scores if np.isfinite(sc[0])]
        if not finite: break
        finite.sort(key=lambda x: x[0])
        # mostly climb from the best; occasionally from the runner-up to keep some diversity
        parent = finite[0][1] if (rng.random() < 0.8 or len(finite) < 2) else finite[1][1]
        cand = _perturb(parent, rng)
        s = ev(cand)
        if s is None: break
        rejected = rejected + 1 if not np.isfinite(s) else 0

    best_cfg, _ = evaluator.best()
    if best_cfg is None:                               # nothing evaluated (should not happen): evaluate the first design
        cfg = _clean(PORTFOLIO[0]); evaluator.evaluate(cfg); return cfg
    return best_cfg
