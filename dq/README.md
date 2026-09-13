# dq: data-quality verifier for Harbor-format science tasks

`dq` is the automatic first filter in front of the human review committee. Give it a Harbor task (a folder, a `.zip`, or
a git URL) and it runs a battery of checks, each returning **pass / warn / fail with a reason and evidence**, and an
overall verdict:

- **FAIL**: a blocking check failed (missing verifier, task.toml invalid, ground truth shipped to the agent, verifier
  cannot run, solution copies the answer, verifier reads a deliverable the instruction never names, …). Fix before review.
- **NEEDS_REVIEW**: warnings or advisory findings; the committee sees the reasons.
- **PASS**: nothing mechanical is wrong. This is not an endorsement of the science; domain experts review next.

It is meant to be modified: every check is a small class in `dq/checks/`, severities and taxonomies live in
`dq/config.yaml`, and the LLM judge's rubric is plain text in `dq/checks/llm_judge.py`. It deliberately stays light on
domain knowledge, which is the reviewers' job.

## Install and run

```bash
pip install -r dq/requirements.txt          # pyyaml, fastapi, uvicorn, python-multipart
pip install harbor                           # optional: full task.toml schema validation and --exec checks
python -m dq list-checks
python -m dq run tasks/spiral-tip-patterns --out dq_runs/spiral        # static checks + URL check
python -m dq run tasks/spiral-tip-patterns --llm                       # + advisory LLM judge
python -m dq run https://github.com/harbor-framework/terminal-bench-science --subdir tasks/life-sciences/ambient-rna-correction --no-urls
python -m dq run my-task.zip --exec                                    # + docker build, oracle passes, nop fails (needs harbor + Docker)
python -m dq corpus /path/to/repo --glob 'tasks/*/*' --out dq_runs/corpus   # every task, with a summary of which checks fire
python -m dq serve                                                     # web UI at http://127.0.0.1:8765
```

Run from the repository root (`python -m dq …`), or `pip install -e .` once a `pyproject.toml` is added.

Credentials for the LLM judge come from the environment only: `DQ_LLM_API_KEY` and `DQ_LLM_BASE_URL` (falling back to
`ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL`), model from `DQ_LLM_MODEL` or `config.yaml`. Nothing is read from files
or command lines. `--exec` uses the `harbor` CLI with the backend in `DQ_HARBOR_ENV` (default `docker`) and passes
`DQ_HARBOR_ENV_FILE` as `--env-file` when set.

## What is checked

| category | checks | typical severity |
|---|---|---|
| structure | required files (task.toml, instruction.md, environment, tests/test.sh, solution/); task.toml parses; Harbor `TaskConfig` schema; name matches folder; stray, junk or oversized files | block / warn |
| config | description, authors, domain metadata; agent and verifier timeouts (and agreement with hours stated in the instruction); cpus/memory/gpus vs the text; network policy (agent mode explicit, separate verifier not public); separate-verifier tasks declare `artifacts` and `tests/Dockerfile`; environment variables the grader reads are declared in `[verifier.env]`, `${VAR}` templates flagged | warn / info |
| instruction | length and named deliverables and a scoring sentence; **prompt–artifacts–verifier coherence**: every agent-produced file the verifier opens is named in the instruction (FAIL if not), deliverables the verifier ignores (info); input files the instruction points at exist in `environment/` (or the Dockerfile fetches them); no verifier-side paths (`tests/`, `sealed`, `/logs/verifier`) in the text; no "ask the user"; absolute deliverable paths | block / warn / info |
| verifier | `tests/test.sh` runnable (shebang, referenced scripts shipped, reward channel written, fail-fast, `bash -n`); graders compile; reward written and clipped/binarised; no unseeded randomness or clock dependence; no trial-time network fetches (model-API judges are noted, not failed); reward not copied from an agent-written `score` field; agent code executed with a timeout and reduced privileges; files referenced under `/tests` are shipped | block / warn |
| leakage / reward hacking | tests/ data byte-identical to files in `environment/` or `solution/` (FAIL); environment Dockerfile copies `tests/` or `solution/` (FAIL); sealed values quoted in the instruction; verifier gate values quoted in the instruction (quality gates → warn, primary pass bar → info); solution reads `tests/` or writes the reward channel (FAIL); solution pastes large literal data; canary present; answer-looking file names in the workspace | block / warn / info |
| solution | `solve.sh` runnable, scripts present and compile; solution mentions the deliverables the verifier reads | warn / info |
| category | declared domain maps onto the taxonomy; declared tier valid; keyword-inferred domain agrees; tier hints (generator for T1, expert reference for T2, open-ended language for T3) | warn / info |
| urls | every link in instruction/README/task files resolves (403/429 reported as bot-blocked, not broken) | warn |
| execution (`--exec`) | environment builds; oracle reaches the pass reward; doing nothing does not | block |
| llm (`--llm`, advisory) | solvable; verifiable; best-fit domain and tier vs declared; the capability an agent must gain and whether the task is agent-feasible (a wet-lab, physical-instrument or human-in-the-loop step is infeasible); leakage/hacking notes; clarity issues; recommendation with confidence | advisory (never blocks) |

Each check's `description` is shown by `python -m dq list-checks` and in the report.

## Adding or changing a check

```python
# dq/checks/my_checks.py
from ..model import Severity
from .base import Check, register

@register
class MyCheck(Check):
    id = "mycat.my_check"; name = "One-line name"; category = "mycat"; default_severity = Severity.WARN
    def run(self, b, cfg):
        hits = b.grep(r"TODO", b.tests_files)           # b: TaskBundle (files, text(), grep(), toml, instruction, ...)
        return self.warn("TODOs in the verifier", evidence=[f"{f}:{ln}" for f, ln, _ in hits]) if hits else self.ok("no TODOs")
```

Import the module in `dq/checks/__init__.py`. Change a severity without touching code in `config.yaml`
(`severity_overrides: {mycat.my_check: block}`); switch a check off with `off`. Taxonomy, keywords, URL and LLM settings
are also in `config.yaml`.

## Web UI

`python -m dq serve` starts a small FastAPI app: upload a zip of a task folder or paste a path / git URL, tick the
optional LLM and execution checks, and browse the report (filter by status, download `report.md` / `.json` / `.html`).
Runs are stored under `dq_runs/` (`DQ_RUNS_DIR`).

## Tests and calibration

`pytest dq/tests` exercises synthetic tasks (a clean one; sealed data leaked into the workspace; Dockerfile copying
tests/; missing verifier; a deliverable read but never announced; a disclosed quality gate; "ask the user"; a reward
copied from the agent's file; a grader that does not compile; loading from zip).

`CALIBRATION.md` records the runs on this repository's tasks and on Terminal-Bench-Science's 70 public tasks, which
checks fired and why, and what was changed as a result (after calibration: our four tasks pass; TB-Science 47 pass, 23
need review, 0 fail).

## Design notes and credits

The shape follows the pattern of internal data-quality tooling at Scale (declarative requirements with an output
schema, an assessment that composes them into a decision, CLI plus web app), rewritten from scratch for Harbor tasks;
no internal code is included. Several checks are adapted from the public CI of
[Terminal-Bench-Science](https://github.com/harbor-framework/terminal-bench-science) (test-file references,
separate-verifier configuration, trial-time network fetches, compose host binds, near-duplicate detection), and its
implementation rubric informed the LLM judge's criteria. Harbor's own `TaskConfig` model is used for schema validation
when the package is installed.
