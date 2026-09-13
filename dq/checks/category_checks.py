"""Categorisation checks: declared domain and tier are valid; keyword-inferred domain agrees (softly)."""
from __future__ import annotations

import re

from ..model import Severity
from .base import Check, cfg_get, register


def declared_domain(b) -> str | None:
    for src in (b.toml.get("metadata", {}) if b.toml and isinstance(b.toml.get("metadata"), dict) else {}, b.yaml or {}):
        for k in ("domain", "field", "subdomain", "category"):
            if src.get(k):
                return str(src.get(k))
    # Terminal-Bench-Science style: domain folder above the task
    parent = b.root.parent.name
    if parent.endswith("-sciences") or parent in ("mathematical-sciences", "engineering-sciences"):
        return parent
    return None


def declared_tier(b) -> str | None:
    for src in (b.toml.get("metadata", {}) if b.toml and isinstance(b.toml.get("metadata"), dict) else {}, b.yaml or {}):
        t = src.get("tier")
        if t:
            return str(t)
    return None


def normalise_domain(value: str, taxonomy: dict) -> str | None:
    v = re.sub(r"[-_/]+", " ", value.lower()).strip()
    best, best_hits = None, 0
    for dom, aliases in taxonomy.items():
        if v == re.sub(r"[-_/]+", " ", dom):
            return dom
        hits = sum(1 for a in aliases if re.search(r"(?<![a-z])" + re.escape(re.sub(r"[-_/]+", " ", a.lower())) + r"(?![a-z])", v))
        if hits > best_hits:
            best, best_hits = dom, hits
    return best


def infer_domain(text: str, keywords: dict) -> list[tuple[str, int]]:
    low = text.lower()
    scores = []
    for dom, kws in keywords.items():
        s = sum(len(re.findall(r"\b" + re.escape(k.lower()) + r"\b", low)) for k in kws)
        scores.append((dom, s))
    return sorted(scores, key=lambda x: -x[1])


@register
class DomainDeclaredValid(Check):
    id = "category.domain_declared_valid"
    name = "Declared domain maps onto the taxonomy"
    category = "category"
    default_severity = Severity.WARN

    def run(self, b, cfg):
        taxonomy = cfg_get(cfg, "taxonomy.domains", {})
        d = declared_domain(b)
        if not d:
            return self.warn("no domain declared in [metadata] or task.yaml (and no domain folder)")
        dom = normalise_domain(d, taxonomy)
        if not dom:
            return self.warn(f"declared domain '{d}' does not map onto the taxonomy {list(taxonomy)}", data={"declared": d})
        return self.ok(f"'{d}' -> {dom}", data={"declared": d, "domain": dom})


@register
class TierDeclaredValid(Check):
    id = "category.tier_declared_valid"
    name = "Declared tier is one of the benchmark's tiers"
    category = "category"
    default_severity = Severity.INFO

    def run(self, b, cfg):
        tiers = cfg_get(cfg, "taxonomy.tiers", {})
        t = declared_tier(b)
        if not t:
            return self.info(f"no tier declared (expected one of {list(tiers)}); the LLM judge will propose one if enabled")
        if t not in tiers:
            return self.warn(f"tier '{t}' is not one of {list(tiers)}")
        return self.ok(f"tier {t}: {tiers[t]}")


@register
class DomainKeywordConsistency(Check):
    id = "category.domain_keyword_consistency"
    name = "Instruction vocabulary agrees with the declared domain"
    category = "category"
    default_severity = Severity.INFO

    def run(self, b, cfg):
        taxonomy = cfg_get(cfg, "taxonomy.domains", {})
        keywords = cfg_get(cfg, "taxonomy.domain_keywords", {})
        d = declared_domain(b)
        dom = normalise_domain(d, taxonomy) if d else None
        scores = infer_domain(b.instruction + "\n" + b.readme, keywords)
        top = [f"{k}:{s}" for k, s in scores[:3] if s]
        if not scores or scores[0][1] == 0:
            return self.info("no domain keywords matched; rely on the LLM judge / reviewer", data={"scores": scores[:3]})
        if dom and scores[0][0] != dom and scores[0][1] >= 2 * max(1, dict(scores).get(dom, 0)):
            return self.warn(f"declared {dom} but the text reads as {scores[0][0]} (keyword scores {top})", data={"scores": scores[:3]})
        return self.ok(f"top keyword domains {top}" + (f"; declared {dom}" if dom else ""), data={"scores": scores[:3]})


@register
class TierHeuristics(Check):
    id = "category.tier_heuristics"
    name = "Tier hints in the task match the declared tier"
    category = "category"
    default_severity = Severity.INFO
    description = "T1 expects a generator (regenerable instances); T2 an expert reference on real data; T3 an open method-building problem."

    def run(self, b, cfg):
        t = declared_tier(b)
        text = (b.instruction + "\n" + b.readme).lower()
        has_generator = any(f.startswith("generator/") for f in b.files) or "seed" in text and "regenerat" in text
        expert_ref = bool(re.search(r"expert|lab's|reference (map|pipeline|solution)|ground truth|hand-?drawn|as processed by", text))
        open_ended = bool(re.search(r"no systematic method|open-ended|research how|design a method|beat the|improve (on|upon)|discover|replace the by-hand|by hand|manual(ly)? |systematic,? (automatic )?(method|pipeline|procedure|way)|without human intervention", text))
        hints = [h for h, v in (("generator", has_generator), ("expert reference", expert_ref), ("open-ended", open_ended)) if v]
        if not t:
            return self.info(f"no tier declared; hints found: {hints or 'none'}")
        if t == "T1" and not has_generator:
            return self.warn("declared T1 (controlled generator) but no generator/ directory or seed-regeneration language found")
        if t == "T3" and not open_ended:
            return self.info("declared T3 (open-ended discovery) but the text does not read as open-ended; reviewer to confirm")
        return self.ok(f"tier {t}; hints: {hints or 'none'}")
