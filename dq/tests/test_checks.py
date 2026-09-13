from __future__ import annotations

from pathlib import Path

from dq.loader import TaskBundle
from dq.model import Status, Verdict
from dq.runner import load_config, run_bundle

from .conftest import make_task

CFG = load_config()
OPTS = {"network": False, "llm": False, "exec": False}


def run(path: Path):
    rep = run_bundle(TaskBundle(path, str(path)), CFG, OPTS)
    return rep, {r.id: r for r in rep.results}


def test_good_task_passes(good_task):
    rep, res = run(good_task)
    blocking_fails = [r.id for r in rep.results if r.status == Status.FAIL and r.severity.value == "block"]
    assert not blocking_fails, blocking_fails
    assert rep.verdict in (Verdict.PASS, Verdict.NEEDS_REVIEW)
    assert res["leakage.sealed_not_in_environment"].status == Status.PASS
    assert res["instruction.deliverables_match_verifier"].status == Status.PASS
    assert res["verifier.test_sh_sanity"].status == Status.PASS
    assert res["category.domain_declared_valid"].status == Status.PASS


def test_sealed_leak_fails(tmp_path):
    rep, res = run(make_task(tmp_path, leak_sealed=True))
    assert res["leakage.sealed_not_in_environment"].status == Status.FAIL
    assert rep.verdict == Verdict.FAIL


def test_dockerfile_copies_tests_fails(tmp_path):
    rep, res = run(make_task(tmp_path, copy_tests=True))
    assert res["leakage.dockerfile_no_tests_solution"].status == Status.FAIL
    assert rep.verdict == Verdict.FAIL


def test_missing_tests_fails(tmp_path):
    rep, res = run(make_task(tmp_path, missing_tests=True))
    assert res["structure.required_files"].status == Status.FAIL
    assert rep.verdict == Verdict.FAIL


def test_unannounced_deliverable_flagged(tmp_path):
    rep, res = run(make_task(tmp_path, unannounced_read=True))
    r = res["instruction.deliverables_match_verifier"]
    assert r.status == Status.WARN and "hidden_config.json" in " ".join(r.evidence)
    assert rep.verdict == Verdict.NEEDS_REVIEW


def test_disclosed_quality_gate_warns(tmp_path):
    rep, res = run(make_task(tmp_path, disclosed_quality_gate=True))
    assert res["leakage.gate_values_disclosed"].status == Status.WARN


def test_ask_user_warns(tmp_path):
    rep, res = run(make_task(tmp_path, ask_user=True))
    assert res["instruction.no_ask_user"].status == Status.WARN


def test_trusting_agent_scores_flagged(tmp_path):
    rep, res = run(make_task(tmp_path, trust_scores=True))
    assert res["verifier.no_trust_in_agent_scores"].status in (Status.FAIL, Status.INFO)
    assert res["verifier.no_trust_in_agent_scores"].status == Status.FAIL


def test_broken_grader_fails(tmp_path):
    rep, res = run(make_task(tmp_path, broken_grader=True))
    assert res["verifier.graders_compile"].status == Status.FAIL
    assert rep.verdict == Verdict.FAIL


def test_zip_source(tmp_path):
    import shutil
    t = make_task(tmp_path)
    z = shutil.make_archive(str(tmp_path / "task"), "zip", root_dir=tmp_path, base_dir=t.name)
    b = TaskBundle.from_source(z)
    assert b.root.name == t.name and b.exists("task.toml")
    b.cleanup()
