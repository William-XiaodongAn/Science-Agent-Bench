# Science Agent Bench

Verifiable, agentic science tasks for **SciAgent Bench** (Scale AI x Georgia Tech). Each task
ships as a sandboxed environment with data and tools, a compute/wall-clock budget, a frozen
programmatic verifier, and sealed ground truth (proposal + spec, Aug 2026).

## What makes this different from other science agent benchmarks

Most agentic-science suites (Terminal-Bench Science and similar) are built *from the literature*:
a published paper plus its public repository is turned into a task, and the ground truth is the
figure or number the paper already reports. SciAgent Bench is built *from the bench*.

**1. Real experimental data and real lab workflows, not literature reproduction.** The tier-2 task is
a raw recording from the lab that ran the experiment — a 239 MB 128x128 voltage-dye camera stream of
beating cardiac tissue at 529.09 fps (Fenton lab, Georgia Tech). The agent is handed the instrument
output, not a cleaned array: a vendor binary stream with an under-exposed first frame, stored
transposed relative to the analysis convention, with an inverted fluorescence polarity. Every one of
those has a plausible shortcut that is quietly wrong, and the validity probes in each task's README §4
measure exactly how wrong. The tier-3 task replaces a step the same lab still does by hand (drawing
spiral-wave tip patterns in its own WebGL simulator) with a systematic pipeline. Tier 1 sits alongside
them as a controlled generator, so difficulty is a dial rather than a lucky find. (A fourth task built
on the zebrafish cardiac recording behind Delshad & Cherry 2025 is retired to the `dev` branch: both
leading agents pass it.)

**2. Expert workflows published here for the first time.** The ground truth is not a published
figure — it is what a lab's own analysis pipeline produces, frozen into code. Tier 2's activation
and APD80 maps come from an expert-processed recording that has never been released; the frozen
definitions in `tier_2_task_1/gt/make_gt.py` (beat detection on the field mean, 50% upstroke
crossing, APD80 as time above the 20% level, mean over 18 beats) encode practice that until now
existed only inside the lab. That also shrinks the contamination surface: there is no public repo
carrying the answer, and every text file in every task carries a canary GUID so leakage is
detectable. (Data licences and second-expert sign-offs are still pending — see *Known issues*.)

**3. First Georgia Tech x Scale AI collaboration on a science agent benchmark.** The tasks come
from the people who ran the experiments rather than from readers of their papers, so the metric
definitions, validity gates and anchors were written with the experimentalists instead of being
reverse-engineered from a figure caption. Where the paper's setup and a well-posed task disagreed,
the authors were asked directly — Tier 3's v0.1 -> v0.3 history is that conversation.

**4. Domain professors supervising the tasks, not just crowd annotators.** Each task is overseen by
a faculty expert in its field; **Flavio Fenton** and **Elizabeth Cherry** (Georgia Tech) have
already agreed to supervise, and both are principals of the science the cardiac tiers are built on
— the Tier 2 recording and the Tier 3 spiral-wave problem come from the Fenton lab, and the retired
zebrafish task is the problem of Delshad & Cherry 2025. Supervision covers what a verifier cannot check by itself: that the metric is the one
the field actually uses, that the pass bar corresponds to a result a working scientist would accept,
and that the shortcuts the validity probes reject are the shortcuts that matter.

## Harbor tasks (RSI Bench layout)

`tasks/` holds the runnable tasks in the [RSI Bench](https://github.com/scaleapi/rsi-benchmark)
/ [Harbor](https://www.harborframework.com) layout, one per tier of the proposal:

| Task | Tier | Domain | Metric (lower is better) | Do-nothing | Pass bar | Reference |
|---|---|---|---|---|---|---|
| [`ssn-heldout-stimulus-prediction`](tasks/ssn-heldout-stimulus-prediction) | T1 controlled generator | neuroscience / nonlinear dynamics | held-out trajectory nRMSE | 1.104 | < 0.444 | 0.423 |
| [`optical-mapping-activation-maps`](tasks/optical-mapping-activation-maps) | T2 expert workflow | cardiac electrophysiology | activation-map RMSE (ms), APD80 RMSE (ms) | 19.33 | < 1.89 (one frame) and APD80 < 3.78 (two frames) | 0.92 / 2.5 |
| [`spiral-tip-patterns`](tasks/spiral-tip-patterns) | T3 open-ended discovery | cardiac dynamics / spiral-wave meander | pattern-class match of the pipeline's simulated tip trajectories (6 reference + 8 hidden parameter sets, higher is better) | 0 | 6/6 reference and >= 7/8 hidden | 14/14 (score 1.0) |

All tasks are **CPU-only** (4 vCPU, 16 GB; Harbor passes these to Docker as hard limits, so a local Docker VM must offer at least that many CPUs). Every verifier writes `/logs/verifier/reward.txt`
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
pip install "harbor>=0.21,<0.23"     # add harbor[modal] to run on Modal
python fetch_data.py --only dat      # tier-2's 250 MB raw recording (or let its Dockerfile download it)
ln tier_2_task_1/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat tasks/optical-mapping-activation-maps/environment/workspace/data/

harbor run -p tasks/ssn-heldout-stimulus-prediction -a oracle -y                 # reference solution through the verifier
export ANTHROPIC_API_KEY=...
harbor run -p tasks/ssn-heldout-stimulus-prediction -a claude-code -m claude-fable-5-1 -y
harbor run -p tasks/optical-mapping-activation-maps -a codex -m gpt-5.6-sol -y
```

Tasks declare `network_mode = "allowlist"` (model API hosts only), so the images bake in the
scientific stack and the agent CLIs; on a Docker host without egress-control support Harbor will
say so, and the tasks can be run with `network_mode = "public"` for local checks. `spiral-tip-patterns`
runs a VLM judge inside its verifier and needs the judge credentials passed with `harbor --env-file`
(see its README).

## Results: frontier agents, pass@1 under the current verifiers

Fable 5.1 (`claude-code`), GPT-5.6 Sol (`codex`) and Gemini 3.7 Flash (`gemini-cli`), k = 3 scored trials per agent, on
Modal with each task's budget. Where a verifier changed after the runs, the captured submissions were re-verified with
the current verifier; the agents were not re-run. Full trajectories, submitted deliverables and verifier outputs per
trial: [`results/`](results).

<!-- results-table -->
| Task | Version | Fable 5.1 | GPT-5.6 Sol | Gemini 3.7 Flash | Human check |
|---|---|---|---|---|---|
| [`optical-mapping-activation-maps`](results/optical-mapping-activation-maps) | 0.3 | **0.00** (0/3; one-sample 0) | **0.00** (0/3; one-sample 0) | **0.00** (0/3; one-sample 0) | expert rejected all nine deliverables next to the lab's maps; the v0.3 gates encode that |
| [`spiral-tip-patterns`](results/spiral-tip-patterns) | 0.2 | **0.33** (1/3; one-sample 1) | **0.25** (1/4; one-sample 0) | **0.00** (0/3; one-sample 0) | verifier agrees with the expert's blinded review on 10 of 11 drawings |
| [`ssn-heldout-stimulus-prediction`](results/ssn-heldout-stimulus-prediction) | 0.1 | **0.33** (1/3; one-sample 1) | **0.33** (1/3; one-sample 1) | **0.33** (1/3; one-sample 1) | - |

Cells: n-sample pass@1 (passes / scored trials; one-sample = outcome of the first trial). Per-task confidence intervals, pass@n, rewards and agent times: `results/<task>/README.md`; benchmark-level aggregate: `results/README.md`.
<!-- /results-table -->

Reading the table: tier 2 and tier 3 task 2 are deliverable-style tasks where RMSE-only gates let work through that the
domain expert rejects at a glance; their current verifiers add expert-calibrated gates (mask outline and map smoothness;
straight drift runs, sharp linear-core cusps and a blinded VLM judge) without stating those standards in the
instruction. Tier 1 keeps headroom (best known legitimate method about 0.62 normalised against an oracle at 1.0).

**Retired from `main` (2026-09-07): `zebrafish-voltage-forecast`** (T3, v0.10, causal voltage forecast under the paper's
protocol, ESN family). Fable 5.1 and GPT-5.6 Sol beat the paper's number in 3/3 attempts each (Gemini 0/3), so the task
does not discriminate between frontier agents. The task, its results (pass@1 and trajectories) and its v0.1 -> v0.10
history stay on the `dev` branch (`tasks/zebrafish-voltage-forecast/`, `results/zebrafish-voltage-forecast/`).

### Known issues to resolve before acceptance

- **Tier 1 headroom:** no legitimate method above 0.62 normalised is known while the oracle sits at 1.0 (task README §4-5).
- **Tier 2 / tier 3 task 2 gates** encode one expert's judgement each; a second expert's sign-off is pending, as are the
  data licences for tiers 2 and 3 and the expert solve times for tiers 1-3 (tier 3 task 2: under 5 min per pattern).

## Branches

- `main` (this branch): the Harbor tasks with their current verifier suites, `results/` (pass@1 and trajectories), and the
  task owner's original material below. Retired tasks are removed from `main` and kept on `dev`.
- [`dev`](https://github.com/William-XiaodongAn/Science-Agent-Bench/tree/dev): everything else, with history: verifier calibration write-ups (`calibration/RESULTS-*.md`), trajectory
  audits (`calibration/trajectory-digests/`), the calibration and re-verification tooling, the agent-env adapter, and the
  script that publishes the clean layout to `main` (`calibration/publish_main.sh`).

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
| **Submit** | `r_pred.npy` (49, 12001) | `mask.npy`, `activation_ms.npy`, `apd80_ms.npy`, each (128,128) | `search.py` (a search procedure the verifier runs 5 times under the paper's size and budget) |
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
