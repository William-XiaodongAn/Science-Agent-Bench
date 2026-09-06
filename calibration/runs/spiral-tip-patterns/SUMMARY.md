# spiral-tip-patterns: calibration runs

10 scored trials (one directory each: `trajectory/` = agent log + Harbor trajectory, `workspace/` = the agent's workspace as it left it
(its `submission/` plus scratch scripts; shipped data/baseline/tool, frames and files above the size cap omitted, see SKIPPED_LARGE_FILES.txt), `verifier/` = frozen verifier output,
`trial.log` / `config.json` / `result.json` = Harbor records); 8 trials that ended in an infrastructure exception are under
`infra_failed/` (logs only) and are excluded from pass@k. `inputs/` holds the task definition the agents saw. Narrative results and audits:
`calibration/RESULTS-*.md`, `calibration/trajectory-digests/`.

| agent | trial | agent time | score (raw metric) | reward | passed | verifier | flags |
|---|---|---|---|---|---|---|---|
| codex | 83EytP9 | 90 min | 1.0 | 1.0 | True | re-verified (final grader, fresh sandbox) |  |
| codex | K6Hb4Co | 77 min | 1.0 | 1.0 | True | re-verified (final grader, fresh sandbox) |  |
| codex | RQ3r8zD | 82 min | 0.9286 | 0.9286 | True | re-verified (final grader, fresh sandbox) |  |
| codex | xoWeMZ2 | 104 min | 1.0 | 1.0 | True | re-verified (final grader, fresh sandbox) |  |
| fable | Gj4rJgv | 129 min | 0.8571 | 0.8571 | False | re-verified (final grader, fresh sandbox) |  |
| fable | LM6eV6W | 100 min | 0.8571 | 0.8571 | False | re-verified (final grader, fresh sandbox) |  |
| fable | fAYdiX5 | 114 min | 1.0 | 1.0 | True | re-verified (final grader, fresh sandbox) |  |
| gemini | QvfLa5G | 50 min | 0.5 | 0.5 | False | re-verified (final grader, fresh sandbox) | invalid_sets:H8 |
| gemini | uEdXH2x | 38 min | 1.0 | 1.0 | True | re-verified (final grader, fresh sandbox) |  |
| gemini | xm3wq9H | 51 min | 0.2143 | 0.2143 | False | re-verified (final grader, fresh sandbox) | provenance_failures:B,C,D,F,H1,H3,H4,H5,H6,H7, invalid_sets:H8 |

## pass@k (scored trials)

- codex: 4/4
- fable: 1/3
- gemini: 1/3

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
of each run. Final pass = programmatic pass AND expert acceptance: fable__fAYdiX5, codex__K6Hb4Co (Fable 1/3, Codex 1/3,
Gemini 0/3); fable__Gj4rJgv was accepted by the expert but failed the verifier (12/14).
