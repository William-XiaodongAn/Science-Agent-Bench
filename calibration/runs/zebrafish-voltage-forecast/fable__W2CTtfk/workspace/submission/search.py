"""Search procedure for baseline.esn.Forecaster configurations (zebrafish cardiac voltage, closed-loop pacing).

Strategy (see methods.md):
  Phase 1 -- hypotheses: a short list of stimulus-driven (no voltage feedback) designs with slow / multi-timescale
             leaks and a near-zero ridge, plus the untuned default as a control.  Each costs one evaluation.
  Phase 2 -- refinement: coordinate moves around the best design so far (leak time-scales, connectivity, spectral
             radius, stimulus gain / ridge, bias, washout), accepting a move only if the dev RMSE improves.
  Always returns a configuration the evaluator has scored; never exceeds the budget or the wall clock.
"""
import copy
import time

import numpy as np

WALL_LIMIT_SEC = 900.0
SAFETY_SEC = 150.0           # stop refining when less than this remains of the 900 s wall clock

STIM = dict(bias=0.1, stimulus=20.0)
RIDGE_FLOOR, GAIN_CAP = 3e-8, 100.0     # keep refinement out of the ill-conditioned (ridge -> 0) corner


def _nf(**kw):
    """Stimulus-driven reservoir (no fed-back voltage), strong stimulus gain, small matched ridge; kw overrides."""
    c = dict(layers=(368,), voltage_feedback=False, ridge=1e-7, input_scale=dict(STIM))
    c.update(kw)
    return c


def _bank(layers, leaks, **kw):
    """Parallel bank of reservoirs with different leaks, all driven by the input and all read out."""
    return _nf(layers=layers, leak=leaks, inter_scale=0.0, input_to_all_layers=True, all_layers_to_output=True, **kw)


# ---------------------------------------------------------------- phase 1: the hypotheses, in priority order
SHORTLIST = [
    # multi-timescale flat reservoir: per-neuron log-uniform leaks spanning ~3 ms to ~30 ms integration
    _nf(leak=(0.03, 0.3)),
    # parallel bank of a fast (waveform) and a slow (interval-memory) reservoir, stronger gain
    _bank((184, 184), (0.2, 0.05), input_scale=dict(bias=0.1, stimulus=50.0)),
    # dense recurrent matrix, slightly larger ridge
    _nf(leak=(0.03, 0.3), connectivity=1.0, ridge=3e-7),
    # narrower multi-timescale range, stronger gain
    _nf(leak=(0.03, 0.2), input_scale=dict(bias=0.1, stimulus=50.0)),
    # three-timescale parallel bank
    _bank((123, 123, 122), (0.25, 0.1, 0.04)),
    # two-timescale bank at the base gain
    _bank((184, 184), (0.2, 0.05)),
    # single slow leak at the original (low-gain, near-zero-ridge) scaling
    _nf(leak=0.15, input_scale=dict(bias=0.1, stimulus=5.0), ridge=1e-8),
    # the framework's untuned default (voltage feedback, leak 0.5, ridge 1e-3) as the control hypothesis
    dict(layers=(368,)),
]


class _Budget:
    def __init__(self, evaluator, t0):
        self.ev = evaluator; self.t0 = t0

    def time_left(self):
        return WALL_LIMIT_SEC - (time.time() - self.t0)

    def can(self):
        return self.ev.remaining > 0 and self.time_left() > SAFETY_SEC

    def run(self, cfg):
        """Evaluate cfg; returns dev RMSE or None if it could not be evaluated (bad config / no budget)."""
        if not self.can():
            return None
        try:
            r = float(self.ev.evaluate(cfg))
        except Exception:  # noqa: BLE001  (a ConfigError does not consume budget; anything else we skip)
            return None
        if not np.isfinite(r):
            return None
        return r


def _key(cfg):
    import json
    return json.dumps(cfg, sort_keys=True, default=str)


# ---------------------------------------------------------------- phase 2: coordinate moves around a configuration
def _scale_leak(leak, f):
    if isinstance(leak, (tuple, list)):
        return tuple(float(min(1.0, max(1e-3, x * f))) for x in leak)
    return float(min(1.0, max(1e-3, leak * f)))


def _moves(cfg, rng):
    """Candidate neighbours of cfg (each a full config)."""
    out = []
    h = {**cfg}
    leak = h.get("leak", 0.5)
    for f in (0.7, 1.4):
        out.append({**h, "leak": _scale_leak(leak, f)})
    if isinstance(leak, (tuple, list)) and len(leak) == 2 and len(h.get("layers", (368,))) != 2:
        lo, hi = leak                      # per-neuron range: move one end at a time
        out.append({**h, "leak": (float(lo * 0.6), float(hi))})
        out.append({**h, "leak": (float(lo), float(min(1.0, hi * 1.6)))})
        out.append({**h, "leak": (float(lo * 1.6), float(hi))})
    conn = h.get("connectivity", 0.1)
    for c in (0.1, 0.3, 1.0):
        if abs(c - conn) > 1e-9:
            out.append({**h, "connectivity": c})
    sr = h.get("spectral_radius", 0.9)
    for f in (0.96, 1.04):
        out.append({**h, "spectral_radius": float(sr * f)})
    sc = dict(h.get("input_scale", STIM)) if isinstance(h.get("input_scale", STIM), dict) else dict(STIM)
    stim = sc.get("stimulus", 5.0); ridge = h.get("ridge", 1e-8)
    if stim * 2.0 <= GAIN_CAP:
        out.append({**h, "input_scale": {**sc, "stimulus": float(stim * 2.0)}})
    out.append({**h, "input_scale": {**sc, "stimulus": float(stim * 0.5)}})
    out.append({**h, "ridge": float(ridge * 3.0)})
    if ridge / 3.0 >= RIDGE_FLOOR:
        out.append({**h, "ridge": float(ridge / 3.0)})
    for b in (0.05, 0.2):
        if abs(sc.get("bias", 0.1) - b) > 1e-9:
            out.append({**h, "input_scale": {**sc, "bias": b}})
    out.append({**h, "washout": 2000 if h.get("washout", 1000) != 2000 else 500})
    rng.shuffle(out)
    return out


def _clean(cfg):
    """Drop keys the framework would ignore/normalise so that the returned dict equals what was evaluated."""
    return copy.deepcopy(cfg)


def search(evaluator, seed):
    t0 = time.time()
    rng = np.random.default_rng(1000 + int(seed))
    B = _Budget(evaluator, t0)
    seen = {}

    def score(cfg):
        k = _key(cfg)
        if k in seen:
            return seen[k]
        r = B.run(cfg)
        if r is not None:
            seen[k] = r
        return r

    # ---- phase 1: shortlist
    results = []
    for cfg in SHORTLIST:
        r = score(cfg)
        if r is not None:
            results.append((r, cfg))
    if not results:                                   # nothing could be evaluated: return the default (evaluated if possible)
        cfg = dict(layers=(368,)); score(cfg); return cfg
    results.sort(key=lambda t: t[0])
    best_r, best = results[0]

    # ---- phase 2: coordinate refinement around the best (and, if budget allows, the runner-up)
    frontier = [best] + [c for _, c in results[1:2]]
    stale, k = 0, 1
    while B.can():
        improved = False
        for base in list(frontier):
            for cand in _moves(base, rng):
                if not B.can():
                    break
                r = score(cand)
                if r is None:
                    continue
                if r < best_r - 1e-6:
                    best_r, best = r, cand; improved = True
            if not B.can():
                break
        if improved:
            frontier = [best]; stale = 0
        else:
            stale += 1                              # no neighbour of the incumbent helps: walk down the shortlist ranking
            frontier = [c for _, c in results[k:k + 2]] or [best]
            k += 2
            if k > len(results) + 2:                # every ranked design has been used as a base: perturb the incumbent again
                k = 1; frontier = [best]
            if stale >= 12:
                break
    # the evaluator's own record of the best is authoritative
    cfg_best, _ = evaluator.best()
    return _clean(cfg_best if cfg_best is not None else best)
