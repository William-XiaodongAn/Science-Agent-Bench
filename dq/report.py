"""Render a Report as JSON, Markdown or HTML."""
from __future__ import annotations

import html
import json

from .model import Report, Status

ORDER = [Status.FAIL, Status.ERROR, Status.WARN, Status.INFO, Status.PASS, Status.SKIP]
LABEL = {Status.FAIL: "FAIL", Status.ERROR: "ERROR", Status.WARN: "WARN", Status.INFO: "INFO", Status.PASS: "PASS", Status.SKIP: "SKIP"}


def to_json(rep: Report) -> str:
    return json.dumps(rep.to_dict(), indent=1, default=str)


def to_markdown(rep: Report) -> str:
    L = [f"# DQ report: `{rep.task_name}`", "", f"Source: `{rep.source}`  ", f"Verdict: **{rep.verdict.value}**  ",
         f"Counts: " + ", ".join(f"{k} {v}" for k, v in rep.counts.items() if v), f"Run: {rep.started_at} to {rep.finished_at}", ""]
    L += ["## Why", ""] + [f"- {r}" for r in rep.verdict_reasons] + [""]
    L += ["## Checks", "", "| status | severity | check | reason |", "|---|---|---|---|"]
    for st in ORDER:
        for r in rep.results:
            if r.status == st:
                L.append(f"| {LABEL[st]} | {r.severity.value} | `{r.id}` {r.name} | {r.reason.replace('|', '/')} |")
    ev = [r for r in rep.results if r.evidence]
    if ev:
        L += ["", "## Evidence", ""]
        for r in ev:
            L.append(f"**{r.id}** ({LABEL[r.status]})")
            L += [f"- {e}" for e in r.evidence] + [""]
    return "\n".join(L)


def to_html(rep: Report) -> str:
    rows = []
    for st in ORDER:
        for r in rep.results:
            if r.status == st:
                ev = "".join(f"<li>{html.escape(e)}</li>" for e in r.evidence)
                rows.append(f"<tr class='{st.value}'><td><span class='badge {st.value}'>{LABEL[st]}</span></td><td>{r.severity.value}</td>"
                            f"<td><code>{html.escape(r.id)}</code><br><small>{html.escape(r.name)}</small></td>"
                            f"<td>{html.escape(r.reason)}{('<ul>' + ev + '</ul>') if ev else ''}</td></tr>")
    return f"""<h2>{html.escape(rep.task_name)} — <span class='badge verdict-{rep.verdict.value}'>{rep.verdict.value}</span></h2>
<p><small>{html.escape(rep.source)}</small></p><ul>{''.join(f'<li>{html.escape(x)}</li>' for x in rep.verdict_reasons)}</ul>
<table class='dq'><thead><tr><th>status</th><th>severity</th><th>check</th><th>reason / evidence</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"""
