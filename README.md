# Science Agent Bench

Verifiable, agentic science tasks for **SciAgent Bench** (Scale AI x Georgia Tech). Each task
ships as a sandboxed environment with data and tools, a compute/wall-clock budget, a frozen
programmatic verifier, and sealed ground truth (proposal + spec, Aug 2026).

## Harbor tasks (RSI Bench layout)

`tasks/` holds the runnable tasks in the [RSI Bench](https://github.com/scaleapi/rsi-benchmark)
/ [Harbor](https://www.harborframework.com) layout, one per tier of the proposal:

| Task | Tier | Domain | Metric (lower is better) | Do-nothing | Pass bar | Reference |
|---|---|---|---|---|---|---|
| [`ssn-heldout-stimulus-prediction`](tasks/ssn-heldout-stimulus-prediction) | T1 controlled generator | neuroscience / nonlinear dynamics | held-out trajectory nRMSE | 1.104 | < 0.444 | 0.423 |
| [`optical-mapping-activation-maps`](tasks/optical-mapping-activation-maps) | T2 expert workflow | cardiac electrophysiology | activation-map RMSE (ms), APD80 RMSE (ms) | 19.33 | < 1.89 (one frame) and APD80 < 3.78 (two frames) | 0.92 / 2.5 |
| [`zebrafish-voltage-forecast`](tasks/zebrafish-voltage-forecast) | T3 open-ended discovery | cardiac dynamics | test RMSE, paper's split; the submitted echo state network is rolled out causally by the verifier (stimulus delivered one sample at a time), mean of 5 seeds | 0.302 | < 0.0745 (5% below the paper's best published result, with an ESN) | 0.071 (stimulus-driven multi-timescale ESN) |

All three are **CPU-only** (4 vCPU, 16 GB; Harbor passes these to Docker as hard limits, so a local Docker VM must offer at least that many CPUs). Every verifier writes `/logs/verifier/reward.txt`
(the task's normalised score in [0, 1], or 1.0/0.0 pass with `REWARD_MODE=binary`) and
`/logs/verifier/result.json` (raw metric, normalised score, `passed`, `ranked`, flags, secondary
metrics, diagnostics). "Pass" is the documented per-task rule (valid + `methods.md` + metric below
the bar) and is what pass@k counts. Each task directory also carries `task.yaml` (spec §3.2
metadata), a maintainer `README.md` (science background, provenance, anchors, validity probes, spec
gate self-assessment) and a canary GUID in every text file.

Layout of a task, and how it maps onto the spec's §3.1 anatomy:

    tasks/<name>/
      task.toml               Harbor task config: resources, timeouts, network allowlist, verifier anchors
      task.yaml               spec §3.2 metadata (tier, domain, modality, budget, baselines, probes, canary)
      instruction.md          agent-facing (spec: INSTRUCTIONS.md)
      README.md               maintainer-facing (spec: README.md)
      environment/            Dockerfile + workspace/ = exactly what the agent sees at t=0 (spec: environment/, assets/)
      solution/               solve.sh (oracle = reference method) + baseline.sh (naive) (spec: baseline/)
      tests/                  test.sh -> grade.py, SHA256SUMS, sealed/ ground truth, validity_probes.py (spec: verifier/, tests/)
      generator/              Tier 1 only: seed -> instance (spec: generator/, private)

### Running

```bash
pip install -e ".[runner]"           # harbor
python fetch_data.py --only dat      # tier-2's 250 MB raw recording (or let its Dockerfile download it)
ln tier_2_task_1/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat tasks/optical-mapping-activation-maps/environment/workspace/data/

harbor run -p tasks/zebrafish-voltage-forecast -a oracle -y                      # reference solution through the verifier
export ANTHROPIC_API_KEY=...
harbor run -p tasks/ssn-heldout-stimulus-prediction -a claude-code -m claude-opus-5 -y
harbor run -p tasks/optical-mapping-activation-maps -a codex -m gpt-5.6-sol -y
```

Tasks declare `network_mode = "allowlist"` (model API hosts only), so the images bake in the
scientific stack and the agent CLIs; on a Docker host without egress-control support Harbor will
say so, and the tasks can be run with `network_mode = "public"` for local checks.

### Frontier-agent calibration (2026-09-03 / 04)

Fable 5.1 (claude-code), GPT-5.6 Sol (codex) and Gemini 3.7 Flash (gemini-cli), k = 3 on Modal via
`calibration/run_calibration.sh`. Tier 1 passed 1/3 by each agent
([`RESULTS-2026-09-03.md`](calibration/RESULTS-2026-09-03.md)). Tier 2 passed 3/3 by Fable and Codex and 0/3 by
Gemini under v0.1's empirical 3.0 ms bar; under v0.2 (gates in frame units, APD80 gated) **Fable 3/3, Codex 1/3,
Gemini 0/3**, and a blinded forced-choice judge (two model families, agreeing on all 11 comparisons) preferred the
expert's maps in 9 of 11 ([`RESULTS-2026-09-04-tier2-v02.md`](calibration/RESULTS-2026-09-04-tier2-v02.md)). Tier 3 was run three
times as the task was tightened: 3/3 for every agent under v0.3 (whole test stimulus released; all
solutions read beat durations off future stimulus times); 3/3 for Fable and Codex with beat templates
and tree ensembles and 0/3 for Gemini under v0.5 (causal roll-out, any method;
[`RESULTS-2026-09-04-tier3-v05.md`](calibration/RESULTS-2026-09-04-tier3-v05.md)); under v0.6
(causal roll-out, echo state networks only, bar = the paper's 0.0784) Fable 3/3, Codex 0/3, Gemini 0/3,
every pass a stimulus-driven ESN without voltage feedback, audited compliant
([`RESULTS-2026-09-04-tier3-v06.md`](calibration/RESULTS-2026-09-04-tier3-v06.md)); and under v0.7
(pass = at least 5% below the paper, RMSE < 0.0745) **Fable 2/3, Codex 2/3, Gemini 0/3**, pass@1 0.67 /
0.67 / 0, all four passes stimulus-driven ESN ensembles or deep ESNs with cell-model inputs, audited
compliant ([`RESULTS-2026-09-04-tier3-v07.md`](calibration/RESULTS-2026-09-04-tier3-v07.md)).

### agent-env (pass@k on frontier models)

[`agentenv/register_task.py`](agentenv/register_task.py) registers a task directory as a runnable
agent-env `Task` (sandbox VM -> task container -> claude-code A2A agent -> `/tests/test.sh`),
`agent-env eval run --k N` runs it, and [`agentenv/passk.py`](agentenv/passk.py) aggregates
pass@k. See [`agentenv/README.md`](agentenv/README.md).

### Known issues to resolve before acceptance

- **Tier 3 (v0.6) follows the paper's setup causally and restricts the method to the paper's model
  class.** The stimulus is an input, as in the paper, but the paper's networks receive it one sample at
  a time; under the closed-loop pacing protocol the *next* stimulus time reveals the current beat's
  duration (repolarisation-to-stimulus gap 51 ± 1.4 ms), so releasing the whole test stimulus (v0.1-v0.4)
  let a template score 0.0555 and frontier agents 0.022-0.042. v0.5 made the submission a model rolled out
  by the verifier with the stimulus delivered sample by sample; frontier agents then passed with causal
  beat templates and tree ensembles (0.055-0.065), which are not what the paper studies. v0.6 restricts
  the method to echo state networks (declaration + import scan in the verifier, code audit afterwards);
  the shipped framework covers the paper's whole family, and our reference, a stimulus-driven
  multi-timescale ESN without voltage feedback, scores 0.071 against the paper's 0.0784. See its README §2.
- **Tier 1 headroom:** no legitimate method above 0.62 normalised is known, while the oracle
  sits at 1.0. Probe gap to a drive-only proxy is modest. See its README §4-5.
- **Tier 2 APD80 definition** in the original instruction did not match the frozen ground truth;
  the task instruction now matches the ground-truth code.
- Data licences (tier 2, tier 3), second-expert sign-offs, expert solve times and frontier-model
  calibration runs are pending for all three.

---

## Author's copy (source data and ground truth)

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
| **Input** | rates + drive under one stimulus; drive only under the held-out one | 128x128 16-bit camera stream, 529.09 fps | 16454 training samples; the test-window stimulus arrives one sample at a time |
| **Submit** | `r_pred.npy` (49, 12001) | `mask.npy`, `activation_ms.npy`, `apd80_ms.npy`, each (128,128) | `forecaster.py` (an echo state network the verifier rolls out for 5 seeds) |
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
