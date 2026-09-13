"""Checks adapted from Terminal-Bench-Science's CI (compose host binds, near-duplicate tasks)."""
from __future__ import annotations

import glob
import math
import os
import re
from collections import Counter

from ..model import Severity
from .base import Check, cfg_get, register


@register
class ComposeHostBinds(Check):
    id = "structure.compose_no_host_binds"
    name = "docker-compose files use named volumes, not host bind mounts"
    category = "structure"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        files = [f for f in b.files if re.search(r"(docker-)?compose.*\.ya?ml$", f)]
        if not files:
            return self.skip("no compose file")
        hits = b.grep(r"^\s*-\s*[\"']?(\.{1,2}/|/|~)[^:]*:", files)
        if hits:
            return self.warn("host bind mounts in a compose file are unsafe and non-portable in a sandbox; use named volumes", evidence=[f"{f}:{ln}: {l}" for f, ln, l in hits])
        return self.ok(f"{len(files)} compose file(s) without host bind mounts")


def _tf(text: str) -> Counter:
    words = re.findall(r"[a-z][a-z0-9_]{2,}", text.lower())
    stop = {"the", "and", "for", "with", "that", "this", "are", "from", "you", "your", "must", "should", "file", "files", "task", "use", "using", "each", "all", "any", "not", "into", "than", "then", "when", "which", "will", "can", "one", "two", "have", "has", "its", "per", "may", "only", "also", "under", "over", "via"}
    return Counter(w for w in words if w not in stop)


def _cos(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    num = sum(v * b.get(k, 0) for k, v in a.items())
    return num / (math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values())))


@register
class NearDuplicate(Check):
    id = "structure.near_duplicate"
    name = "Instruction is not a near-duplicate of a task in the reference corpora"
    category = "structure"
    default_severity = Severity.WARN
    description = "TF cosine similarity of instruction.md against instruction.md files under the directories in config similarity.reference_dirs."

    def run(self, b, cfg):
        dirs = cfg_get(cfg, "similarity.reference_dirs", []) or []
        dirs = [os.path.expanduser(d) for d in dirs]
        thr = float(cfg_get(cfg, "similarity.threshold", 0.8))
        if not dirs or not b.instruction.strip():
            return self.skip("no similarity.reference_dirs configured")
        me = _tf(b.instruction)
        best = []
        for d in dirs:
            for f in glob.glob(os.path.join(d, "**", "instruction.md"), recursive=True):
                if os.path.realpath(os.path.dirname(f)) == os.path.realpath(str(b.root)):
                    continue
                try:
                    sim = _cos(me, _tf(open(f, encoding="utf-8", errors="replace").read()))
                except OSError:
                    continue
                best.append((sim, f))
        if not best:
            return self.skip("no reference instructions found")
        best.sort(reverse=True)
        top = [f"{s:.2f} {os.path.relpath(f)}" for s, f in best[:3]]
        if best[0][0] >= thr:
            return self.warn(f"instruction is {best[0][0]:.2f} similar to an existing task (threshold {thr})", evidence=top)
        return self.ok(f"max similarity {best[0][0]:.2f} over {len(best)} reference task(s)", evidence=top)
