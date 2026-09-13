"""Result and report data structures."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"
    SKIP = "skip"
    ERROR = "error"


class Severity(str, Enum):
    BLOCK = "block"        # a FAIL here fails the task
    WARN = "warn"          # a FAIL/WARN here sends the task to review
    INFO = "info"          # never changes the verdict
    ADVISORY = "advisory"  # LLM-judged: never blocks, always shown to the reviewer
    OFF = "off"            # check disabled by configuration


class Verdict(str, Enum):
    PASS = "PASS"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAIL = "FAIL"


@dataclass
class CheckResult:
    id: str
    name: str
    category: str
    status: Status
    reason: str
    severity: Severity = Severity.WARN
    evidence: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    duration_sec: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["severity"] = self.severity.value
        return d


@dataclass
class Report:
    task_name: str
    source: str
    task_root: str
    started_at: str
    finished_at: str = ""
    verdict: Verdict = Verdict.NEEDS_REVIEW
    verdict_reasons: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    results: list[CheckResult] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_name": self.task_name, "source": self.source, "task_root": self.task_root,
            "started_at": self.started_at, "finished_at": self.finished_at,
            "verdict": self.verdict.value, "verdict_reasons": self.verdict_reasons, "counts": self.counts,
            "options": self.options, "meta": self.meta, "results": [r.to_dict() for r in self.results],
        }
