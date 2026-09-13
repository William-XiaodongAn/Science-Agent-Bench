"""task.toml content checks: metadata, timeouts, resources, network policy, artifacts, verifier env templating."""
from __future__ import annotations

import re

from ..model import Severity
from .base import Check, cfg_get, register


@register
class MetadataFields(Check):
    id = "config.metadata_fields"
    name = "Description, authors and classification metadata present"
    category = "config"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        if not b.toml:
            return self.skip("task.toml not parseable")
        problems = []
        task = b.toml.get("task", {}) if isinstance(b.toml.get("task"), dict) else {}
        if not str(task.get("description", "")).strip():
            problems.append("[task].description empty")
        if not task.get("authors"):
            problems.append("[task].authors empty")
        md = b.toml.get("metadata", {}) if isinstance(b.toml.get("metadata"), dict) else {}
        keys = cfg_get(cfg, "taxonomy.metadata_domain_keys", ["domain", "field"])
        if not any(md.get(k) for k in keys) and not (b.yaml and any(b.yaml.get(k) for k in keys)):
            problems.append(f"no domain classification in [metadata] (expected one of {keys}) or task.yaml")
        if problems:
            return self.warn("; ".join(problems))
        return self.ok("description, authors and domain metadata present")


@register
class Timeouts(Check):
    id = "config.timeouts"
    name = "Agent and verifier timeouts set and plausible"
    category = "config"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        if not b.toml:
            return self.skip("task.toml not parseable")
        a = b.toml_get("agent", "timeout_sec")
        v = b.toml_get("verifier", "timeout_sec")
        lo = float(cfg_get(cfg, "requirements.agent_timeout_min_sec", 300))
        hi = float(cfg_get(cfg, "requirements.agent_timeout_max_sec", 86400))
        notes = []
        if a is None:
            notes.append("[agent].timeout_sec not set (Harbor default applies)")
        elif not (lo <= float(a) <= hi):
            notes.append(f"[agent].timeout_sec={a} outside [{lo:.0f}, {hi:.0f}]")
        if v is None:
            notes.append("[verifier].timeout_sec not set (600 s default)")
        text = b.instruction
        hours = [m.group(1) for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:h|hour|hours)\b", text)
                 if re.search(r"(budget|limit|you have|within|allowed|wall[- ]clock|time|session|complete)", text[max(0, m.start() - 80): m.end() + 40], re.I)]
        if a and hours:
            declared = float(a) / 3600
            if not any(abs(float(h) - declared) < 0.51 for h in hours):
                notes.append(f"instruction mentions hours {sorted(set(hours))[:4]} but [agent].timeout_sec is {declared:.1f} h")
        if notes:
            return self.warn("; ".join(notes))
        return self.ok(f"agent {a} s, verifier {v} s")


@register
class Resources(Check):
    id = "config.resources"
    name = "Compute resources declared and consistent"
    category = "config"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        if not b.toml:
            return self.skip("task.toml not parseable")
        env = b.toml.get("environment", {}) if isinstance(b.toml.get("environment"), dict) else {}
        notes = []
        if env.get("cpus") is None and env.get("memory_mb") is None and env.get("memory") is None:
            notes.append("no cpus/memory declared (sandbox defaults will apply; agents cannot plan a budget)")
        gpus = env.get("gpus") or 0
        mentions_gpu = re.search(r"\b(GPU|CUDA|cuda)\b", b.instruction) is not None
        if gpus and not mentions_gpu:
            notes.append(f"gpus={gpus} declared but the instruction never mentions a GPU")
        promises = [m.group(0) for m in re.finditer(r"[^.\n]{0,60}\b(a|an|one|the)\s+GPUs?\b[^.\n]{0,40}|[^.\n]{0,60}GPUs? (is|are) available[^.\n]{0,20}", b.instruction)
                    if not re.search(r"\b(no|without|not|none|zero|cannot|can't|unavailable)\b", m.group(0), re.I)]
        if not gpus and promises:
            notes.append("instruction promises a GPU but none is declared: " + promises[0].strip()[:80])
        if notes:
            return self.warn("; ".join(notes))
        return self.ok(f"cpus={env.get('cpus')} memory={env.get('memory_mb') or env.get('memory')} gpus={gpus}")


@register
class NetworkPolicy(Check):
    id = "config.network_policy"
    name = "Network policy explicit; verifier phase not open when it need not be"
    category = "config"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        if not b.toml:
            return self.skip("task.toml not parseable")
        env = b.toml.get("environment", {}) if isinstance(b.toml.get("environment"), dict) else {}
        mode = env.get("network_mode") or ("public" if env.get("allow_internet") else None)
        notes, ev = [], []
        if mode is None:
            notes.append("[environment].network_mode not declared (Harbor default is public)")
        vmode = b.toml_get("verifier", "environment", "network_mode") or b.toml_get("verifier", "network_mode")
        sep = b.toml_get("verifier", "environment_mode") == "separate"
        if sep and (vmode in (None, "public")):
            notes.append("separate verifier with public network: the verifier phase should be no-network or an allowlist")
        hosts = env.get("allowed_hosts") or []
        if mode == "allowlist" and not hosts:
            notes.append("allowlist mode with no allowed_hosts")
        if notes:
            return self.warn("; ".join(notes), evidence=ev)
        return self.ok(f"agent network_mode={mode}" + (f", verifier={vmode}" if vmode else ""))


@register
class ArtifactsAndSeparateVerifier(Check):
    id = "config.artifacts_separate_verifier"
    name = "Separate-verifier tasks declare artifacts and a tests/Dockerfile"
    category = "config"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        if not b.toml:
            return self.skip("task.toml not parseable")
        sep = b.toml_get("verifier", "environment_mode") == "separate"
        artifacts = b.toml.get("artifacts")
        if not sep:
            if artifacts:
                return self.info("artifacts declared although the verifier shares the agent environment (harmless)")
            return self.ok("shared verifier environment; verifier reads the agent's filesystem directly")
        notes = []
        if not artifacts:
            notes.append("environment_mode=separate but no top-level artifacts: the verifier will see nothing the agent produced")
        if not b.exists("tests/Dockerfile"):
            notes.append("environment_mode=separate but tests/Dockerfile missing")
        if b.toml_get("verifier", "artifacts") is not None:
            notes.append("[verifier].artifacts is not a Harbor field (artifacts is top-level) and is silently ignored")
        if notes:
            return self.fail("; ".join(notes))
        return self.ok(f"separate verifier with {len(artifacts)} artifact spec(s) and tests/Dockerfile")


@register
class VerifierEnvDeclared(Check):
    id = "config.verifier_env_declared"
    name = "Environment variables the grader reads are declared"
    category = "config"
    default_severity = Severity.WARN
    description = "os.environ lookups in tests/ without a default must be declared in [verifier.env]; ${VAR} templates need `harbor --env-file`."

    def run(self, b, cfg):
        declared = dict(b.toml_get("verifier", "env", default={}) or {})
        for f in b.tests_files:
            if f.endswith((".sh", ".bash")) and b.is_text(f):
                for m in re.finditer(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]+)=", b.text(f), re.M):
                    declared.setdefault(m.group(1), "set in test.sh")
        used = {}
        for f, ln, line in b.grep(r"os\.environ(?:\.get\()?\[?\s*[\"']([A-Z0-9_]+)[\"']", b.tests_files):
            for m in re.finditer(r"os\.environ(?:\.get\()?\[?\s*[\"']([A-Z0-9_]+)[\"']\s*(?:,\s*([^)]+))?", line):
                used.setdefault(m.group(1), (f, ln, bool(m.group(2)) or "[" not in m.group(0)))
        undeclared_no_default = [k for k, (f, ln, has_default) in used.items() if k not in declared and not has_default
                                 and k not in ("PATH", "HOME", "PYTHONPATH", "TMPDIR", "TMP", "TEMP", "USER", "LANG", "SHELL", "PWD", "CI", "HOSTNAME", "CUDA_VISIBLE_DEVICES", "OMP_NUM_THREADS")]
        templates = [k for k, v in declared.items() if isinstance(v, str) and "${" in v]
        ev = [f"{k}: {f}:{ln}" for k, (f, ln, _) in used.items() if k in undeclared_no_default]
        if undeclared_no_default:
            return self.warn(f"grader reads {undeclared_no_default} without a default and [verifier.env] does not declare them", evidence=ev)
        note = f"{len(used)} env var(s) read by the grader, {len(declared)} declared"
        if templates:
            return self.info(note + f"; templated at job time from the host: {templates} (verification needs `harbor --env-file`)")
        return self.ok(note)
