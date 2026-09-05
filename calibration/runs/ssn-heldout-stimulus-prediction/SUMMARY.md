# ssn-heldout-stimulus-prediction: calibration runs

9 scored trials (one directory each: `trajectory/` = agent log + Harbor trajectory, `workspace/` = the agent's workspace as it left it
(its `submission/` plus scratch scripts; shipped data/baseline/tool, frames and files above the size cap omitted, see SKIPPED_LARGE_FILES.txt), `verifier/` = frozen verifier output,
`trial.log` / `config.json` / `result.json` = Harbor records); 5 trials that ended in an infrastructure exception are under
`infra_failed/` (logs only) and are excluded from pass@k. `inputs/` holds the task definition the agents saw. Narrative results and audits:
`calibration/RESULTS-*.md`, `calibration/trajectory-digests/`.

| agent | trial | agent time | score (raw metric) | reward | passed | verifier | flags |
|---|---|---|---|---|---|---|---|
| codex | CKfPbib | 51 min | 0.38447 | 0.6565 | True | harbor |  |
| codex | CS8SF8M | 191 min | 0.58552 | 0.4729 | False | harbor |  |
| codex | wGzsSc6 | 22 min | 0.45489 | 0.5922 | False | harbor |  |
| fable | 8qdqnXA | 38 min | 0.43767 | 0.6079 | True | harbor |  |
| fable | fzwQrV5 | 190 min | 0.44947 | 0.5971 | False | harbor |  |
| fable | qzDqt5D | 48 min | 0.46337 | 0.5844 | False | harbor |  |
| gemini | CQHKvBg | 39 min | 0.40807 | 0.6349 | True | harbor |  |
| gemini | SMcfcpw | 120 min | None | 0.0 | False | harbor | invalid_submission, r_pred_missing |
| gemini | T73XqyH | 108 min | 0.90552 | 0.1808 | False | harbor |  |

## pass@k (scored trials)

- codex: 1/3
- fable: 1/3
- gemini: 1/3

## infrastructure failures (excluded)

| agent | trial | exception | message |
|---|---|---|---|
| fable | imeig8z | NonZeroAgentExitCodeError | Command failed (exit 137): export PATH="$HOME/.local/bin:$PATH"; harbor_claude_code_instruction_1dcf69b0350f49b7b95c3231 |
| fable | ps8dLAL | EnvironmentStartTimeoutError | Environment start timed out after 3600.0 seconds |
| codex | KD5uwky | ApiRateLimitError | Command failed (exit 1): if [ -s ~/.nvm/nvm.sh ]; then . ~/.nvm/nvm.sh; fi; codex exec --dangerously-bypass-approvals-an |
| codex | NiSw5Kb | ApiRateLimitError | Command failed (exit 1): if [ -s ~/.nvm/nvm.sh ]; then . ~/.nvm/nvm.sh; fi; codex exec --dangerously-bypass-approvals-an |
| codex | PEgxLVt | ApiRateLimitError | Command failed (exit 1): if [ -s ~/.nvm/nvm.sh ]; then . ~/.nvm/nvm.sh; fi; codex exec --dangerously-bypass-approvals-an |
