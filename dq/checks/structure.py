"""Structure and configuration-file checks: required files, task.toml parses and validates, extraneous files."""
from __future__ import annotations

import re

from ..model import Severity
from .base import Check, cfg_get, register

ROOT_ALLOWED = {"task.toml", "task.yaml", "instruction.md", "README.md", "LICENSE", "LICENSE.md", ".gitignore",
                ".dockerignore", "environment", "solution", "tests", "authoring", "generator", "docs"}


@register
class RequiredFiles(Check):
    id = "structure.required_files"
    name = "Required files present"
    category = "structure"
    default_severity = Severity.BLOCK
    description = "task.toml, instruction.md, an environment (Dockerfile or docker_image), tests/test.sh and a solution/ must exist."

    def run(self, b, cfg):
        missing, notes = [], []
        for f in ("task.toml", "instruction.md"):
            if not b.exists(f):
                missing.append(f)
        if not b.exists("tests/test.sh"):
            missing.append("tests/test.sh")
        has_dockerfile = b.exists("environment/Dockerfile") or any(f.startswith("environment/") and f.endswith("Dockerfile") for f in b.files)
        image = b.toml_get("environment", "docker_image") if b.toml else None
        if not has_dockerfile and not image:
            missing.append("environment/Dockerfile (or [environment].docker_image)")
        if not b.solution_files:
            notes.append("no solution/ directory: the task ships no oracle, so solvability cannot be demonstrated (harbor run -a oracle)")
        elif not b.exists("solution/solve.sh"):
            notes.append("solution/ exists but has no solve.sh (Harbor's oracle entry point)")
        if missing:
            return self.fail("missing: " + ", ".join(missing), evidence=notes)
        if notes:
            return self.warn("; ".join(notes))
        return self.ok("task.toml, instruction.md, environment, tests/test.sh and solution/solve.sh present")


@register
class TomlParses(Check):
    id = "structure.task_toml_parses"
    name = "task.toml parses"
    category = "structure"
    default_severity = Severity.BLOCK

    def run(self, b, cfg):
        if not b.exists("task.toml"):
            return self.fail("task.toml missing")
        if b.toml_error:
            return self.fail(f"task.toml does not parse: {b.toml_error}")
        return self.ok("task.toml is valid TOML")


@register
class HarborSchema(Check):
    id = "structure.harbor_schema"
    name = "task.toml matches Harbor's schema"
    category = "structure"
    default_severity = Severity.BLOCK
    description = "Validated with the installed harbor package when available (pydantic TaskConfig); otherwise a minimal field check."

    def run(self, b, cfg):
        if not b.toml:
            return self.skip("task.toml not parseable")
        try:
            from harbor.models.task.config import TaskConfig  # type: ignore
        except Exception:  # noqa: BLE001
            problems = []
            if not isinstance(b.toml.get("task"), dict) or not b.toml["task"].get("name"):
                problems.append("[task].name missing")
            if problems:
                return self.fail("harbor not installed; minimal check failed: " + "; ".join(problems))
            return self.info("harbor package not installed: only a minimal field check was possible (install harbor for full schema validation)")
        try:
            TaskConfig.model_validate(b.toml)
        except Exception as e:  # noqa: BLE001
            msg = str(e).splitlines()
            return self.fail("Harbor rejects task.toml: " + " | ".join(m.strip() for m in msg[:6])[:600])
        return self.ok("Harbor TaskConfig validation passed")


@register
class TaskNameMatchesFolder(Check):
    id = "structure.task_name_matches_folder"
    name = "[task].name ends with the folder name"
    category = "structure"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        name = b.toml_get("task", "name") if b.toml else None
        if not name:
            return self.warn("[task].name is missing or empty")
        slug = str(name).split("/")[-1]
        if slug != b.root.name and b._tempdir is None:
            return self.warn(f"[task].name slug '{slug}' differs from the folder name '{b.root.name}'")
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", slug):
            return self.warn(f"slug '{slug}' should be lowercase letters, digits, '-', '_' or '.'")
        return self.ok(f"name '{name}' consistent with folder")


@register
class ExtraneousFiles(Check):
    id = "structure.extraneous_files"
    name = "No stray or oversized files"
    category = "structure"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        max_mb = float(cfg_get(cfg, "requirements.max_file_mb", 50))
        stray = [f for f in b.files if f.split("/")[0] not in ROOT_ALLOWED and "/" not in f and not f.startswith(".")]
        junk = [f for f in b.files if any(p in ("__pycache__", ".DS_Store", ".ipynb_checkpoints") for p in f.split("/")) or f.endswith((".pyc", ".swp"))]
        big = [f"{f} ({b.size(f) / 1e6:.1f} MB)" for f in b.files if b.size(f) > max_mb * 1e6]
        ev = [f"stray root file: {f}" for f in stray] + [f"junk: {f}" for f in junk] + [f"large: {f}" for f in big]
        if big:
            return self.warn(f"{len(big)} file(s) above {max_mb:.0f} MB (ship large data via the Dockerfile or a dataset host)", evidence=ev)
        if stray or junk:
            return self.warn(f"{len(stray)} unexpected root file(s), {len(junk)} junk file(s)", evidence=ev)
        return self.ok(f"{len(b.files)} files, none stray, junk or oversized")
