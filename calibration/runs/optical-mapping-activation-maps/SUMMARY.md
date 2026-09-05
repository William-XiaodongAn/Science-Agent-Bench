# optical-mapping-activation-maps: calibration runs

9 scored trials (one directory each: `trajectory/` = agent log + Harbor trajectory, `workspace/` = the agent's workspace as it left it
(its `submission/` plus scratch scripts; shipped data/baseline/tool, frames and files above the size cap omitted, see SKIPPED_LARGE_FILES.txt), `verifier/` = frozen verifier output,
`trial.log` / `config.json` / `result.json` = Harbor records); 0 trials that ended in an infrastructure exception are under
`infra_failed/` (logs only) and are excluded from pass@k. `inputs/` holds the task definition the agents saw. Narrative results and audits:
`calibration/RESULTS-*.md`, `calibration/trajectory-digests/`.

| agent | trial | agent time | score (raw metric) | reward | passed | verifier | flags |
|---|---|---|---|---|---|---|---|
| codex | brvm6rA | 7 min | None | 0.0 | False | harbor | invalid_submission, mask_coverage_below_gate |
| codex | n9VV3Ek | 6 min | 1.1684 | 0.9645 | True | harbor |  |
| codex | oyMV4Wg | 8 min | None | 0.0 | False | harbor | invalid_submission, mask_coverage_below_gate |
| fable | 4HtdEYJ | 21 min | 1.1688 | 0.9645 | True | harbor |  |
| fable | MiZf4zM | 17 min | 0.8055 | 0.9838 | True | harbor |  |
| fable | gs2BQC9 | 12 min | 1.0126 | 0.9728 | True | harbor |  |
| gemini | Ky2uo8Z | 8 min | 1.5406 | 0.9447 | False | harbor | apd80_above_gate |
| gemini | MV8FKV4 | 13 min | None | 0.0 | False | harbor | invalid_submission, mask_iou_below_gate |
| gemini | rVDA5tv | 9 min | None | 0.0 | False | harbor | invalid_submission, mask_iou_below_gate |

## pass@k (scored trials)

- codex: 1/3
- fable: 3/3
- gemini: 0/3
