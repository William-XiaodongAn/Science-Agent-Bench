"""Web UI: upload a Harbor task (zip), or point at a local path / git URL, run the checks, browse the report.
Start with: python -m dq serve  (then open http://127.0.0.1:8765)"""
from __future__ import annotations

import json
import os
import shutil
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse

from ..report import to_html, to_json, to_markdown
from ..runner import run_task

RUNS = Path(os.environ.get("DQ_RUNS_DIR", "dq_runs")).resolve()
RUNS.mkdir(parents=True, exist_ok=True)
STATIC = Path(__file__).with_name("static")
app = FastAPI(title="dq: Harbor task data-quality verifier")
_pool = ThreadPoolExecutor(max_workers=int(os.environ.get("DQ_WORKERS", "2")))
_lock = threading.Lock()


def _status_path(run_id: str) -> Path:
    return RUNS / run_id / "status.json"


def _write_status(run_id: str, **kw):
    with _lock:
        p = _status_path(run_id)
        cur = json.loads(p.read_text()) if p.exists() else {}
        cur.update(kw)
        p.write_text(json.dumps(cur, indent=1, default=str))


def _job(run_id: str, source: str, subdir: str | None, options: dict):
    d = RUNS / run_id
    try:
        _write_status(run_id, state="running")
        rep = run_task(source, subdir=subdir, options=options)
        (d / "report.json").write_text(to_json(rep)); (d / "report.md").write_text(to_markdown(rep)); (d / "report.html").write_text(to_html(rep))
        _write_status(run_id, state="done", verdict=rep.verdict.value, task_name=rep.task_name, counts=rep.counts, finished_at=rep.finished_at)
    except Exception as e:  # noqa: BLE001
        _write_status(run_id, state="error", error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:])


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text()


@app.post("/api/run")
async def start_run(file: UploadFile | None = File(default=None), source: str = Form(default=""), subdir: str = Form(default=""),
                    llm: bool = Form(default=False), exec_checks: bool = Form(default=False), urls: bool = Form(default=True)):
    run_id = uuid.uuid4().hex[:10]
    d = RUNS / run_id
    d.mkdir(parents=True)
    if file is not None and file.filename:
        target = d / "upload.zip"
        with open(target, "wb") as fh:
            shutil.copyfileobj(file.file, fh)
        src = str(target)
        label = file.filename
    elif source.strip():
        src = source.strip()
        label = src
    else:
        shutil.rmtree(d, ignore_errors=True)
        raise HTTPException(400, "upload a .zip or give a path / git URL")
    options = {"network": bool(urls), "llm": bool(llm), "exec": bool(exec_checks)}
    _write_status(run_id, state="queued", source=label, options=options, subdir=subdir or None)
    _pool.submit(_job, run_id, src, subdir or None, options)
    return {"run_id": run_id}


@app.get("/api/runs")
def list_runs():
    out = []
    for d in sorted(RUNS.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        p = d / "status.json"
        if p.exists():
            s = json.loads(p.read_text()); s["run_id"] = d.name; out.append(s)
    return out[:200]


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    p = _status_path(run_id)
    if not p.exists():
        raise HTTPException(404, "unknown run")
    status = json.loads(p.read_text())
    rep = RUNS / run_id / "report.json"
    return {"status": status, "report": json.loads(rep.read_text()) if rep.exists() else None}


@app.get("/api/runs/{run_id}/report.{fmt}")
def get_report(run_id: str, fmt: str):
    p = RUNS / run_id / f"report.{fmt}"
    if fmt not in ("json", "md", "html") or not p.exists():
        raise HTTPException(404, "no such report")
    if fmt == "html":
        return HTMLResponse(p.read_text())
    if fmt == "md":
        return PlainTextResponse(p.read_text())
    return FileResponse(p)


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str):
    d = RUNS / run_id
    if not d.exists():
        raise HTTPException(404, "unknown run")
    shutil.rmtree(d)
    return JSONResponse({"deleted": run_id})
