"""Optional execution checks (run with --exec): build the environment, run the oracle and a no-op agent through the
verifier with Harbor, and read the rewards. Requires `harbor` and Docker (or another Harbor environment backend)."""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import tempfile

from ..model import Severity
from .base import Check, cfg_get, register


def _harbor_run(task_root, agent: str, env_backend: str, timeout: float, extra: list[str]) -> dict:
    out = tempfile.mkdtemp(prefix=f"dq-{agent}-")
    cmd = ["harbor", "run", "-p", str(task_root), "-a", agent, "-e", env_backend, "-y", "-o", out] + extra
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"harbor run timed out after {timeout:.0f} s", "out": out}
    results = glob.glob(os.path.join(out, "*", "*", "result.json"))
    reward = None
    exc = None
    for f in results:
        try:
            d = json.load(open(f))
            vr = d.get("verifier_result") or {}
            reward = (vr.get("rewards") or {}).get("reward", vr.get("reward"))
            exc = (d.get("exception_info") or {}).get("exception_type")
        except Exception:  # noqa: BLE001
            pass
    return {"ok": r.returncode == 0, "rc": r.returncode, "reward": reward, "exception": exc,
            "stderr": r.stderr[-1500:], "stdout": r.stdout[-800:], "out": out}


@register
class ExecOracleAndNop(Check):
    id = "exec.oracle_passes_nop_fails"
    name = "Environment builds; oracle passes; doing nothing fails"
    category = "execution"
    default_severity = Severity.BLOCK
    needs = frozenset({"exec"})
    description = "Runs `harbor run -a oracle` and `-a nop` on the task. The oracle must reach the pass reward; the nop must not."

    def run(self, b, cfg):
        if not shutil.which("harbor"):
            return self.skip("harbor CLI not on PATH")
        backend = os.environ.get("DQ_HARBOR_ENV", cfg_get(cfg, "exec.environment", "docker"))
        timeout = float(cfg_get(cfg, "exec.timeout_sec", 3600))
        extra = []
        env_file = os.environ.get("DQ_HARBOR_ENV_FILE")
        if env_file:
            extra += ["--env-file", env_file]
        oracle = _harbor_run(b.root, "oracle", backend, timeout, extra)
        if "error" in oracle:
            return self.fail(oracle["error"])
        nop = _harbor_run(b.root, "nop", backend, timeout, extra)
        ev = [f"oracle: rc={oracle.get('rc')} reward={oracle.get('reward')} exception={oracle.get('exception')}",
              f"nop: rc={nop.get('rc')} reward={nop.get('reward')} exception={nop.get('exception')}"]
        if oracle.get("exception"):
            ev.append("oracle stderr: " + oracle.get("stderr", "")[-600:])
        pass_min = float(cfg_get(cfg, "exec.oracle_min_reward", 1.0))
        o, n = oracle.get("reward"), nop.get("reward")
        if o is None:
            return self.fail("oracle produced no reward (build or verifier failure)", evidence=ev)
        if float(o) < pass_min:
            return self.fail(f"oracle reward {o} below the pass level {pass_min}", evidence=ev)
        if n is not None and float(n) >= pass_min:
            return self.fail(f"doing nothing already reaches reward {n}", evidence=ev)
        return self.ok(f"oracle reward {o}, nop reward {n}", evidence=ev, data={"oracle": o, "nop": n})
