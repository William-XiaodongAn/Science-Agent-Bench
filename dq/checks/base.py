"""Check base class and registry. Add a check by subclassing Check in any module under dq/checks and decorating with
@register; the module must be imported from dq/checks/__init__.py."""
from __future__ import annotations

import time
from typing import Any, Iterable

from ..loader import TaskBundle
from ..model import CheckResult, Severity, Status

REGISTRY: list[type["Check"]] = []


def register(cls: type["Check"]) -> type["Check"]:
    REGISTRY.append(cls)
    return cls


class Check:
    id: str = "base"
    name: str = "base check"
    category: str = "general"
    default_severity: Severity = Severity.WARN
    needs: frozenset[str] = frozenset()   # subset of {"network", "llm", "exec"}; the runner skips when the option is off
    description: str = ""

    def run(self, b: TaskBundle, cfg: dict[str, Any]) -> CheckResult:  # pragma: no cover - abstract
        raise NotImplementedError

    def result(self, status: Status, reason: str, evidence: Iterable[str] | None = None, data: dict | None = None) -> CheckResult:
        return CheckResult(id=self.id, name=self.name, category=self.category, status=status, reason=reason,
                           severity=self.default_severity, evidence=list(evidence or [])[:25], data=data or {})

    def ok(self, reason: str, evidence=None, data=None) -> CheckResult:
        return self.result(Status.PASS, reason, evidence, data)

    def warn(self, reason: str, evidence=None, data=None) -> CheckResult:
        return self.result(Status.WARN, reason, evidence, data)

    def fail(self, reason: str, evidence=None, data=None) -> CheckResult:
        return self.result(Status.FAIL, reason, evidence, data)

    def info(self, reason: str, evidence=None, data=None) -> CheckResult:
        return self.result(Status.INFO, reason, evidence, data)

    def skip(self, reason: str) -> CheckResult:
        return self.result(Status.SKIP, reason)

    def timed(self, b: TaskBundle, cfg: dict[str, Any]) -> CheckResult:
        t0 = time.time()
        try:
            r = self.run(b, cfg)
        except Exception as e:  # noqa: BLE001 - a crashing check must not hide the other results
            r = self.result(Status.ERROR, f"check raised {type(e).__name__}: {str(e)[:200]}")
        r.duration_sec = round(time.time() - t0, 3)
        return r


def cfg_get(cfg: dict[str, Any], path: str, default=None):
    cur: Any = cfg
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
