"""CLI: python -m dq run|corpus|serve|list-checks"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dq", description="Data-quality verifier for Harbor-format science tasks")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="check one task (directory, .zip or git URL)")
    r.add_argument("source"); r.add_argument("--subdir", default=None, help="task folder inside a zip or repo")
    r.add_argument("--llm", action="store_true", help="also run the advisory LLM judge (needs credentials in env)")
    r.add_argument("--exec", action="store_true", help="also build and run oracle/nop through harbor (needs harbor + Docker)")
    r.add_argument("--no-urls", action="store_true", help="skip URL reachability (offline)")
    r.add_argument("--only", default=None, help="comma-separated check ids to run")
    r.add_argument("--config", default=None); r.add_argument("--out", default=None, help="directory for report.json/.md/.html")
    r.add_argument("--quiet", action="store_true")
    c = sub.add_parser("corpus", help="check every task under a directory and summarise")
    c.add_argument("root"); c.add_argument("--glob", default="*", help="task directories relative to root, e.g. 'tasks/*/*'")
    c.add_argument("--llm", action="store_true"); c.add_argument("--no-urls", action="store_true"); c.add_argument("--config", default=None)
    c.add_argument("--out", default="dq_runs/corpus", help="output directory")
    s = sub.add_parser("serve", help="start the web UI"); s.add_argument("--host", default="127.0.0.1"); s.add_argument("--port", type=int, default=8765)
    sub.add_parser("list-checks", help="list registered checks")
    a = ap.parse_args(argv)

    if a.cmd == "list-checks":
        from .checks.base import REGISTRY
        for cls in REGISTRY:
            print(f"{cls.id:45s} {cls.default_severity.value:9s} {cls.category:12s} {cls.name}")
        return 0
    if a.cmd == "serve":
        import uvicorn
        uvicorn.run("dq.web.app:app", host=a.host, port=a.port, reload=False)
        return 0
    if a.cmd == "corpus":
        from .scripts.run_corpus import run_corpus
        return run_corpus(a.root, a.glob, out=a.out, llm=a.llm, network=not a.no_urls, config_path=a.config)

    from .report import to_html, to_json, to_markdown
    from .runner import run_task
    rep = run_task(a.source, subdir=a.subdir, config_path=a.config,
                   options={"network": not a.no_urls, "llm": a.llm, "exec": a.exec, "only": a.only.split(",") if a.only else None})
    if a.out:
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(to_json(rep)); (out / "report.md").write_text(to_markdown(rep)); (out / "report.html").write_text(to_html(rep))
    if not a.quiet:
        print(to_markdown(rep))
    return 0 if rep.verdict.value != "FAIL" else 2


if __name__ == "__main__":
    sys.exit(main())
