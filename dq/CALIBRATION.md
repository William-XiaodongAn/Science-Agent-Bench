# dq calibration (2026-09-13)

Two corpora: this repository's four tasks (three on `main` plus the retired `zebrafish-voltage-forecast` from `dev`) and the 70 public
tasks of Terminal-Bench-Science 0.1 (`harbor-framework/terminal-bench-science`, `tasks/<domain>/<field>/<task>`), which went through
their own three-stage review and therefore serve as a reference for *false positives*: a check that fails many of them is miscalibrated.
Static checks only (no `--exec`, no URLs); the LLM judge was exercised separately (see the end).

## Outcome after calibration

- Our tasks: optical-mapping-activation-maps PASS, spiral-tip-patterns PASS, ssn-heldout-stimulus-prediction PASS, zebrafish-voltage-forecast PASS.
- Terminal-Bench-Science: 47 PASS, 23 NEEDS_REVIEW, 0 FAIL (first uncalibrated pass: 32 FAIL, 36 NEEDS_REVIEW, 2 PASS).

## Checks that still fire on Terminal-Bench-Science, and why that is right

| check | warn | fail | what fires |
|---|---|---|---|
| `structure.extraneous_files` | 4 | 0 | data files above 50 MB committed to the task (TB-Science moves these to a dataset host). |
| `config.timeouts` | 1 | 0 | an hours figure in the instruction, in a budget context, that differs from [agent].timeout_sec. |
| `instruction.length_and_sections` | 1 | 0 | instruction under 300 characters or no named output while the verifier reads agent files. |
| `instruction.deliverables_match_verifier` | 14 | 0 | agent-produced files the verifier opens but neither the instruction nor a shipped document names (implicit expectations; TB-Science's own check-test-file-references guards the same property). Heuristic, so warn not fail. |
| `instruction.referenced_inputs_exist` | 1 | 0 | input files named in the instruction that are neither shipped nor produced by the Dockerfile. |
| `instruction.absolute_paths` | 3 | 0 | deliverables named without an absolute location. |
| `leakage.sealed_not_in_environment` | 1 | 0 | the reference solution ships a copy of a ground-truth file (oracle pastes the answer): warn, not a leak to the agent. |
| `leakage.solution_not_hardcoded` | 1 | 0 | large literal arrays or data files inside solution/. |
| `solution.oracle_valid` | 1 | 0 | solve.sh without a shebang (cosmetic). |
| `solution.writes_deliverables` | 8 | 0 | the reference solution never mentions any of the files the verifier reads (paths built at run time); info-level, never changes the verdict. |
| `category.domain_keyword_consistency` | 30 | 0 | keyword scorer disagrees with the declared domain; info-level; the LLM judge and the reviewer decide. |
| `structure.compose_no_host_binds` | 1 | 0 | host bind mount in a compose file. |

## What the first pass got wrong, and the fix

- **Shared inputs are not leaks.** 31 of 70 TB-Science tasks had files under `tests/` byte-identical to files in `environment/`; all were inputs the verifier also needs (vocabularies, Lean project files, input arrays). Now only answer-like names (`truth`, `ground_truth`, `expected`, `answer`, `labels`, `golden_*`, `reference_*`) that are not input-like count as a leak; identical files inside `solution/` are reported as an oracle that pastes the answer (warn); everything else is info.
- **Format-string fragments are not file names.** `frame_{t:06d}.npy` and `base_{i}.csv` were read as `frame_.npy` / `base_.csv`. Placeholders (`{...}`, `<...>`, `$VAR`) are stripped before extraction and a name whose stem ends in `_`/`-` is matched as a family by prefix and extension.
- **Verifier-internal literals are not deliverables.** Lines that reference `tests/`, `SEALED`, fixtures, `__file__`, `/logs/verifier`, and files the verifier itself writes (`np.save`, `json.dump`, `to_csv`, `open(..., 'w')`) are excluded; names announced in any shipped README/template count as announced. The check is a warning, not a failure.
- **Optional sealed files.** A reference read inside an `exists()`/`try` guard within three lines (per-instance `anchors.json`) is optional, not missing.
- **Negations.** 'no GPU', 'cannot run', 'without a GPU' no longer read as a promise of a GPU.
- **Domain labels with hyphens** (`mathematical-sciences`) now normalise onto the taxonomy; aliases were extended with TB-Science's field names; alias matching is whole-phrase and picks the domain with the most hits (`population` alone had pulled a neuroscience task into clinical).
- **Info-severity checks never change the verdict.** Previously a warn-status result of an info-severity check sent a task to review.
- **Separate verifier containers** satisfy the reward-channel isolation the `executes_agent_code_safely` check asks for; local HTTP calls (`localhost` health checks) are not trial-time network fetches; a missing shebang is cosmetic because Harbor invokes bash explicitly; solve.sh may call scripts shipped in `environment/`.
- **Hours in the instruction** count against the budget only in a budget context ('you have', 'within', 'limit'); observation durations do not.
- **Standard environment variables** (`TMPDIR`, `USER`, ...) and variables exported inside `test.sh` are not undeclared.
- **Starter/template/submit scripts** in the workspace are not answer files.
- **URLs** are checked only in prose files; API base hosts in `task.toml` are not links.
- **LLM judge and reasoning models:** with an 1800-token budget the model spent every output token thinking (usage showed 1800 thinking tokens, stop reason max_tokens) and returned no text. The budget is now 8000 with one retry at double if the reply is empty; a `temperature` field was removed because some gateways reject it.

## What TB-Science's suite has that this one deliberately does not

Benchmark-specific conventions (task name namespace, binary rewards, the timeout sentence at the end of the instruction, CTRF reports, a proposal link in the PR) and API-backed checks (AI-authorship detection). They belong in a benchmark's CI; `dq` is the benchmark-agnostic first filter. Near-duplicate detection is included (`structure.near_duplicate`, TF cosine against `similarity.reference_dirs`), as are compose host-bind mounts.

## Genuine findings on the two corpora

- `geometric-pharmacophore-alignment` (TB-Science): `solution/ground_truth.sdf` is byte-identical to `tests/ground_truth.sdf`, i.e. the oracle pastes the answer; a commented-out `cp /tests/ground_truth.sdf` remains in `solve.sh`.
- 14 TB-Science tasks read agent files that no shipped text names (worth a reviewer's glance each; several are SDK-internal record files).
- Our tasks pass; the remaining information items are the templated judge credentials in `spiral-tip-patterns` and the keyword scorer reading the cardiac tasks as clinical/physiology rather than physics.

## LLM judge (advisory) spot checks

See the section appended by the calibration run below.

### Spot checks (Fable 5.1 through the gateway, 2026-09-13)

| task | judge status | recommendation | notable findings |
|---|---|---|---|
| `spiral-tip-patterns` | WARN | needs_review, confidence 0.6 | solvable/verifiable 'uncertain' (class sensitivity to discretisation; the mandatory VLM vote); domain and tier match; flags that the classifier's rule thresholds are stated in the instruction and that hidden labels are the reference pipeline's own output |
| `optical-mapping-activation-maps` | WARN | pass, confidence 0.65 | domain mismatch: task.toml declares `neuroscience-physiology`, the judge says cardiac physiology (clinical-health-population); the instruction's smoothing hint 'converts the inference into a recipe'; allowlisted model-API hosts contradict 'No internet' in the text |
| `ambient-rna-correction (TB-Science)` | WARN | pass, confidence 0.65 | verifiable yes, solvable uncertain (about 15 tight thresholds calibrated on one instance); proposes tier T1 (seeded synthetic generator) where TB-Science declares none; instruction reproduces verifier thresholds verbatim; a gene-symbol vs Ensembl-ID alignment ambiguity |

The judge's status is WARN whenever it says 'needs_review', rates solvable or verifiable 'uncertain', or disagrees with the declared domain or tier; FAIL only for 'fail', an 'infeasible' capability verdict (wet lab, physical instrument, human in the loop) or a hard 'no'. It never blocks: severity is advisory, so the committee always sees it with the reasons.
The two findings on our own tasks are real: the tier-2 domain label is wrong in `task.toml`, and the smoothing hint in its instruction is a legitimate design question (kept because the definitions require it; the expert-likeness gates remain undisclosed).
