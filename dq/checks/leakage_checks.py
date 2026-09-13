"""Answer-leakage and reward-hacking surface checks."""
from __future__ import annotations

import re

from ..model import Severity
from .base import Check, cfg_get, register

CODE_EXT = (".py", ".sh", ".bash", "Dockerfile", ".toml", ".txt", ".md", ".json", ".yaml", ".yml")


def sealed_files(b) -> list[str]:
    """Data files under tests/ (anything that is not verifier code)."""
    return [f for f in b.tests_files if not f.endswith((".py", ".sh", ".bash", ".toml", ".md", "Dockerfile", "requirements.txt", "SHA256SUMS", ".txt"))]


@register
class SealedNotInEnvironment(Check):
    id = "leakage.sealed_not_in_environment"
    name = "Ground-truth files under tests/ are not shipped to the agent"
    category = "leakage"
    default_severity = Severity.BLOCK
    description = "Byte-identical copies of tests/ data inside environment/ or solution/ hand the answer to the agent."

    def run(self, b, cfg):
        sealed = sealed_files(b)
        if not sealed:
            return self.info("no data files under tests/ (ground truth is computed or lives in the verifier image)")
        env_hashes = {}
        for f in b.env_files + b.solution_files:
            if b.size(f) > 0 and b.size(f) < 500_000_000:
                env_hashes.setdefault(b.sha256(f), []).append(f)
        inputish = re.compile(r"(input|data/|vocab|schema|config|starter|template|lakefile|requirements|README|LICENSE)", re.I)     # tests-side path
        env_inputish = re.compile(r"(input|vocab|schema|config|starter|template|lakefile|requirements|README|LICENSE)", re.I)      # agent-side twin (data/ is where answers would be dropped)
        answer_like = re.compile(r"(truth|ground_?truth|\bgt\b|expected|answer|labels?\.|golden_?(output|result|answer)|reference_(output|result|solution)|oracle_(output|result))", re.I)
        leaks, oracle_copies, shared = [], [], []
        for f in sealed:
            if b.size(f) == 0:
                continue
            h = b.sha256(f)
            if h in env_hashes:
                twins = env_hashes[h]
                line = f"{f} == {', '.join(twins)}"
                env_twins = [t for t in twins if t.startswith("environment/")]
                if answer_like.search(f) and env_twins and not inputish.search(f) and not all(env_inputish.search(t) for t in env_twins):
                    leaks.append(line)
                elif answer_like.search(f) and not env_twins:
                    oracle_copies.append(line)
                else:
                    shared.append(line)
        if leaks:
            return self.fail(f"{len(leaks)} answer-like file(s) under tests/ are byte-identical to files the agent can see", evidence=leaks + shared[:5])
        if oracle_copies:
            return self.warn("the reference solution ships a copy of a ground-truth file: the oracle pastes the answer, so solvability is not demonstrated", evidence=oracle_copies + shared[:5])
        if shared:
            return self.info(f"{len(shared)} tests/ file(s) are byte-identical to environment/ files: inputs shared with the verifier; confirm none is the target", evidence=shared[:10])
        same_name = [f for f in sealed if any(e.split('/')[-1] == f.split('/')[-1] for e in b.env_files)]
        if same_name:
            return self.info("some tests/ data files share a name with environment/ files (different content); confirm the agent copy is not the answer", evidence=same_name[:10])
        return self.ok(f"{len(sealed)} sealed file(s), none duplicated in the agent environment")


@register
class DockerfileNoTestsOrSolution(Check):
    id = "leakage.dockerfile_no_tests_solution"
    name = "Environment Dockerfile does not copy tests/ or solution/"
    category = "leakage"
    default_severity = Severity.BLOCK

    def run(self, b, cfg):
        dfs = [f for f in b.env_files if f.endswith("Dockerfile") or "docker-compose" in f]
        if not dfs:
            return self.skip("no environment Dockerfile")
        hits = b.grep(r"^\s*(COPY|ADD)\s+(\.\./)?(tests|solution)(/|\s)|\.\./tests|\.\./solution", dfs)
        wide = b.grep(r"^\s*(COPY|ADD)\s+\.\s|^\s*(COPY|ADD)\s+\./\s|^\s*(COPY|ADD)\s+\.\.\s", dfs)
        ev = [f"{f}:{ln}: {l}" for f, ln, l in hits + wide]
        if hits:
            return self.fail("environment image copies tests/ or solution/ into the agent container", evidence=ev)
        if wide:
            # COPY . from environment/ is fine (build context = environment/); from the task root it is not
            return self.info("Dockerfile copies its whole build context; fine if the context is environment/, a leak if it is the task root", evidence=ev)
        return self.ok("no COPY/ADD of tests/ or solution/")


@register
class InstructionNoGroundTruthValues(Check):
    id = "leakage.instruction_no_ground_truth_values"
    name = "Instruction does not contain the sealed answer"
    category = "leakage"
    default_severity = Severity.WARN
    description = "Compares numeric literals and identifiers in small sealed JSON/CSV/TXT files with the instruction text."

    def run(self, b, cfg):
        small = [f for f in sealed_files(b) if f.endswith((".json", ".csv", ".tsv", ".txt")) and 0 < b.size(f) < 200_000]
        if not small:
            return self.skip("no small text-based sealed files to compare")
        instr = b.instruction
        instr_nums = set(re.findall(r"(?<![\w.])(\d+\.\d{3,}|\d{5,})(?![\w.])", instr))
        leaks = []
        for f in small:
            nums = set(re.findall(r"(?<![\w.])(\d+\.\d{3,}|\d{5,})(?![\w.])", b.text(f)))
            common = nums & instr_nums
            if len(common) >= 3:
                leaks.append(f"{f}: {len(common)} numeric literals also in the instruction, e.g. {sorted(common)[:3]}")
        if leaks:
            return self.warn("sealed values appear verbatim in the instruction", evidence=leaks)
        return self.ok(f"{len(small)} sealed text file(s) share no distinctive numbers with the instruction")


@register
class GateValuesDisclosure(Check):
    id = "leakage.gate_values_disclosed"
    name = "Verifier gate values quoted in the instruction (review whether intended)"
    category = "leakage"
    default_severity = Severity.INFO
    description = ("Numbers from [verifier.env]/[metadata] that appear in the instruction. A primary pass bar may be stated; "
                   "expert-quality gates (smoothness, outline shape, rubric thresholds) should not be, or they become optimisation targets.")

    def run(self, b, cfg):
        if not b.toml:
            return self.skip("task.toml not parseable")
        values = {}
        for sect in ("verifier", "metadata"):
            d = b.toml.get(sect, {})
            if sect == "verifier" and isinstance(d, dict):
                d = d.get("env", {})
            if isinstance(d, dict):
                for k, v in d.items():
                    m = re.fullmatch(r"\s*(\d+\.\d+|\d+)\s*", str(v))
                    if m and float(m.group(1)) not in (0, 1) and len(m.group(1)) >= 3:
                        values[k] = m.group(1)
        found = {k: v for k, v in values.items() if re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d])", b.instruction)}
        quality_like = {k: v for k, v in found.items() if re.search(r"(SMOOTH|ROUGH|COMPACT|OUTSIDE|JUDGE|CUSP|SAGITTA|SHAPE|QUALITY|MASK_(?!IOU|COVERAGE))", k)}
        if quality_like:
            return self.warn("quality-gate values appear in the instruction; agents will optimise the number instead of the property", evidence=[f"{k}={v}" for k, v in quality_like.items()])
        if found:
            return self.info("pass-bar values stated in the instruction (acceptable for a primary metric)", evidence=[f"{k}={v}" for k, v in found.items()])
        return self.ok("no verifier gate values quoted in the instruction")


@register
class SolutionIndependentOfTests(Check):
    id = "leakage.solution_independent_of_tests"
    name = "Solution does not read tests/ or write the reward channel"
    category = "leakage"
    default_severity = Severity.BLOCK

    def run(self, b, cfg):
        if not b.solution_files:
            return self.skip("no solution/")
        hits = [(f, ln, l) for f, ln, l in b.grep(r"(/tests/|\btests/sealed|\.\./tests|/logs/verifier|reward\.txt)", [f for f in b.solution_files if b.is_text(f)])
                if not l.lstrip().startswith("#")]
        if hits:
            return self.fail("the reference solution touches verifier-side paths (copying the answer or writing the reward)", evidence=[f"{f}:{ln}: {l}" for f, ln, l in hits])
        return self.ok("solution reads only the agent-visible environment")


@register
class SolutionNotHardcoded(Check):
    id = "leakage.solution_not_hardcoded"
    name = "Reference solution computes rather than pastes answers"
    category = "leakage"
    default_severity = Severity.INFO

    def run(self, b, cfg):
        code_files = [f for f in b.solution_files if f.endswith((".py", ".sh", ".R", ".jl")) and b.is_text(f)]
        if not code_files:
            return self.skip("no solution code")
        big_literals = b.grep(r"(\[\s*-?\d[\d.,\s-]{200,}\]|np\.array\(\[\s*-?\d[\d.,\s-]{120,})", code_files)
        data_in_solution = [f for f in b.solution_files if f.endswith((".npy", ".npz", ".csv", ".json", ".h5", ".pkl")) and b.size(f) > 20_000]
        if big_literals or data_in_solution:
            return self.warn("solution contains large literal arrays or data files: it may paste the answer instead of computing it (allowed only if the task is 'produce this artifact' and the file is not the ground truth)",
                             evidence=[f"{f}:{ln}" for f, ln, _ in big_literals][:5] + data_in_solution[:5])
        return self.ok(f"{len(code_files)} solution code file(s), no large literal data")


@register
class CanaryPresent(Check):
    id = "leakage.canary_present"
    name = "Canary string present in text files"
    category = "leakage"
    default_severity = Severity.INFO

    def run(self, b, cfg):
        pattern = cfg_get(cfg, "canary.pattern", "")
        if not pattern:
            return self.skip("no canary pattern configured")
        rx = re.compile(pattern)
        texts = [f for f in b.files if b.is_text(f) and f.endswith((".md", ".toml", ".yaml", ".yml", ".py", ".sh")) and b.size(f) > 0]
        missing = [f for f in texts if not rx.search(b.text(f))]
        if not texts:
            return self.skip("no text files")
        if len(missing) == len(texts):
            return self.warn("no canary string in any text file (contamination cannot be detected later)")
        if missing:
            return self.info(f"canary missing from {len(missing)} of {len(texts)} text file(s)", evidence=missing[:15])
        return self.ok(f"canary present in all {len(texts)} text files")


@register
class WorkspaceNoAnswerFiles(Check):
    id = "leakage.workspace_no_answer_files"
    name = "Agent workspace has no answer-looking files"
    category = "leakage"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        sus = [f for f in b.env_files if re.search(r"(answer|solution|ground_?truth|sealed|expected|reference_output|\bgt_)", f.split("/")[-1], re.I)
               and not re.search(r"(starter|template|submit|example|baseline|skeleton|stub|scaffold|README)", f.split("/")[-1], re.I)]
        if sus:
            return self.warn("files in environment/ are named like answers; confirm they are inputs, not the target", evidence=sus[:15])
        return self.ok("no answer-looking file names in environment/")
