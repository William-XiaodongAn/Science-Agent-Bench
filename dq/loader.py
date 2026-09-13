"""Load a Harbor-format task from a directory, a zip archive or a git URL into a TaskBundle."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Iterable

TEXT_EXT = {".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".py", ".sh", ".bash", ".cfg", ".ini", ".csv", ".tsv",
            ".tex", ".rst", ".js", ".html", ".css", ".r", ".R", ".jl", ".m", ".c", ".cpp", ".h", ".env", ".dockerfile"}
TEXT_NAMES = {"Dockerfile", "Makefile", "LICENSE", "SHA256SUMS", ".gitignore", ".dockerignore", "requirements.txt"}
MAX_TEXT_BYTES = 2_000_000
GIT_URL = re.compile(r"^(https?://|git@|ssh://).+")


class LoadError(Exception):
    pass


class TaskBundle:
    """A task directory with cached file access. `root` is the directory containing task.toml."""

    def __init__(self, root: Path, source: str, tempdir: str | None = None):
        self.root = Path(root).resolve()
        self.source = source
        self._tempdir = tempdir
        self.files: list[str] = sorted(
            str(p.relative_to(self.root)) for p in self.root.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(self.root).parts and "__pycache__" not in p.parts
        )
        self.toml: dict | None = None
        self.toml_error: str | None = None
        if (self.root / "task.toml").exists():
            try:
                self.toml = tomllib.loads(self.text("task.toml"))
            except Exception as e:  # noqa: BLE001
                self.toml_error = f"{type(e).__name__}: {e}"
        self.yaml: dict | None = None
        if (self.root / "task.yaml").exists():
            try:
                import yaml  # optional dependency
                self.yaml = yaml.safe_load(self.text("task.yaml")) or {}
            except Exception:  # noqa: BLE001
                self.yaml = None

    # ---- construction -------------------------------------------------------------------------------------------
    @classmethod
    def from_source(cls, source: str, subdir: str | None = None, workdir: str | None = None) -> "TaskBundle":
        source = source.strip()
        tempdir = None
        if GIT_URL.match(source):
            tempdir = tempfile.mkdtemp(prefix="dq-git-", dir=workdir)
            url, ref = source, None
            if "@" in source.split("://", 1)[-1] and not source.startswith("git@"):
                url, ref = source.rsplit("@", 1)
            cmd = ["git", "clone", "--depth", "1", "--quiet"] + (["--branch", ref] if ref else []) + [url, tempdir]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if r.returncode != 0:
                shutil.rmtree(tempdir, ignore_errors=True)
                raise LoadError(f"git clone failed: {r.stderr.strip()[:300]}")
            base = Path(tempdir)
        elif source.lower().endswith(".zip") and Path(source).is_file():
            tempdir = tempfile.mkdtemp(prefix="dq-zip-", dir=workdir)
            with zipfile.ZipFile(source) as zf:
                for m in zf.infolist():
                    target = (Path(tempdir) / m.filename).resolve()
                    if not str(target).startswith(str(Path(tempdir).resolve())):
                        raise LoadError(f"zip entry escapes the archive: {m.filename}")
                zf.extractall(tempdir)
            base = Path(tempdir)
        elif Path(source).is_dir():
            base = Path(source)
        else:
            raise LoadError(f"source is not a directory, a .zip file or a git URL: {source}")
        if subdir:
            base = base / subdir
        root = cls.find_task_root(base)
        return cls(root, source, tempdir)

    @staticmethod
    def find_task_root(base: Path) -> Path:
        if (base / "task.toml").exists():
            return base
        found = [p.parent for p in base.rglob("task.toml") if ".git" not in p.parts and len(p.relative_to(base).parts) <= 4]
        if len(found) == 1:
            return found[0]
        if not found:
            raise LoadError(f"no task.toml found under {base} (is this a Harbor task?)")
        raise LoadError(f"{len(found)} task.toml files found under {base}; point at one task or use the corpus runner")

    def cleanup(self) -> None:
        if self._tempdir:
            shutil.rmtree(self._tempdir, ignore_errors=True)

    # ---- file access -------------------------------------------------------------------------------------------
    def exists(self, rel: str) -> bool:
        return (self.root / rel).exists()

    def is_text(self, rel: str) -> bool:
        p = self.root / rel
        if p.suffix.lower() in TEXT_EXT or p.name in TEXT_NAMES or p.name.startswith("Dockerfile"):
            return True
        try:
            if p.stat().st_size > MAX_TEXT_BYTES:
                return False
            with open(p, "rb") as fh:
                chunk = fh.read(4096)
            return b"\x00" not in chunk
        except OSError:
            return False

    @lru_cache(maxsize=4096)
    def text(self, rel: str) -> str:
        p = self.root / rel
        try:
            if p.stat().st_size > MAX_TEXT_BYTES:
                return ""
            return p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def size(self, rel: str) -> int:
        try:
            return (self.root / rel).stat().st_size
        except OSError:
            return 0

    def sha256(self, rel: str) -> str:
        h = hashlib.sha256()
        with open(self.root / rel, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    def under(self, prefix: str) -> list[str]:
        prefix = prefix.rstrip("/") + "/"
        return [f for f in self.files if f.startswith(prefix)]

    def grep(self, pattern: str | re.Pattern, files: Iterable[str], flags: int = 0) -> list[tuple[str, int, str]]:
        rx = re.compile(pattern, flags) if isinstance(pattern, str) else pattern
        hits = []
        for f in files:
            if not self.is_text(f):
                continue
            for i, line in enumerate(self.text(f).splitlines(), 1):
                if rx.search(line):
                    hits.append((f, i, line.strip()[:200]))
        return hits

    # ---- convenience ---------------------------------------------------------------------------------------------
    @property
    def instruction(self) -> str:
        return self.text("instruction.md") if self.exists("instruction.md") else ""

    @property
    def readme(self) -> str:
        return self.text("README.md") if self.exists("README.md") else ""

    @property
    def tests_files(self) -> list[str]:
        return self.under("tests")

    @property
    def env_files(self) -> list[str]:
        return self.under("environment")

    @property
    def solution_files(self) -> list[str]:
        return self.under("solution")

    @property
    def name(self) -> str:
        if self.toml and isinstance(self.toml.get("task"), dict) and self.toml["task"].get("name"):
            return str(self.toml["task"]["name"])
        return self.root.name

    def toml_get(self, *keys, default=None):
        cur: object = self.toml
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur
