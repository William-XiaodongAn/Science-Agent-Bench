# spiral-tip-patterns: calibration runs

10 scored trials (one directory each: `trajectory/` = agent log + Harbor trajectory, `workspace/` = the agent's workspace as it left it
(its `submission/` plus scratch scripts; shipped data/baseline/tool, frames and files above the size cap omitted, see SKIPPED_LARGE_FILES.txt), `verifier/` = frozen verifier output,
`trial.log` / `config.json` / `result.json` = Harbor records); 8 trials that ended in an infrastructure exception are under
`infra_failed/` (logs only) and are excluded from pass@k. `inputs/` holds the task definition the agents saw. Narrative results and audits:
`calibration/RESULTS-*.md`, `calibration/trajectory-digests/`.

| agent | trial | agent time | score (raw metric) | reward | passed | verifier | flags |
|---|---|---|---|---|---|---|---|
| codex | 83EytP9 | 90 min | 0.7143 | 0.7143 | False | re-verified (v0.2 suite, fresh sandbox) | shape_failures:C,F,H7,H8, judge_rejections:C,F,H7,H8 |
| codex | K6Hb4Co | 77 min | 1.0 | 1.0 | True | re-verified (v0.2 suite, fresh sandbox) |  |
| codex | RQ3r8zD | 82 min | 0.8571 | 0.8571 | False | re-verified (v0.2 suite, fresh sandbox) | shape_failures:C, judge_rejections:C,H3 |
| codex | xoWeMZ2 | 104 min | 0.9286 | 0.9286 | False | re-verified (v0.2 suite, fresh sandbox) | shape_failures:C |
| fable | Gj4rJgv | 129 min | 0.7857 | 0.7857 | False | re-verified (v0.2 suite, fresh sandbox) | judge_rejections:A |
| fable | LM6eV6W | 100 min | 0.6429 | 0.6429 | False | re-verified (v0.2 suite, fresh sandbox) | shape_failures:C,F,H7,H8, judge_rejections:F,H6,H7,H8 |
| fable | fAYdiX5 | 114 min | 1.0 | 1.0 | True | re-verified (v0.2 suite, fresh sandbox) |  |
| gemini | QvfLa5G | 50 min | 0.5 | 0.5 | False | re-verified (v0.2 suite, fresh sandbox) | shape_failures:C, judge_rejections:B,C,E,H3,H4, invalid_sets:H8 |
| gemini | uEdXH2x | 38 min | 0.9286 | 0.9286 | False | re-verified (v0.2 suite, fresh sandbox) | shape_failures:C |
| gemini | xm3wq9H | 51 min | 0.0714 | 0.0714 | False | re-verified (v0.2 suite, fresh sandbox) | provenance_failures:B,C,D,F,H1,H3,H4,H5,H6,H7, shape_failures:C,F,H7, judge_rejections:B,C,D,E,F,H1,H2,H3,H4,H5,H6,H7, invalid_sets:H8 |

## pass@k (scored trials)

- codex: 1/4
- fable: 1/3
- gemini: 0/3

## infrastructure failures (excluded)

| agent | trial | exception | message |
|---|---|---|---|
| codex | 8VM4Hb4 | ApiRateLimitError | Command failed (exit 1): if [ -s ~/.nvm/nvm.sh ]; then . ~/.nvm/nvm.sh; fi; codex exec --dangerously-bypass-approvals-an |
| gemini | US3qJwo | NetworkConnectionError | Command failed (exit 1): set -euo pipefail; curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | e |
| gemini | Ud6t5GU | NetworkConnectionError | Command failed (exit 1): set -euo pipefail; curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | e |
| gemini | XdyJ3p8 | NetworkConnectionError | Command failed (exit 1): set -euo pipefail; curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | e |
| gemini | HuXd6v4 | NetworkConnectionError | Command failed (exit 1): set -euo pipefail; curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | e |
| gemini | mjafGjU | NetworkConnectionError | Command failed (exit 1): set -euo pipefail; curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | e |
| gemini | sGfWopm | NetworkConnectionError | Command failed (exit 1): set -euo pipefail; curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | e |
| gemini | vteDbsh | infrastructure (manual: agent CLI stopped by gateway rate limiting) |  |

## Expert review (task owner, blinded drawings, 2026-09-06)
Accepted: `codex__K6Hb4Co`, `fable__fAYdiX5`, `fable__Gj4rJgv`. Rejected: all other submissions. Failure patterns: drift
trajectories (row C) that do not run straight between edge turns; linear cores (F, H7, H8) without the sharp cusp at the ends
of each run. Under the v0.1 grader the final pass (programmatic pass AND expert acceptance) was `fable__fAYdiX5` and
`codex__K6Hb4Co` (Fable 1/3, Codex 1/3, Gemini 0/3); `fable__Gj4rJgv` was accepted by the expert but failed the verifier (12/14).

## v0.2 suite (the `verifier/` directories above)
`inputs/` is the v0.1 task definition the agents worked from (instruction, task.toml, task.yaml, README as of 2026-09-05);
the task itself has since moved to v0.2 (`tasks/spiral-tip-patterns/`).
The verifier output of every trial is the v0.2 suite (human-calibrated shape rules + VLM judge, `tests/` of the task),
re-run on the captured submissions in fresh Modal sandboxes on 2026-09-06/07 (`jobs/t3t2-reverify-v02`); the trial-time v0.1
verdicts are kept under `verifier_original/`. v0.2 passes: `fable__fAYdiX5`, `codex__K6Hb4Co`. Passes that the expert also accepted: `fable__fAYdiX5`, `codex__K6Hb4Co`.
Tally under v0.2 (scored trials): Fable 1/3, Codex 1/4 (1/3 at k = 3; the fourth Codex trial replaced the
infrastructure-cut 8VM4Hb4, whose v0.2 re-verification is 8/14 like its v0.1 one), Gemini 0/3. Agreement between the v0.2 pass verdict and the expert: 10/11 submissions
(the exception is `fable__Gj4rJgv`, accepted by the expert but classified C instead of L on hidden sets H7 and H8). Details:
`calibration/RESULTS-2026-09-06-tier3-task2-v02.md`.
