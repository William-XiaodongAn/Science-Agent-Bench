"""Verifier checks: test.sh sanity, graders compile, reward written and bounded, determinism, trial-time network,
agent-supplied scores, safe execution of agent code, referenced files exist."""
from __future__ import annotations

import py_compile
import re
import subprocess
import tempfile

from ..model import Severity
from .base import Check, register


def graders(b) -> list[str]:
    return [f for f in b.tests_files if f.endswith(".py") and b.is_text(f)]


def shells(b) -> list[str]:
    return [f for f in b.tests_files if f.endswith((".sh", ".bash")) and b.is_text(f)]


@register
class TestShSanity(Check):
    id = "verifier.test_sh_sanity"
    name = "tests/test.sh is a runnable entry point"
    category = "verifier"
    default_severity = Severity.BLOCK

    def run(self, b, cfg):
        if not b.exists("tests/test.sh"):
            return self.fail("tests/test.sh missing")
        t = b.text("tests/test.sh")
        problems, ev = [], []
        if not t.strip():
            return self.fail("tests/test.sh is empty")
        if not t.lstrip().startswith("#!"):
            ev.append("no shebang line (Harbor invokes bash explicitly, so this is cosmetic)")
        refs = re.findall(r"(?:python3?|bash|sh|pytest)\s+([\w./-]+\.(?:py|sh))", t)
        missing = [r for r in refs if not b.exists("tests/" + r.split("/")[-1]) and not b.exists(r.lstrip("/").replace("tests/", "tests/", 1)) and not any(f.endswith("/" + r.split("/")[-1]) for f in b.tests_files)]
        if missing:
            problems.append(f"invokes scripts not shipped in tests/: {missing}")
        writes_reward = bool(re.search(r"reward\.txt|/logs/verifier|ctrf\.json|pytest", t + "\n".join(b.text(f) for f in graders(b))))
        if not writes_reward:
            problems.append("neither test.sh nor a grader writes /logs/verifier/reward.txt or a CTRF report")
        grader_code = "\n".join(b.text(f) for f in graders(b))
        fail_safe = bool(re.search(r"except\b", grader_code)) and "reward.txt" in grader_code
        if not re.search(r"set -e|set -o pipefail|\|\|\s*exit|exit \$", t) and "pytest" not in t and not fail_safe:
            ev.append("test.sh does not fail fast (no set -e / exit handling) and the grader has no exception handler writing the reward; a crash may leave no reward")
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as fh:
            fh.write(t)
        r = subprocess.run(["bash", "-n", fh.name], capture_output=True, text=True)
        if r.returncode != 0:
            problems.append(f"bash -n: {r.stderr.strip()[:200]}")
        if problems:
            return self.fail("; ".join(problems), evidence=ev)
        if ev:
            return self.info("test.sh runs; note: " + ev[0])
        return self.ok("shebang, referenced scripts present, reward channel written, syntax OK")


@register
class GradersCompile(Check):
    id = "verifier.graders_compile"
    name = "Grader scripts compile"
    category = "verifier"
    default_severity = Severity.BLOCK

    def run(self, b, cfg):
        bad = []
        for f in graders(b):
            try:
                py_compile.compile(str(b.root / f), doraise=True, cfile=tempfile.mktemp(suffix=".pyc"))
            except py_compile.PyCompileError as e:
                bad.append(f"{f}: {str(e.msg).splitlines()[-1][:160]}")
        for f in shells(b):
            r = subprocess.run(["bash", "-n", str(b.root / f)], capture_output=True, text=True)
            if r.returncode != 0:
                bad.append(f"{f}: {r.stderr.strip()[:160]}")
        if bad:
            return self.fail(f"{len(bad)} verifier file(s) do not compile", evidence=bad)
        n = len(graders(b)) + len(shells(b))
        return self.ok(f"{n} verifier script(s) compile") if n else self.warn("no python or shell grader under tests/")


@register
class RewardWrittenAndBounded(Check):
    id = "verifier.reward_written_bounded"
    name = "Reward is written to /logs/verifier and bounded to [0, 1]"
    category = "verifier"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        code = "\n".join(b.text(f) for f in graders(b) + shells(b))
        if not code.strip():
            return self.skip("no grader code")
        writes = re.search(r"reward\.txt", code)
        pytest_mode = "pytest" in code
        if not writes and not pytest_mode:
            return self.fail("no code path writes reward.txt (and no pytest-based reward)")
        bounded = bool(re.search(r"(clip|min\(|max\(|np\.clip|1\.0 if|\b[01]\.0\b|reward\s*=\s*(1|0)\b|float\(passed\)|int\(passed\)|echo\s+[\"']?[01](\.0)?[\"']?\s*>|REWARD=[01]|reward=[01]|\$\?)", code))
        binary = bool(re.search(r"reward\s*=\s*(1(\.0)?\s+if|float\(|int\()|echo\s+[\"']?[01](\.0)?[\"']?\s*>\s*.*reward|REWARD=[01]", code))
        raw_metric_write = bool(re.search(r"reward\.txt[\"'][^\n]*\n?[^\n]*write\((f?[\"']\{|str\()\s*(rmse|score|error|loss|mse|mae|dist|metric)", code, re.I))
        if writes and not bounded and raw_metric_write:
            return self.warn("reward.txt receives a raw metric with no clipping or binarisation; a value above 1 or below 0 would corrupt pass@k", data={"binary": binary})
        if writes and not bounded:
            return self.info("could not confirm the reward is clipped to [0, 1] (heuristic); check the write site", data={"binary": binary})
        return self.ok("reward written and bounded" + (" (binary)" if binary else " (continuous, clipped)"), data={"binary": binary})


@register
class Deterministic(Check):
    id = "verifier.deterministic"
    name = "Verifier has no unseeded randomness or clock dependence"
    category = "verifier"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        hits = b.grep(r"\b(random\.(random|randint|choice|shuffle|sample|uniform)|np\.random\.(rand|randn|randint|choice|shuffle|permutation|normal|uniform)|torch\.rand|datetime\.now|time\.time\(\)|uuid4)\b", graders(b))
        seeded = bool(b.grep(r"(seed\(|default_rng\(\s*\d|manual_seed|RandomState\(\s*\d|--seed)", graders(b)))
        rand = [h for h in hits if "random" in h[2] or "rand" in h[2]]
        clock = [h for h in hits if "time" in h[2] or "now" in h[2] or "uuid" in h[2]]
        ev = [f"{f}:{ln}: {l}" for f, ln, l in hits]
        if rand and not seeded:
            return self.warn("random calls without a visible seed: repeated verifications may disagree", evidence=ev)
        if clock:
            return self.info("clock/uuid used (fine for logging; a problem if it enters the score)", evidence=ev)
        return self.ok("no unseeded randomness found" + (" (seeded RNG present)" if seeded else ""))


@register
class NoNetworkAtTrial(Check):
    id = "verifier.no_network_at_trial"
    name = "Verifier does not fetch from the network at trial time"
    category = "verifier"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        sh_hits = b.grep(r"\b(curl|wget|git clone|pip3? install|uv pip install|npm install|apt(-get)? install|conda install)\b", shells(b))
        py_hits = b.grep(r"\b(requests\.(get|post)|urllib\.request\.urlopen|httpx\.|urlopen\()", graders(b))
        judge = bool(b.grep(r"JUDGE_|anthropic|openai|/v1/messages|/v1/chat", graders(b)))
        ev = [f"{f}:{ln}: {l}" for f, ln, l in sh_hits + py_hits]
        if sh_hits:
            return self.warn("test.sh installs or downloads at trial time: verification depends on the network and on version resolution; bake dependencies into the image", evidence=ev)
        if py_hits and judge:
            return self.info("grader calls a model API (LLM/VLM judge); the verifier phase needs that host allowlisted and credentials via [verifier.env]", evidence=ev)
        external = [h for h in py_hits if re.search(r"https?://(?!(localhost|127\.0\.0\.1|0\.0\.0\.0))", h[2])]
        if external:
            return self.warn("grader calls an external URL at trial time", evidence=ev)
        if py_hits:
            return self.info("grader makes HTTP calls, apparently to a local service (variable or localhost URL)", evidence=ev)
        return self.ok("no trial-time network fetches in the verifier")


@register
class NoTrustInAgentScores(Check):
    id = "verifier.no_trust_in_agent_scores"
    name = "Reward is computed by the verifier, not read from the submission"
    category = "verifier"
    default_severity = Severity.WARN
    description = "A grader that copies a 'score', 'reward' or 'passed' field from an agent-written file into the reward can be trivially gamed."

    def run(self, b, cfg):
        code = "\n".join(b.text(f) for f in graders(b))
        if not code:
            return self.skip("no python grader")
        loads = [l for l in code.splitlines() if re.search(r"json\.load|np\.load|read_csv|open\(", l) and re.search(r"\b(SUB|SUBMISSION|submission|sub_dir|artifact|/workspace|/app)\b", l)]
        keys = re.findall(r"\[\s*[\"'](score|reward|passed|accuracy|rmse|result)[\"']\s*\]", code)
        suspicious = bool(loads) and bool(keys) and bool(re.search(r"reward\s*=\s*\w*(sub|submitted|pred|agent|claimed|result)\w*\s*\[\s*[\"'](score|reward|passed)[\"']\s*\]", code))
        self_reported = re.findall(r"(submitted_\w+|claimed_\w+|self[_-]reported\w*)", code)
        if suspicious:
            return self.fail("the reward appears to be taken from a value the agent wrote (json field named score/reward/passed)", evidence=sorted(set(keys))[:10])
        if loads and keys:
            return self.info("grader reads agent-written JSON fields named like scores; verify they are only compared, never used as the reward", evidence=sorted(set(keys))[:10] + sorted(set(self_reported))[:5])
        return self.ok("no sign of agent-supplied scores entering the reward")


@register
class ExecutesAgentCodeSafely(Check):
    id = "verifier.executes_agent_code_safely"
    name = "If the verifier runs agent code, it does so with a timeout and unprivileged"
    category = "verifier"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        code = "\n".join(b.text(f) for f in graders(b) + shells(b))
        runs = re.search(r"subprocess\.(run|Popen|call|check_output)\(|os\.system\(|importlib\.import_module\(|exec\(|runpy\.|python3?\s+[\"']?/(workspace|app)", code)
        if not runs:
            return self.ok("verifier does not execute agent-produced code")
        has_timeout = bool(re.search(r"timeout\s*=|\btimeout\s+\d+|TIMEOUT|pytest", code))
        unpriv = bool(re.search(r"(RUN_USER|runuser|su\s+-|setpriv|--user|preexec_fn|os\.setuid|nobody|chmod 700|drop.?priv)", code))
        separate = b.toml_get("verifier", "environment_mode") == "separate" if b.toml else False
        notes = []
        if not has_timeout:
            notes.append("no timeout on the executed agent code (an infinite loop hangs the verifier)")
        if not unpriv and not separate:
            notes.append("agent code appears to run as the verifier user with access to /tests and the reward channel (a separate verifier container or a dropped-privilege user avoids this)")
        if notes:
            return self.warn("; ".join(notes))
        if separate and not unpriv:
            return self.info("agent code runs inside the separate verifier container; the agent's own environment cannot reach the reward channel")
        return self.ok("agent code executed with a timeout and reduced privileges")


@register
class VerifierReferencesExist(Check):
    id = "verifier.references_exist"
    name = "Files the verifier expects under tests/ are shipped"
    category = "verifier"
    default_severity = Severity.BLOCK

    def run(self, b, cfg):
        code = "\n".join(b.text(f) for f in graders(b) + shells(b))
        refs = set(re.findall(r"/tests/([\w./-]+\.[\w]+)", code)) | set(re.findall(r"[\"']tests/([\w./-]+\.[\w]+)[\"']", code))
        refs |= set(re.findall(r"os\.path\.join\(\s*SEALED\s*,\s*[\"']([\w./-]+)[\"']", code))
        sealed_dir = [f for f in b.tests_files if "/sealed/" in f or "/data/" in f]
        missing = []
        for r in sorted(refs):
            name = r.split("/")[-1]
            if name in ("reward.txt", "result.json", "ctrf.json"):
                continue
            rel = r if r.startswith("tests/") else "tests/" + r.lstrip("/")
            is_dir = any(f.startswith(rel.rstrip("/") + "/") or f.startswith("tests/sealed/" + name + "/") for f in b.tests_files)
            if is_dir or any(f.endswith("/" + name) or f == rel for f in b.tests_files):
                continue
            missing.append(r)
        lines = code.splitlines()
        def guarded(name):
            for i, l in enumerate(lines):
                if name in l and any(re.search(r"exists\(|isfile\(|glob\(|\btry:|except\b|default|if .*os\.path", w) for w in lines[max(0, i - 3): i + 4]):
                    return True
            return False
        optional = [r for r in missing if guarded(r.split("/")[-1])]
        missing = [r for r in missing if r not in optional]
        if optional and not missing:
            return self.info(f"{len(optional)} tests/ reference(s) not shipped but read conditionally (optional per-instance files)", evidence=optional)
        if missing:
            # sealed data may legitimately be generated at build time from tests/Dockerfile
            dockerfile = b.text("tests/Dockerfile") if b.exists("tests/Dockerfile") else ""
            if dockerfile and re.search(r"\b(curl|wget|python3?)\b", dockerfile):
                return self.info(f"{len(missing)} referenced file(s) not in tests/ but tests/Dockerfile generates or fetches data", evidence=missing)
            return self.fail(f"verifier references {len(missing)} file(s) that are not under tests/", evidence=missing)
        return self.ok(f"{len(refs)} tests/ reference(s) resolve" + (f"; {len(sealed_dir)} sealed/data file(s) shipped" if sealed_dir else ""))
