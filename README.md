# Science Agent Bench — tasks

Three benchmark tasks. Each has a solver-facing `instruction.md`, input data, and
frozen ground truth.

**This is the author's copy: it contains the answers.** To hand a task to a
solver, build the released half with the script below — never copy a task
directory directly.

## Layout

    tier1_task_1/
      instruction.md      what the solver is shown
      gt/                 inputs + ANSWERS + make_gt.py (regenerates everything)
    tier_2_task_1/
      instruction.md      what the solver is shown
      *.dat  *.mat        raw recording (released) / expert-processed (author only)
      gt/                 ANSWER maps + make_gt.py + scoring anchors
    tier_3_task_1/
      instruction.md      what the solver is shown
      dataset1.mat        the raw recording
      *.pdf               Delshad & Cherry 2025, the source paper
      gt/                 split + ANSWER (test_data.npy) + anchors
    METRICS.md            exact scoring definitions + code
    make_solver_package.py
    fetch_data.py         downloads the two large recordings from Google Drive

## The three tasks

| | tier1_task_1 | tier_2_task_1 | tier_3_task_1 |
|---|---|---|---|
| **Task** | predict a 49-neuron SSN's response to a stimulus it never saw | recover per-pixel activation and APD80 maps from a raw optical mapping recording | forecast the last 20% of a zebrafish cardiac voltage trace |
| **Input** | rates + drive under one stimulus; drive only under the held-out one | 128x128 16-bit camera stream, 529.09 fps | 16454 training samples + the test-window stimulus |
| **Submit** | `r_pred.npy` (49, 12001) | `mask.npy`, `activation_ms.npy`, `apd80_ms.npy`, each (128,128) | `pred.npy` (4113,) |
| **Metric** | trajectory nRMSE | activation-time map RMSE (ms), median offset removed | RMSE, paper's definition |
| **Do-nothing** | 1.104 | 19.33 ms | 0.3022 |
| **Reference** | 0.008 (oracle floor) | 1.01 ms (noise floor) | **0.0784** (published baseline) |

tier1 is synthetic and regenerable; tier2 and tier3 are real recordings.

The third column is different in kind. tier1's oracle and tier2's noise floor are
**unreachable by construction** — nothing can score below them. tier3's 0.0784 is
a **published baseline that should be beaten**; it is the result to improve on,
not a ceiling, so do not normalise scores against it as if it were full marks.

## Large files

Two recordings exceed GitHub's 100 MB limit and live in Google Drive instead:

| file | size | needed for |
|---|---|---|
| `...-PM1394Cam00.dat` | 239 MB | tier2's **input data** — any solver needs it |
| `...-PM1394Cam00.mat` | 469 MB | only to regenerate `tier_2_task_1/gt/` |

    pip install gdown
    python fetch_data.py              # both
    python fetch_data.py --only dat   # just the solver input
    python fetch_data.py --check      # verify what is present

Downloads are checksum-verified. Everything else in the repo is 20 MB. The `.mat`
is rarely needed: the maps it produces are already committed (396 KB total).

## Building the solver package

    python make_solver_package.py --out ../solver_package

Copies only the released inputs and the instructions, rewrites tier1's
`meta.json` down to the physical constants, and refuses to finish if any answer
file or scoring anchor slipped through.

## Scoring

See **[METRICS.md](METRICS.md)** — the exact definition of each metric, runnable
code, the validity gates, and the anchors. There are no verifier scripts and no
reference solutions here, so that file is the specification.

## Regenerating ground truth

    python tier1_task_1/gt/make_gt.py     # seeded and deterministic
    python tier_3_task_1/gt/make_gt.py    # splits dataset1.mat

Needs `numpy` and `scipy`. tier2's `gt/make_gt.py` reads the expert `.mat`.

## What must not reach a solver

`tier1_task_1/gt/eval_r.npy` and `W_true.npy` are the answer; `make_gt.py`
regenerates both. `tier1_task_1/gt/meta.json` mixes solver-facing constants with
the true spectral radius, the metric's normaliser, and the anchors — which is why
the package script rewrites it rather than copying it. Everything in
`tier_2_task_1/gt/` is an answer or an anchor, as is the `.mat`.
`tier_3_task_1/gt/test_data.npy` is the forecast target.

## Notes

- **No verifiers and no reference solutions.** [METRICS.md](METRICS.md) is the
  scoring specification.
- **tier1 has no `paper.pdf`.** `instruction.md` reproduces the model equations
  (Eqs. 1-6 of Rubin, Van Hooser & Miller 2015, *Neuron* 85:402-417,
  doi:10.1016/j.neuron.2014.12.026), so the paper is not needed to solve it.
- **tier3's 0.0784 is a baseline to beat, not a floor.** It is Fig. 14(b) of
  Delshad & Cherry 2025, a 5-layer deep hybrid ESN. Going below it is the point
  of the task.
- **tier3 has a tuning budget.** The paper fixed its hyperparameter search
  (20/30/40/50/60 Bayesian-optimisation iterations for 1-5 layers, 5 repeats,
  mean of the 5 reported). A result from a much larger search, or a single lucky
  seed picked from many, is not comparable to 0.0784 — see `instruction.md` and
  `gt/meta.json`.
- **tier2 pixel pitch was never recorded**, so conduction velocity has an unknown
  scale factor. `gt/cv_cm_s.npy` exists but is not scored.
- **tier2 documentation carried stale numbers**, now corrected against the
  shipped maps: 18 usable beats (not 17 with a dropped final beat), noise floors
  1.01/2.27 ms (not 1.56/2.69), and do-nothing baselines 19.33/12.17 ms (not
  22.67/9.21). The old APD80 figure was the misleading one — it understated the
  baseline, so a solver scoring 10 ms would have looked like a win when it is
  in fact worse than predicting a constant.
