"""Synthetic fixture tasks for the dq checks."""
from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

TOML = textwrap.dedent('''
    schema_version = "1.3"
    [task]
    name = "fixture-bench/{name}"
    description = "Fit the hidden parameter of a synthetic system."
    authors = [{{ name = "Fixture Author" }}]
    keywords = ["fixture"]
    [metadata]
    domain = "physics"
    tier = "T1"
    [agent]
    timeout_sec = 3600.0
    [verifier]
    timeout_sec = 600.0
    [verifier.env]
    PASS_RMSE = "0.444"
    [environment]
    network_mode = "no-network"
    cpus = 2
    memory_mb = 4096
    ''')

INSTRUCTION = textwrap.dedent('''
    # Recover the damping coefficient
    A damped oscillator was simulated and sampled at 200 Hz. The observed series is at
    `/workspace/data/observed.csv` (columns t, x). The system is x'' + c x' + k x = 0 with k = 4.0 (rad/s)^2.

    ## Deliverables
    Write `/workspace/submission/estimate.json` with the field `c` (the damping coefficient) and
    `/workspace/submission/methods.md` describing your method. Keep your script in `/workspace/submission/`.

    ## How you are scored
    The verifier compares your `c` with the sealed value; the relative error must be below the bar.
    The run is unattended: state assumptions instead of asking questions. You have 1 h.
    ''')

TEST_SH = "#!/bin/bash\nset -euo pipefail\nmkdir -p /logs/verifier\npython3 /tests/grade.py\n"
GRADE = textwrap.dedent('''
    import json, os
    SUB = os.environ.get("SUBMISSION_DIR", "/workspace/submission")
    OUT = os.environ.get("VERIFIER_LOG_DIR", "/logs/verifier")
    truth = json.load(open("/tests/sealed/truth.json"))["c"]
    bar = float(os.environ.get("PASS_RMSE", "0.444"))
    try:
        est = float(json.load(open(os.path.join(SUB, "estimate.json")))["c"])
        err = abs(est - truth) / truth
        reward = 1.0 if err < bar and os.path.exists(os.path.join(SUB, "methods.md")) else 0.0
    except Exception:
        reward = 0.0
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "reward.txt"), "w").write(f"{reward:.4f}\\n")
    ''')
SOLVE = "#!/bin/bash\nset -e\nmkdir -p /workspace/submission\npython3 /solution/fit.py\n"
FIT = "import json, numpy as np\nprint('fit')\njson.dump({'c': 0.31}, open('/workspace/submission/estimate.json','w'))\nopen('/workspace/submission/methods.md','w').write('least squares fit')\n"
DOCKERFILE = "FROM python:3.12-slim\nRUN pip install numpy\nCOPY workspace /workspace\nWORKDIR /workspace\n"


def make_task(root: Path, name: str = "damped-oscillator", *, leak_sealed=False, copy_tests=False, missing_tests=False,
              unannounced_read=False, disclosed_quality_gate=False, ask_user=False, trust_scores=False, broken_grader=False) -> Path:
    t = root / name
    (t / "environment" / "workspace" / "data").mkdir(parents=True)
    (t / "tests" / "sealed").mkdir(parents=True)
    (t / "solution").mkdir(parents=True)
    toml = TOML.format(name=name)
    if disclosed_quality_gate:
        toml = toml.replace('PASS_RMSE = "0.444"\n', 'PASS_RMSE = "0.444"\nMASK_SMOOTHNESS_MAX = "0.123"\n')
    (t / "task.toml").write_text(toml)
    instr = INSTRUCTION
    if disclosed_quality_gate:
        instr += "\nYour mask smoothness must be at most 0.123.\n"
    if ask_user:
        instr += "\nIf anything is unclear, ask the user before proceeding.\n"
    (t / "instruction.md").write_text(instr)
    (t / "environment" / "Dockerfile").write_text(DOCKERFILE + ("COPY ../tests /tests\n" if copy_tests else ""))
    (t / "environment" / "workspace" / "data" / "observed.csv").write_text("t,x\n0,1.0\n0.005,0.99\n")
    if not missing_tests:
        (t / "tests" / "test.sh").write_text(TEST_SH)
        g = GRADE
        if unannounced_read:
            g += "\nextra = json.load(open(os.path.join(SUB, 'hidden_config.json')))\n"
        if trust_scores:
            g += "\nsub = json.load(open(os.path.join(SUB, 'estimate.json')))\nreward = sub['score']\nopen(os.path.join(OUT, 'reward.txt'), 'w').write(str(reward))\n"
        if broken_grader:
            g += "\ndef broken(:\n"
        (t / "tests" / "grade.py").write_text(g)
    (t / "tests" / "sealed" / "truth.json").write_text('{"c": 0.3125}')
    if leak_sealed:
        (t / "environment" / "workspace" / "data" / "truth.json").write_text('{"c": 0.3125}')
    (t / "solution" / "solve.sh").write_text(SOLVE)
    (t / "solution" / "fit.py").write_text(FIT)
    os.chmod(t / "solution" / "solve.sh", 0o755)
    return t


@pytest.fixture
def good_task(tmp_path):
    return make_task(tmp_path)
