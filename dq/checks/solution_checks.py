"""Reference-solution (oracle) checks."""
from __future__ import annotations

import py_compile
import re
import subprocess
import tempfile

from ..model import Severity
from .base import Check, register


@register
class OracleValid(Check):
    id = "solution.oracle_valid"
    name = "solve.sh is runnable and its scripts are present and compile"
    category = "solution"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        if not b.exists("solution/solve.sh"):
            return self.warn("no solution/solve.sh: solvability is asserted, not demonstrated")
        t = b.text("solution/solve.sh")
        problems = []
        if not t.lstrip().startswith("#!"):
            problems.append("solve.sh has no shebang")
        r = subprocess.run(["bash", "-n", str(b.root / "solution/solve.sh")], capture_output=True, text=True)
        if r.returncode != 0:
            problems.append(f"bash -n: {r.stderr.strip()[:160]}")
        refs = re.findall(r"(?:python3?|bash|sh|Rscript)\s+(?:\"?\$\(dirname[^)]*\)\"?/|/solution/|\./)?([\w./-]+\.(?:py|sh|R))", t)
        missing = [x for x in refs if not any(f.endswith("/" + x.split("/")[-1]) for f in b.solution_files + b.env_files)]
        if missing:
            problems.append(f"solve.sh invokes scripts shipped neither in solution/ nor in environment/: {missing}")
        for f in b.solution_files:
            if f.endswith(".py"):
                try:
                    py_compile.compile(str(b.root / f), doraise=True, cfile=tempfile.mktemp(suffix=".pyc"))
                except py_compile.PyCompileError as e:
                    problems.append(f"{f}: {str(e.msg).splitlines()[-1][:120]}")
        hard = [p for p in problems if not p.startswith("solve.sh has no shebang")]
        if hard:
            return self.fail("; ".join(problems))
        if problems:
            return self.warn("; ".join(problems))
        return self.ok(f"solve.sh OK; {len(b.solution_files)} solution file(s) compile")


@register
class OracleWritesDeliverables(Check):
    id = "solution.writes_deliverables"
    name = "Solution writes the deliverables the verifier reads"
    category = "solution"
    default_severity = Severity.INFO

    def run(self, b, cfg):
        from .instruction_checks import GENERIC, _names_in, announced, verifier_reads
        if not b.solution_files or not b.tests_files:
            return self.skip("needs solution/ and tests/")
        code = "\n".join(b.text(f) for f in b.solution_files if b.is_text(f))
        reads = {p.split("/")[-1] for p in verifier_reads(b)} - GENERIC
        sealed = {f.split("/")[-1] for f in b.tests_files}
        shipped = {f.split("/")[-1] for f in b.env_files}
        deliverables = sorted(n for n in reads if n not in sealed and n not in shipped and not n.endswith((".py", ".sh")))
        sol_names = {p.split("/")[-1] for p in _names_in(code)}
        missing = [n for n in deliverables if not announced(n, sol_names) and n not in code]
        if deliverables and missing and len(missing) == len(deliverables):
            return self.warn(f"solution never mentions {len(missing)} of {len(deliverables)} verifier-read deliverable(s); the oracle may not pass", evidence=missing)
        return self.ok(f"solution references all {len(deliverables)} verifier-read deliverable(s)" if deliverables else "no deliverable names to cross-check")
