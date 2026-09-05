# zebrafish-voltage-forecast: calibration runs

9 scored trials (one directory each: `trajectory/` = agent log + Harbor trajectory, `workspace/` = the agent's workspace as it left it
(its `submission/` plus scratch scripts; shipped data/baseline/tool, frames and files above the size cap omitted, see SKIPPED_LARGE_FILES.txt), `verifier/` = frozen verifier output,
`trial.log` / `config.json` / `result.json` = Harbor records); 3 trials that ended in an infrastructure exception are under
`infra_failed/` (logs only) and are excluded from pass@k. `inputs/` holds the task definition the agents saw. Narrative results and audits:
`calibration/RESULTS-*.md`, `calibration/trajectory-digests/`.

| agent | trial | agent time | score (raw metric) | reward | passed | verifier | flags |
|---|---|---|---|---|---|---|---|
| codex | UkkQsXJ | 501 min | 0.07479 | 0.7525 | True | local replay (frozen verifier, clean image) |  |
| codex | kLBeUaQ | 263 min | 0.07373 | 0.756 | True | local replay (frozen verifier, clean image) |  |
| codex | wqgaM3X | 65 min | 0.0695 | 0.77 | True | harbor |  |
| fable | G3PNHFG | 58 min | 0.07388 | 0.7555 | True | harbor |  |
| fable | W2CTtfk | 59 min | 0.073 | 0.7584 | True | harbor |  |
| fable | n3d5iUi | 62 min | 0.07326 | 0.7576 | True | harbor |  |
| gemini | 4NrwYaN | 26 min | 0.08802 | 0.7087 | False | harbor |  |
| gemini | 9drpmVf | 35 min | 0.10079 | 0.6665 | False | local replay (frozen verifier, clean image) |  |
| gemini | tbAYXxh | 17 min | 0.17311 | 0.4272 | False | harbor |  |

## pass@k (scored trials)

- codex: 3/3
- fable: 3/3
- gemini: 0/3

## infrastructure failures (excluded)

| agent | trial | exception | message |
|---|---|---|---|
| fable | TNrs2ki | AgentTimeoutError | Agent execution timed out after 10800.0 seconds |
| fable | r2Er4ki | ConnectionError | [Errno 8] nodename nor servname provided, or not known |
| codex | 4Z8yo5o | ApiRateLimitError | Command failed (exit 1): if [ -s ~/.nvm/nvm.sh ]; then . ~/.nvm/nvm.sh; fi; codex exec --dangerously-bypass-approvals-an |

Not listed above: Fable replacement trial `RsEXQGD` (launched 2026-09-04 17:11) whose Modal stream hung 13 h past the deadline and was killed before any result was written; see `../RESULTS-2026-09-05-tier3-v10.md`.
