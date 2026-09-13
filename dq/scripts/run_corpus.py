"""Run dq over every task under a directory and summarise which checks fire (for calibration)."""
from __future__ import annotations

import glob
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from ..loader import TaskBundle
from ..model import Status
from ..report import to_json, to_markdown
from ..runner import load_config, run_bundle


def run_corpus(root: str, pattern: str = "*", out: str = "dq_runs/corpus", llm: bool = False, network: bool = True, config_path: str | None = None) -> int:
    cfg = load_config(config_path)
    dirs = sorted(d for d in glob.glob(os.path.join(root, pattern)) if os.path.isdir(d) and os.path.exists(os.path.join(d, "task.toml")))
    if not dirs:
        print(f"no task directories matching {pattern} under {root}")
        return 1
    Path(out).mkdir(parents=True, exist_ok=True)
    fires = defaultdict(Counter)
    rows = []
    for d in dirs:
        b = TaskBundle(Path(d), d)
        rep = run_bundle(b, cfg, {"network": network, "llm": llm, "exec": False})
        name = b.root.name
        (Path(out) / f"{name}.json").write_text(to_json(rep)); (Path(out) / f"{name}.md").write_text(to_markdown(rep))
        for r in rep.results:
            fires[r.id][r.status.value] += 1
        issues = [f"{r.id}={r.status.value}" for r in rep.results if r.status in (Status.FAIL, Status.WARN, Status.ERROR)]
        rows.append((name, rep.verdict.value, rep.counts.get("fail", 0), rep.counts.get("warn", 0), "; ".join(issues)))
        print(f"{rep.verdict.value:13s} {name:45s} fail={rep.counts.get('fail', 0)} warn={rep.counts.get('warn', 0)}")
    L = [f"# dq corpus summary: {root} ({len(dirs)} tasks)", "", "| task | verdict | fails | warns | issues |", "|---|---|---|---|---|"]
    L += [f"| {n} | {v} | {f} | {w} | {i} |" for n, v, f, w, i in rows]
    L += ["", "## How often each check fires", "", "| check | pass | warn | fail | info | skip | error |", "|---|---|---|---|---|---|---|"]
    for cid, c in fires.items():
        L.append(f"| `{cid}` | {c['pass']} | {c['warn']} | {c['fail']} | {c['info']} | {c['skip']} | {c['error']} |")
    (Path(out) / "SUMMARY.md").write_text("\n".join(L) + "\n")
    json.dump({k: dict(v) for k, v in fires.items()}, open(Path(out) / "fires.json", "w"), indent=1)
    verdicts = Counter(v for _, v, *_ in rows)
    print(f"\nverdicts: {dict(verdicts)}; summary in {out}/SUMMARY.md")
    return 0
