"""Advisory LLM judge (run with --llm): brief quality assessment of solvability, verifiability, domain and tier fit, and
whether the task can improve agent capabilities (e.g. a wet-lab step no agent can perform is out of reach).

Deliberately lenient on domain knowledge: it flags only clear problems and states its confidence; domain experts review
and may change the rubric below. Credentials come from the environment (DQ_LLM_API_KEY / DQ_LLM_BASE_URL, falling back
to ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL); the model is DQ_LLM_MODEL or the config value."""
from __future__ import annotations

import json
import os
import re
import urllib.request

from ..model import Severity, Status
from .base import Check, cfg_get, register

RUBRIC = """You are a benchmark-quality reviewer doing a FIRST PASS on a science task for AI agents. Domain experts will
review after you, so do not be strict on domain detail; flag only clear problems, and say how confident you are.

Assess, each with a one-sentence reason:
1. solvable: could a competent scientist with the shipped inputs and tools produce the deliverable within the budget?
   ("yes" | "uncertain" | "no")
2. verifiable: does the verifier, as described, decide correctness from the deliverable in a way that a correct solution
   passes and a wrong or empty one fails? ("yes" | "uncertain" | "no")
3. domain: which of these domains fits best: {domains}. Report the best fit and whether it matches the declared one.
4. tier: which tier fits: {tiers}. Report the best fit and whether it matches the declared one.
5. capability_gain: what capability would an agent have to improve to pass (e.g. inferring an expert's standard from raw
   data, building a method, careful numerics)? Is the task agent-feasible, i.e. entirely computational with the shipped
   inputs? A task that needs a wet lab, a physical instrument, a human in the loop, or an interactive question to the user
   is NOT agent-feasible. ("feasible" | "partly" | "infeasible")
6. leakage_or_hacking_notes: anything in the instruction or file list that hands the agent the answer, names verifier
   internals, states quality thresholds it could optimise directly, or lets a trivial submission pass.
7. clarity_issues: ambiguities that two competent readers would resolve differently (ignore missing scoring details;
   the verifier's internals need not be documented).
8. recommendation: "pass" | "needs_review" | "fail", with confidence 0-1 and a two-sentence justification.

Return JSON only:
{{"solvable": {{"verdict": "...", "reason": "..."}}, "verifiable": {{"verdict": "...", "reason": "..."}},
 "domain": {{"best_fit": "...", "matches_declared": true/false/null, "reason": "..."}},
 "tier": {{"best_fit": "...", "matches_declared": true/false/null, "reason": "..."}},
 "capability_gain": {{"capability": "...", "feasibility": "...", "reason": "..."}},
 "leakage_or_hacking_notes": ["..."], "clarity_issues": ["..."],
 "recommendation": {{"verdict": "...", "confidence": 0.0, "justification": "..."}}}}"""


def _packet(b, cfg) -> str:
    md = b.toml.get("metadata", {}) if b.toml and isinstance(b.toml.get("metadata"), dict) else {}
    max_chars = int(cfg_get(cfg, "llm.max_instruction_chars", 14000))
    tree = "\n".join(f"  {f} ({b.size(f)} B)" for f in b.files[:150])
    test_sh = b.text("tests/test.sh")[:1500] if b.exists("tests/test.sh") else "(missing)"
    graders = [f for f in b.tests_files if f.endswith(".py")]
    grader_head = ""
    for g in graders[:2]:
        grader_head += f"\n--- {g} (head) ---\n" + "\n".join(b.text(g).splitlines()[:120])
    declared = {k: md.get(k) for k in ("domain", "tier", "field", "subfield", "difficulty", "human_baseline") if md.get(k)}
    if b.yaml:
        for k in ("domain", "tier", "difficulty", "human_baseline"):
            if b.yaml.get(k) and k not in declared:
                declared[k] = b.yaml.get(k)
    return (f"TASK NAME: {b.name}\nDECLARED METADATA: {json.dumps(declared, default=str)}\n"
            f"TASK.TOML (abridged): {json.dumps({k: b.toml.get(k) for k in ('task', 'agent', 'verifier', 'environment') if b.toml and k in b.toml}, default=str)[:2500]}\n\n"
            f"FILE TREE:\n{tree}\n\nINSTRUCTION.MD:\n{b.instruction[:max_chars]}\n\n"
            f"TESTS/TEST.SH:\n{test_sh}\n{grader_head[:6000]}\n")


def call_llm(prompt_text: str, cfg) -> str:
    model = os.environ.get("DQ_LLM_MODEL") or cfg_get(cfg, "llm.model", "anthropic/claude-fable-5-1")
    base = os.environ.get("DQ_LLM_BASE_URL") or os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    key = os.environ.get("DQ_LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("no LLM credentials: set DQ_LLM_API_KEY (or ANTHROPIC_API_KEY) and optionally DQ_LLM_BASE_URL")
    body = {"model": model, "max_tokens": int(cfg_get(cfg, "llm.max_tokens", 1800)),
            "messages": [{"role": "user", "content": prompt_text}]}
    req = urllib.request.Request(base.rstrip("/") + "/v1/messages", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=float(cfg_get(cfg, "llm.timeout_sec", 240))) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300] if hasattr(e, "read") else ""
        raise RuntimeError(f"HTTP {e.code} from {base.rstrip('/')}/v1/messages (model {model}): {detail}") from None
    text = "".join(c.get("text", "") for c in d.get("content", []))
    if not text.strip():
        thinking = (d.get("usage", {}).get("output_tokens_details") or {}).get("thinking_tokens")
        raise RuntimeError(f"empty reply (stop_reason={d.get('stop_reason')}, output_tokens={d.get('usage', {}).get('output_tokens')}, thinking_tokens={thinking}); raise llm.max_tokens")
    return text


def parse_json(txt: str) -> dict | None:
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


@register
class LLMJudge(Check):
    id = "llm.advisory_judge"
    name = "Advisory LLM judge: solvable, verifiable, domain/tier fit, capability gain"
    category = "llm"
    default_severity = Severity.ADVISORY
    needs = frozenset({"llm"})

    def run(self, b, cfg):
        domains = list(cfg_get(cfg, "taxonomy.domains", {}).keys())
        tiers = cfg_get(cfg, "taxonomy.tiers", {})
        prompt = RUBRIC.format(domains=", ".join(domains), tiers="; ".join(f"{k}: {v}" for k, v in tiers.items())) + "\n\n" + _packet(b, cfg)
        try:
            txt = call_llm(prompt, cfg)
        except RuntimeError as e:
            if "empty reply" in str(e):        # the model spent the budget thinking: retry once with a larger budget
                big = dict(cfg); big["llm"] = dict(cfg.get("llm", {})); big["llm"]["max_tokens"] = int(cfg_get(cfg, "llm.max_tokens", 8000)) * 2
                try:
                    txt = call_llm(prompt, big)
                except Exception as e2:  # noqa: BLE001
                    return self.skip(f"LLM unavailable: {type(e2).__name__}: {str(e2)[:200]}")
            else:
                return self.skip(f"LLM unavailable: {str(e)[:200]}")
        except Exception as e:  # noqa: BLE001
            return self.skip(f"LLM unavailable: {type(e).__name__}: {str(e)[:160]}")
        out = parse_json(txt)
        if not out:
            txt2 = call_llm(prompt + "\n\nReply with the JSON object only.", cfg)
            out = parse_json(txt2)
        if not out:
            return self.result(Status.ERROR, "judge reply was not parseable JSON", evidence=[txt[:300]])
        rec = out.get("recommendation", {}) or {}
        verdict = str(rec.get("verdict", "needs_review")).lower()
        conf = rec.get("confidence")
        ev = []
        for k in ("solvable", "verifiable"):
            v = out.get(k, {}) or {}
            ev.append(f"{k}: {v.get('verdict')} — {v.get('reason')}")
        dom = out.get("domain", {}) or {}
        ev.append(f"domain best fit: {dom.get('best_fit')} (matches declared: {dom.get('matches_declared')}) — {dom.get('reason')}")
        tier = out.get("tier", {}) or {}
        ev.append(f"tier best fit: {tier.get('best_fit')} (matches declared: {tier.get('matches_declared')}) — {tier.get('reason')}")
        cap = out.get("capability_gain", {}) or {}
        ev.append(f"capability: {cap.get('capability')} | agent feasibility: {cap.get('feasibility')} — {cap.get('reason')}")
        for n in (out.get("leakage_or_hacking_notes") or [])[:5]:
            ev.append(f"leakage/hacking note: {n}")
        for n in (out.get("clarity_issues") or [])[:5]:
            ev.append(f"clarity: {n}")
        reason = f"judge: {verdict} (confidence {conf}) — {rec.get('justification', '')}"
        infeasible = str(cap.get("feasibility", "")).lower() == "infeasible"
        hard_no = any(str((out.get(k) or {}).get("verdict", "")).lower() == "no" for k in ("solvable", "verifiable"))
        if verdict == "fail" or infeasible or hard_no:
            return self.result(Status.FAIL, reason, evidence=ev, data=out)
        if verdict == "needs_review" or any(str((out.get(k) or {}).get("verdict", "")).lower() == "uncertain" for k in ("solvable", "verifiable")) \
                or dom.get("matches_declared") is False or tier.get("matches_declared") is False:
            return self.result(Status.WARN, reason, evidence=ev, data=out)
        return self.result(Status.PASS, reason, evidence=ev, data=out)
