"""URL reachability of links in the task's text files (instruction, README, task.toml, task.yaml)."""
from __future__ import annotations

import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from ..model import Severity
from .base import Check, cfg_get, register

URL_RX = re.compile(r"https?://[^\s<>\"'`)\]}]+")


def _probe(url: str, timeout: float) -> tuple[str, str]:
    url = url.rstrip(".,;:")
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 (dq-verifier link check)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return url, f"{r.status}"
    except urllib.error.HTTPError as e:
        if e.code in (403, 405, 429):   # HEAD refused or bot-blocked: try GET once
            try:
                req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0 (dq-verifier link check)"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return url, f"{r.status}"
            except urllib.error.HTTPError as e2:
                return url, f"HTTP {e2.code}"
            except Exception as e2:  # noqa: BLE001
                return url, f"error: {type(e2).__name__}"
        return url, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return url, f"error: {type(e).__name__}"


@register
class UrlsReachable(Check):
    id = "urls.reachable"
    name = "Links in the task text resolve"
    category = "urls"
    default_severity = Severity.WARN
    needs = frozenset({"network"})

    def run(self, b, cfg):
        files = [f for f in ("instruction.md", "README.md") if b.exists(f)]      # prose only: task.toml holds API base URLs, not links
        ignore = cfg_get(cfg, "urls.ignore", ["localhost", "127.0.0.1", "example.com", "0.0.0.0"]) + ["api.anthropic.com", "api.openai.com", "generativelanguage.googleapis.com"]
        urls = {}
        for f in files:
            for m in URL_RX.finditer(b.text(f)):
                u = m.group(0).rstrip(".,;:)")
                if any(i in u for i in ignore):
                    continue
                urls.setdefault(u, f)
        if not urls:
            return self.ok("no external URLs in the task text")
        timeout = float(cfg_get(cfg, "urls.timeout_sec", 8))
        with ThreadPoolExecutor(8) as ex:
            probes = list(ex.map(lambda u: _probe(u, timeout), list(urls)[:60]))
        bad = [(u, s) for u, s in probes if not s.isdigit() or int(s) >= 400]
        soft = [(u, s) for u, s in bad if s in ("HTTP 403", "HTTP 429", "HTTP 405")]
        hard = [(u, s) for u, s in bad if (u, s) not in soft]
        ev = [f"{s}: {u} ({urls[u]})" for u, s in bad]
        if hard:
            return self.warn(f"{len(hard)} of {len(urls)} URL(s) unreachable or 4xx/5xx" + (f"; {len(soft)} bot-blocked (403/429), probably fine" if soft else ""), evidence=ev)
        if soft:
            return self.info(f"{len(soft)} URL(s) refused automated access (403/429); open them by hand", evidence=ev)
        return self.ok(f"all {len(urls)} URL(s) reachable")
