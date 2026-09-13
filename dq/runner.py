"""Run all registered checks on a task and build the report."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import Any

import yaml

from . import checks as _checks  # noqa: F401  (populates the registry)
from .checks.base import REGISTRY
from .loader import TaskBundle
from .model import Report, Severity, Status, Verdict

DEFAULT_CONFIG = Path(__file__).with_name("config.yaml")


def load_config(path: str | None = None) -> dict[str, Any]:
    with open(path or DEFAULT_CONFIG) as fh:
        return yaml.safe_load(fh) or {}


def verdict_for(results) -> tuple[Verdict, list[str]]:
    reasons = []
    fail = False
    review = False
    for r in results:
        if r.severity in (Severity.OFF, Severity.INFO) or r.status in (Status.SKIP, Status.INFO, Status.PASS):
            continue
        if r.status == Status.ERROR:
            review = True
            reasons.append(f"[{r.id}] check error: {r.reason}")
        elif r.status == Status.FAIL and r.severity == Severity.BLOCK:
            fail = True
            reasons.append(f"[{r.id}] FAIL (blocking): {r.reason}")
        elif r.status in (Status.FAIL, Status.WARN):
            review = True
            reasons.append(f"[{r.id}] {r.status.value.upper()}: {r.reason}")
    if fail:
        return Verdict.FAIL, reasons
    if review:
        return Verdict.NEEDS_REVIEW, reasons
    return Verdict.PASS, ["all blocking and warning checks passed"]


def run_bundle(b: TaskBundle, cfg: dict[str, Any], options: dict[str, Any]) -> Report:
    enabled = {k for k in ("network", "llm", "exec") if options.get(k)}
    overrides = cfg.get("severity_overrides", {}) or {}
    only = set(options.get("only") or [])
    rep = Report(task_name=b.name, source=b.source, task_root=str(b.root), started_at=dt.datetime.now().isoformat(timespec="seconds"), options=dict(options))
    for cls in REGISTRY:
        chk = cls()
        if only and chk.id not in only:
            continue
        sev = Severity(overrides.get(chk.id, chk.default_severity.value))
        if sev == Severity.OFF:
            continue
        if chk.needs - enabled:
            r = chk.skip(f"disabled (needs {', '.join(sorted(chk.needs - enabled))}); enable with the matching option")
        else:
            r = chk.timed(b, cfg)
        r.severity = sev
        rep.results.append(r)
    rep.verdict, rep.verdict_reasons = verdict_for(rep.results)
    rep.counts = {s.value: sum(1 for r in rep.results if r.status == s) for s in Status}
    rep.finished_at = dt.datetime.now().isoformat(timespec="seconds")
    rep.meta = {"n_files": len(b.files), "declared_metadata": (b.toml or {}).get("metadata", {}) if isinstance((b.toml or {}).get("metadata"), dict) else {}}
    return rep


def run_task(source: str, subdir: str | None = None, config_path: str | None = None, options: dict[str, Any] | None = None) -> Report:
    options = {"network": True, "llm": False, "exec": False, **(options or {})}
    cfg = load_config(config_path)
    b = TaskBundle.from_source(source, subdir=subdir, workdir=os.environ.get("DQ_WORKDIR"))
    try:
        return run_bundle(b, cfg, options)
    finally:
        if not options.get("keep_temp"):
            b.cleanup()
