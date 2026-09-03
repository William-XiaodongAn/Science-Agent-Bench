# Metrics

The exact definition of each score, and code that computes it. There are no
verifier scripts in this repo — **this file is the specification**. Both metrics
are `lower_better`.

Paths below assume the author's layout (`<task>/gt/`). A solver's submission is
whatever they wrote; substitute the paths.

---

## tier1_task_1 — held-out trajectory nRMSE

**What is compared.** The solver's predicted firing rates under the held-out
stimulus, against the true rates under that stimulus, over the whole recording.

**Normalisation.** RMSE divided by the standard deviation of the true trajectory.
This puts the score on a fixed scale: predicting a single constant everywhere
gives ≈1.0, so anything below 1 beats doing nothing, and 0 is exact.

```python
import numpy as np

r_pred = np.load("submission/r_pred.npy").astype(np.float64)   # (49, 12001)
r_true = np.load("tier1_task_1/gt/eval_r.npy").astype(np.float64)

score = np.sqrt(np.mean((r_pred - r_true) ** 2)) / r_true.std()
```

`r_true.std()` is the standard deviation over **all** entries, not per-neuron.

### Validity — check before scoring

A submission failing any of these is a **DNF**: no score, excluded from ranking.
Do not score it as "merely bad".

```python
assert r_pred.shape == (49, 12001)          # exact shape
assert np.isfinite(r_pred).all()            # no NaN / inf
assert r_pred.min() >= 0                    # rates are non-negative by construction
assert r_pred.max() <= 100 * r_true.max()   # not a clipped divergence
```

The last one matters and is easy to overlook. With `n = 2` the SSN's gain grows
with its own rate, so a slightly-too-strong `W` diverges. If a solver clips the
runaway to a finite number instead of leaving `inf`, the array passes
`isfinite` and scores ~1e7 — one such submission swamps any average. The true
trajectory peaks at 0.379, so the ceiling is 37.9.

### Secondary — peak-region nRMSE

Same quantity, restricted to timepoints where the true rate is above 10% of its
peak (33% of the trajectory, spread over 47 of the 49 neurons):

```python
active = r_true > 0.1 * r_true.max()
peak_nrmse = np.sqrt(np.mean((r_pred - r_true)[active] ** 2)) / r_true.std()
```

Report it, don't rank on it. A good primary score with a bad peak score means the
solver fitted the quiet stretches and missed the evoked responses.

### Anchors

| | nRMSE | peak-region |
|---|---|---|
| do-nothing (each neuron's training-condition mean) | 1.104 | 1.88 |
| plain ridge inversion | 0.444 | 0.71 |
| oracle (true `W`, initial state guessed) | 0.008 | 0.00 |
| process-noise floor | 0.011 | — |

Stored in `gt/meta.json` under `anchors`.

### Optional 0–100 rescale

```python
score_100 = 100 * np.clip((1.1035 - score) / (1.1035 - 0.0082), 0, 1)
```

Do-nothing is 0, oracle is 100. A linear map of the nRMSE — it adds no
information, so rank on the nRMSE itself.

---

## tier_2_task_1 — activation-time map RMSE (ms)

**What is compared.** The solver's per-pixel activation-time map against the
reference map, in milliseconds, **inside the intersection of the two masks**.

**Offset removal.** The zero of activation time is arbitrary — it depends on
where the beat is deemed to start — so the per-map **median** difference is
subtracted before the RMSE. Only the spatial *pattern* is scored.

```python
import numpy as np

gt_act  = np.load("tier_2_task_1/gt/activation_ms.npy")
gt_mask = np.load("tier_2_task_1/gt/mask.npy")

sub_act  = np.load("submission/activation_ms.npy").astype(np.float64)
sub_mask = np.load("submission/mask.npy").astype(bool)

sel = gt_mask & sub_mask                     # score only where both agree there is tissue
d = sub_act[sel] - gt_act[sel]
d = d[np.isfinite(d)]                        # off-tissue pixels are NaN

score = np.sqrt(np.mean((d - np.median(d)) ** 2))    # ms
```

### Validity — check before scoring

```python
coverage = (sub_mask & gt_mask).sum() / gt_mask.sum()
iou      = (sub_mask & gt_mask).sum() / (sub_mask | gt_mask).sum()

assert sub_act.shape == (128, 128) and sub_mask.shape == (128, 128)
assert sub_mask.any()
assert coverage >= 0.95      # must not omit the hard edges
assert iou      >= 0.55      # must not be an untargeted blob
assert len(d) >= 0.5 * sel.sum()    # enough finite pixels to be meaningful
```

**Both mask gates are needed, and neither alone is sufficient.** Coverage alone
is passed by marking the whole frame — that skips segmentation entirely. IoU
alone is passed by keeping only the easy centre of the tissue. Requiring both
forces a real segmentation. The whole frame scores IoU 0.37, and the hand-drawn
reference boundary caps any method at about 0.81, so the 0.55 gate leaves ample
room.

### Secondary — APD80 map RMSE

Same masked region, but **no offset removal** — APD80 is a duration, so its
absolute value is meaningful:

```python
d2 = sub_apd[sel] - gt_apd[sel]
d2 = d2[np.isfinite(d2)]
apd_rmse = np.sqrt(np.mean(d2 ** 2))         # ms
```

Report `coverage` and `iou` alongside it.

### Anchors

| | activation RMSE | APD80 RMSE |
|---|---|---|
| do-nothing (constant = spatial mean) | 19.33 ms | 12.17 ms |
| beat-to-beat repeatability (floor) | 1.01 ms | 2.27 ms |

Both rows are in `gt/beats.json`: the floors are `noise_floor_*`, and the
do-nothing baselines are `spatial_sd_*` — with the offset removed, a constant
prediction's RMSE is exactly the map's spatial standard deviation.

The APD80 baseline is **harder to beat than it looks**: 12.17 ms is a larger
number than the activation baseline relative to its floor (12.17/2.27 = 5.4x
versus 19.34/1.01 = 19x), and a competent pipeline can easily score worse than
constant on APD80 while doing well on activation. That is a real result about
the task, not a bug — report it rather than hiding it.

**Conduction velocity is not scored.** The pixel pitch was never recorded, so
`gt/cv_cm_s.npy` carries an unknown scale factor. It ships for reference only.

---

## tier_3_task_1 — zebrafish forecast RMSE

**What is compared.** The solver's predicted voltage over the held-out final 20%
of the recording, against the true voltage, at every one of the 4113 test points.

**No normalisation.** The recording is already min-max scaled to `[0, 1]`, so the
RMSE is dimensionless as it stands. This is the paper's own definition
(Delshad & Cherry 2025, Sec. III C) and is kept verbatim so results are directly
comparable to its published figures.

```python
import numpy as np

pred   = np.load("submission/pred.npy").astype(np.float64)   # (5, 4113) or (4113,)
target = np.load("tier_3_task_1/gt/test_data.npy").astype(np.float64)

if pred.ndim == 1:                      # deterministic method, single model
    score = np.sqrt(np.mean((pred - target) ** 2))
else:                                   # 5 seeds: mean of their individual RMSEs
    per_seed = np.sqrt(np.mean((pred - target) ** 2, axis=1))
    score = per_seed.mean()
```

**The mean of the per-seed RMSEs — not the RMSE of the averaged prediction.**
The paper trains one configuration 5 times with different random
initialisations and reports how that configuration typically performs, which is
the mean of the five errors. Collapsing the five rows into one prediction first
and scoring that measures an ensemble instead, and independent errors partially
cancel when averaged, so it lands far below what 0.0784 was measured under.
Score each row, then average the scores.

Using an ensemble as the method is fine — but then each of the five rows should
itself be a separately seeded ensemble, so the five rows remain five independent
instances of whatever the method is.

### Validity — check before scoring

```python
assert pred.shape in {(5, 4113), (4113,)}
assert np.isfinite(pred).all()
# a (4113,) submission must declare itself deterministic
assert pred.ndim == 2 or json.load(open("submission/budget.json"))["deterministic"]
```

Non-finite values are the signature of a diverged autoregressive rollout, which
is the usual failure mode for multi-step forecasting. Treat it as a DNF, not as a
large score. Predictions are **not** clipped to `[0, 1]`: out-of-range values are
permitted but can only increase the error, since the target never leaves it.

### Anchors

| | RMSE |
|---|---|
| do-nothing (predict the training mean) | 0.3022 |
| best possible constant (test mean — requires the answer) | 0.3016 |
| plain ESN+, 368 neurons — paper Fig. 7(b) | 0.1021 |
| **published baseline: DHESN-io+ (CN), 368 neurons — Fig. 14(b)** | **0.0784** |

The full table is in `gt/meta.json` under `paper_zebrafish_rmse`. 0.0784 is the
lowest error the paper reports for this data set.

**0.0784 is a baseline to beat, not a ceiling.** Unlike tier1's oracle and
tier2's noise floor — which are unreachable by construction — this is one
published method's result, and a better method should land below it. Do not
rescale against it as if it were 100 points: that would award full marks for
merely tying the prior art and give no credit for the improvement the task is
actually asking for.

### Reporting

Rank on the raw RMSE. If a normalised number is wanted, anchor the top end on the
perfect score, not on the baseline:

```python
score_100 = 100 * np.clip((0.3022 - score) / 0.3022, 0, 1)   # 0 = do-nothing, 100 = exact
```

Under this, the published baseline sits at **74.1**, leaving the remaining 26
points for genuine improvement over it.

```python
beats_paper = score < 0.0784        # report this flag alongside the score
```

### Comparability — the tuning budget

The paper's results came from a **fixed hyperparameter search budget**
(Sec. III B), and a number found by searching much harder is not comparable:

| depth | Bayesian-optimisation iterations |
|---|---|
| 1 layer | 20 |
| 2 layers | 30 |
| 3 layers | 40 |
| 4 layers | 50 |
| 5 layers | 60 |

with 5 repeats per configuration and the **mean of the 5** reported. The search
space was input weight scale `[0.05, 0.2]`, connection probability `[0.02, 0.15]`,
spectral radius `[0.8, 1.2]`, leaking rate `[0.5, 1]`, over reservoirs of 96, 144,
240, and 368 neurons. All of this is in `gt/meta.json` under
`paper_tuning_budget`.

**A single best-of-many seed is not a 0.0784-comparable result.** The `(5, 4113)`
submission shape exists so this is checkable rather than self-reported: the
scorer computes all five per-seed errors itself. What stays on trust is
`n_configs_evaluated` — a submission omitting `budget.json`, or declaring more
than 60 configurations, is scored but left unranked.
