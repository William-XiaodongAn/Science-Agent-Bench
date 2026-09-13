"""Instruction checks: coherence between the prompt, the shipped artifacts and the verifier."""
from __future__ import annotations

import re

from ..model import Severity
from .base import Check, cfg_get, register

# absolute paths and bare filenames with a data-like extension
ABS_PATH = re.compile(r"(?<![\w/])(/(?:workspace|app|home|data|root|opt|tmp|mnt|srv|output|results)[\w./+-]*)")
FILE_RX = re.compile(r"(?<![\w])([\w][\w.+-]*\.(?:npy|npz|csv|tsv|json|jsonl|txt|md|png|pdf|h5|hdf5|parquet|pkl|pt|pth|nc|tif|tiff|fits|xyz|pdb|cif|mat|yaml|yml|toml|py|sh|R|ipynb|zip|tar\.gz))\b")
GENERIC = {"README.md", "instruction.md", "task.toml", "task.yaml", "requirements.txt", "Dockerfile", "test.sh", "solve.sh",
           "grade.py", "test_state.py", "test_outputs.py", "run.py", "methods.md", "reward.txt", "result.json", "ctrf.json"}


BRACES = re.compile(r"\{[^{}]*\}|<[^<>\s]{1,40}>|\$\{?[A-Za-z_][A-Za-z0-9_]*\}?")   # {label}, <t>, $VAR placeholders


def _clean_name(name: str) -> str | None:
    """A plausible file name: has an extension, a stem of >= 2 word characters, and does not start with a separator
    left over from a format string (e.g. the `_trajectory.png` of f"{label}_trajectory.png")."""
    name = name.rstrip(".,;:)`'\"")
    stem = name.split("/")[-1]
    if "." not in stem or stem.startswith(("_", "-", ".")) or len(stem.split(".")[0]) < 2:
        return None
    if stem.split(".")[0] in ("file", "path", "name", "output", "input", "example", "foo", "bar"):
        return None
    return name


def is_pattern(name: str) -> bool:
    """`frame_.npy` (from frame_{t}.npy) or `params_.json`: a family of files; matched by prefix + extension."""
    stem = name.split("/")[-1].rsplit(".", 1)[0]
    return stem.endswith(("_", "-"))


def announced(name: str, want_names: set[str]) -> bool:
    if name in want_names:
        return True
    stem, ext = name.rsplit(".", 1) if "." in name else (name, "")
    if is_pattern(name):
        return any(w.rsplit(".", 1)[0].startswith(stem) and w.endswith("." + ext) for w in want_names)
    return any(is_pattern(w) and stem.startswith(w.rsplit(".", 1)[0]) and w.endswith("." + ext) for w in want_names)


def _names_in(text: str, *, paths_only: bool = False) -> set[str]:
    text = BRACES.sub("", text)          # drop f-string / format placeholders so fragments are not read as names
    out = set()
    for m in ABS_PATH.finditer(text):
        n = _clean_name(m.group(1))
        if n:
            out.add(n)
    if not paths_only:
        for m in FILE_RX.finditer(text):
            n = _clean_name(m.group(1))
            if n:
                out.add(n)
    return out


def instruction_outputs(text: str) -> set[str]:
    """Files/paths the instruction tells the agent to produce or use (heuristic: named files with an extension)."""
    return _names_in(text)


def verifier_reads(b) -> set[str]:
    """File names that appear as string literals in the verifier code (tests/)."""
    found = set()
    for f in b.tests_files:
        if not f.endswith((".py", ".sh", ".bash")) or not b.is_text(f):
            continue
        for line in b.text(f).splitlines():
            if re.search(r"(/tests/|\btests/|SEALED|sealed|ground_?truth|GT_|expected_|reference_|fixtures?/|golden|__file__|HERE\b|/logs/verifier|#\s*)", line) and not re.search(r"(SUB\b|submission|/workspace/submission|/app/|artifact)", line):
                continue            # verifier-internal paths and comments are not agent deliverables
            if re.search(r"(np\.save|\.to_csv\(|json\.dump\(|savefig|open\([^)]*[\"'](w|a)[\"']|write_text\(|\.save\()", line):
                continue            # files the verifier itself writes are not agent deliverables
            for lit in re.findall(r"[\"']([^\"'\n]{2,200})[\"']", line):
                found |= _names_in(lit)
    return found


@register
class InstructionLengthSections(Check):
    id = "instruction.length_and_sections"
    name = "Instruction is substantial and names its deliverables"
    category = "instruction"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        text = b.instruction
        if not text.strip():
            return self.fail("instruction.md missing or empty")
        n = len(text)
        lo = int(cfg_get(cfg, "requirements.min_instruction_chars", 300))
        notes, soft = [], []
        if n < lo:
            notes.append(f"only {n} characters (< {lo}); an agent cannot infer the deliverable from this")
        if not instruction_outputs(text) and verifier_reads(b):
            notes.append("no output file or path is named although the verifier reads agent-produced files")
        if not re.search(r"\b(score|scored|graded|verif|evaluat|pass|metric|RMSE|accuracy|reward|tests?|checked|correct)\b", text, re.I):
            soft.append("no sentence tells the agent how the result is judged; acceptable if the deliverable is unambiguous")
        if notes:
            return self.warn("; ".join(notes + soft), data={"chars": n})
        if soft:
            return self.info(f"{n} characters; " + soft[0], data={"chars": n})
        return self.ok(f"{n} characters; deliverables named; judging described", data={"chars": n})


@register
class DeliverablesMatchVerifier(Check):
    id = "instruction.deliverables_match_verifier"
    name = "Files the verifier reads are named in the instruction"
    category = "instruction"
    default_severity = Severity.WARN
    description = "Prompt-artifacts-verifier coherence: every agent-produced file the verifier opens must be announced; deliverables the verifier never reads are noise."

    def run(self, b, cfg):
        if not b.instruction or not b.tests_files:
            return self.skip("needs instruction.md and tests/")
        want = instruction_outputs(b.instruction)
        reads = verifier_reads(b)
        want_names = {p.split("/")[-1] for p in want} - GENERIC
        read_names = {p.split("/")[-1] for p in reads} - GENERIC
        # files under tests/ (sealed data) are not deliverables
        sealed_names = {f.split("/")[-1] for f in b.tests_files}
        shipped_names = {f.split("/")[-1] for f in b.env_files}
        read_deliverables = {n for n in read_names if n not in sealed_names and n not in shipped_names}
        unannounced = sorted(n for n in read_deliverables if not announced(n, want_names) and not n.endswith((".py", ".sh")))
        unread = sorted(n for n in want_names if not announced(n, read_names) and n not in shipped_names and not n.endswith((".py", ".sh", ".md")))
        ev = [f"verifier reads but instruction never names: {n}" for n in unannounced] + [f"instruction names but verifier never reads: {n}" for n in unread]
        # names announced anywhere the agent can read (a shipped README or template counts)
        shipped_text = "\n".join(b.text(f) for f in b.env_files if b.is_text(f) and f.endswith((".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py")))
        shipped_named = {p.split("/")[-1] for p in _names_in(shipped_text)}
        unannounced = [n for n in unannounced if not announced(n, shipped_named)]
        if unannounced:
            return self.warn(f"{len(unannounced)} file(s) the verifier reads are named neither in the instruction nor in shipped docs (implicit expectation)", evidence=ev,
                             data={"unannounced": unannounced, "unread": unread})
        if unread:
            return self.info(f"{len(unread)} named deliverable(s) are not read by the verifier (fine if they are supporting material)", evidence=ev)
        return self.ok(f"{len(read_deliverables)} agent-produced file(s) read by the verifier, all named in the instruction",
                       data={"read": sorted(read_deliverables)})


@register
class ReferencedInputsExist(Check):
    id = "instruction.referenced_inputs_exist"
    name = "Input files the instruction points at are shipped"
    category = "instruction"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        if not b.instruction:
            return self.skip("no instruction")
        env_names = {f.split("/")[-1] for f in b.env_files}
        dockerfile = "\n".join(b.text(f) for f in b.env_files if f.endswith("Dockerfile"))
        downloads = bool(re.search(r"\b(curl|wget|gdown|git clone|fetch|hf_hub|huggingface|snapshot_download|urlretrieve|requests\.get|gsutil|aws s3|ADD https?://|kaggle|zenodo)\b", dockerfile, re.I))
        generates = bool(re.search(r"^\s*RUN\s+.*\b(python3?|Rscript|julia|bash|sh|make)\b", dockerfile, re.M))
        missing = []
        for p in instruction_outputs(b.instruction):
            name = p.split("/")[-1]
            if name in GENERIC or not re.search(r"\.(npy|npz|csv|tsv|h5|hdf5|parquet|nc|tif|tiff|fits|mat|dat|json|pdb|cif|xyz|png|pdf)$", name):
                continue
            looks_input = re.search(r"(/data/|/input|/workspace/data|/app/data|/home/\w+/data)", p) or re.search(r"\b(given|provided|ships?|shipped|input|recording|dataset)\b[^.\n]{0,80}" + re.escape(name), b.instruction)
            if looks_input and name not in env_names:
                missing.append(p)
        if missing and not downloads and not generates:
            return self.warn(f"{len(missing)} input file(s) named in the instruction are not in environment/ and the Dockerfile neither downloads nor generates data", evidence=missing)
        if missing and generates and not downloads:
            return self.info(f"{len(missing)} input file(s) not in environment/; the Dockerfile runs scripts that may generate them", evidence=missing)
        if missing:
            return self.info(f"{len(missing)} input file(s) not in environment/ but the Dockerfile fetches data at build time; confirm they land where the instruction says", evidence=missing)
        return self.ok("input files named in the instruction are shipped in environment/ (or none are named)")


@register
class NoVerifierInternalsLeak(Check):
    id = "instruction.no_verifier_internals"
    name = "Instruction does not point at verifier internals"
    category = "instruction"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        hits = [(ln, l) for ln, l in enumerate(b.instruction.splitlines(), 1)
                if re.search(r"(/tests/|\btests/sealed|\bsealed/|ground[_ -]?truth\.(npy|csv|json)|/logs/verifier|reward\.txt)", l)]
        if hits:
            return self.warn(f"{len(hits)} line(s) mention verifier-side paths (tests/, sealed, /logs/verifier, reward.txt)", evidence=[f"L{ln}: {l[:160]}" for ln, l in hits])
        return self.ok("no verifier-side paths mentioned")


@register
class NoAskUser(Check):
    id = "instruction.no_ask_user"
    name = "Instruction does not invite the agent to ask questions"
    category = "instruction"
    default_severity = Severity.INFO

    def run(self, b, cfg):
        hits = [(ln, l) for ln, l in enumerate(b.instruction.splitlines(), 1)
                if re.search(r"\b(ask (the )?(user|me|us)|if (anything is )?unclear,? ask|feel free to ask|let me know)\b", l, re.I)]
        if hits:
            return self.warn("the instruction invites questions, but an unattended agent cannot ask; state assumptions instead", evidence=[f"L{ln}: {l[:160]}" for ln, l in hits])
        if re.search(r"\b(do not|don't|never) (stop to )?ask\b|unattended|no human", b.instruction, re.I):
            return self.ok("instruction states the agent works unattended")
        return self.info("instruction neither invites nor forbids questions; consider stating that the run is unattended")


@register
class AbsoluteDeliverablePaths(Check):
    id = "instruction.absolute_paths"
    name = "Deliverable locations are absolute"
    category = "instruction"
    default_severity = Severity.INFO

    def run(self, b, cfg):
        outs = instruction_outputs(b.instruction)
        rel = sorted(o for o in outs if "/" not in o and o not in GENERIC)
        absolute = sorted(o for o in outs if o.startswith("/"))
        if outs and not absolute:
            return self.warn("deliverables are named without an absolute location; agents may write them anywhere", evidence=rel[:10])
        return self.ok(f"{len(absolute)} absolute path(s) named" if absolute else "no deliverable paths to check")
