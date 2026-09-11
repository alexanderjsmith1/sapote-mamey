"""mamey.rules — load the standing-rules registry and lint verdict text against it.

WHY THIS EXISTS (W8/W30)
------------------------
Retirements and exclusions ("NAPAA is excluded", "BRYO-HGT-001 is retired") used to
live only in a preferences doc and in memory. A fresh chat session with thin context
could re-surface a claim you killed months ago, and nothing would catch it. This module
moves those rules into the code and gives you a linter that flags them — so a retired
claim re-entering a verdict fails a check instead of slipping into a result.

The registry data lives in mamey/data/rules_registry.json (the single source of truth).
This module only loads and applies it.

USAGE
-----
    from mamey.rules import load_registry, lint_text

    hits = lint_text("BGC04 looks like a strong NAPAA lead")
    for h in hits:
        print(h.rule_id, h.status, h.matched)   # -> NAPAA excluded NAPAA

    # CLI: scan a file or stdin, exit 1 on any lead-blocking hit
    python3 -m mamey.rules path/to/verdict.md
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import json
import re
import sys
import pathlib
from dataclasses import dataclass
from typing import Iterable

_REGISTRY_PATH = pathlib.Path(__file__).resolve().parent / "data" / "rules_registry.json"

# RG-04: `status`/`action` are documented enums but were never validated at load,
# so a typo (e.g. action:"downgrde") silently dropped a rule from _downgrade_rules()
# instead of failing loudly. These are the allowed sets — the four originally
# documented values for each, plus the live values actually in use in the shipped
# registry (status neutral/noted; action none). Extend these sets when a genuinely
# new status/action is introduced.
_ALLOWED_STATUS = frozenset({"active", "retired", "excluded", "gate", "neutral", "noted"})
_ALLOWED_ACTION = frozenset({"downgrade", "drop", "flag", "exclude", "none"})


@dataclass(frozen=True)
class Rule:
    id: str
    label: str
    status: str          # active | retired | excluded | gate | neutral | noted
    action: str          # downgrade | drop | flag | exclude | none
    scope: str
    rationale: str
    date: str
    lead_blocking: bool
    patterns: tuple
    false_positive_guard: tuple = ()
    reason_code: str = ""
    evidence_distinctions: tuple = ()


@dataclass(frozen=True)
class Hit:
    rule_id: str
    label: str
    status: str
    action: str
    lead_blocking: bool
    matched: str         # the exact substring that triggered
    context: str         # a little surrounding text, for the human


def load_registry(path: pathlib.Path | None = None) -> list[Rule]:
    """Load and validate the rules registry. Raises on a malformed file so a typo
    in the registry can't silently disable a rule."""
    p = path or _REGISTRY_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    rules = []
    seen = set()
    for r in data["rules"]:
        rid = r["id"]
        if rid in seen:
            raise ValueError(f"duplicate rule id in registry: {rid}")
        seen.add(rid)
        # RG-04: validate the enums so a typo raises here rather than silently
        # dropping the rule from downstream filters (e.g. _downgrade_rules()).
        status = r["status"]
        if status not in _ALLOWED_STATUS:
            raise ValueError(
                f"rule {rid}: unknown status {status!r} "
                f"(allowed: {sorted(_ALLOWED_STATUS)})")
        action = r["action"]
        if action not in _ALLOWED_ACTION:
            raise ValueError(
                f"rule {rid}: unknown action {action!r} "
                f"(allowed: {sorted(_ALLOWED_ACTION)})")
        rules.append(Rule(
            id=rid,
            label=r["label"],
            status=r["status"],
            action=r["action"],
            scope=r["scope"],
            rationale=r["rationale"],
            date=r["date"],
            lead_blocking=bool(r.get("lead_blocking", False)),
            patterns=tuple(re.compile(pat, re.IGNORECASE) for pat in r["patterns"]),
            false_positive_guard=tuple(g.lower() for g in r.get("false_positive_guard", [])),
            reason_code=str(r.get("reason_code", "")),
            evidence_distinctions=tuple(str(v) for v in r.get("evidence_distinctions", [])),
        ))
    return rules


def load_inventory_tier_policy(path: pathlib.Path | None = None) -> dict:
    """Load and validate the governed AQUARIUS_01 bottom-tier routing policy.

    The policy is kept beside standing rules so the scorer, audit, renderers, and
    documentation can share one class list and one normalization contract.  The
    returned mapping is a defensive copy of validated JSON data.
    """
    p = path or _REGISTRY_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    try:
        policy = dict(data["routing_policies"]["inventory_bottom_tier"])
    except (KeyError, TypeError) as exc:
        raise ValueError("missing routing_policies.inventory_bottom_tier") from exc
    required = {
        "id", "schema_version", "status", "decision_date", "decision_owner",
        "scope", "core_housekeeping_classes", "housekeeping_classes",
        "neutral_tokens", "substring_aliases", "ambiguous_review_tokens",
        "route_labels", "claim_ceiling", "review_rule",
    }
    missing = sorted(required - set(policy))
    if missing:
        raise ValueError(f"inventory_bottom_tier missing fields: {missing}")
    if policy["status"] != "active":
        raise ValueError("inventory_bottom_tier policy must be active")
    core = [str(v).strip().lower() for v in policy["core_housekeeping_classes"]]
    all_classes = [str(v).strip().lower() for v in policy["housekeeping_classes"]]
    if not core or not all_classes or len(all_classes) != len(set(all_classes)):
        raise ValueError("inventory_bottom_tier class lists must be non-empty and unique")
    if not set(core) <= set(all_classes):
        raise ValueError("core_housekeeping_classes must be a subset of housekeeping_classes")
    aliases = policy["substring_aliases"]
    if not isinstance(aliases, list) or not aliases:
        raise ValueError("inventory_bottom_tier substring_aliases must be a non-empty list")
    for alias in aliases:
        if set(alias) != {"contains", "canonical"}:
            raise ValueError(f"malformed inventory-bottom-tier alias: {alias!r}")
        if str(alias["canonical"]).lower() not in set(all_classes):
            raise ValueError(f"alias canonical class is not allow-listed: {alias!r}")
    labels = policy["route_labels"]
    expected_labels = {
        "specialized_below_medium": "Low",
        "allow_listed_below_medium": "Inventory",
        "unresolved_below_medium": "Inventory",
    }
    if labels != expected_labels:
        raise ValueError(f"unexpected inventory-bottom-tier route labels: {labels!r}")
    policy["core_housekeeping_classes"] = core
    policy["housekeeping_classes"] = all_classes
    policy["neutral_tokens"] = [str(v).strip().lower() for v in policy["neutral_tokens"]]
    policy["ambiguous_review_tokens"] = [
        str(v).strip().lower() for v in policy["ambiguous_review_tokens"]
    ]
    policy["substring_aliases"] = [
        {"contains": str(v["contains"]).strip().lower(),
         "canonical": str(v["canonical"]).strip().lower()}
        for v in aliases
    ]
    return policy


def _guarded(matched_span: str, full_text: str, start: int, guards: Iterable[str]) -> bool:
    """True if the match is actually part of a guarded longer word (e.g. 'saccharide'
    inside 'polysaccharide'). Cheap check: does any guard token, lowercased, contain
    the matched token and appear in the text around this position?"""
    low = full_text.lower()
    for g in guards:
        # find guard occurrences and see if our match index falls inside one
        idx = low.find(g)
        while idx != -1:
            if idx <= start < idx + len(g):
                return True
            idx = low.find(g, idx + 1)
    return False


def lint_text(text: str, registry: list[Rule] | None = None) -> list[Hit]:
    """Return every registry hit in `text`. Each hit names the rule, its status,
    and whether it is lead-blocking. Gates (e.g. enediyne) are reported too, so a
    caller can attach the [E-signal] claim note (no BSL-2 lab-safety flag is emitted)."""
    reg = registry or load_registry()
    hits: list[Hit] = []
    for rule in reg:
        for pat in rule.patterns:
            for m in pat.finditer(text):
                if rule.false_positive_guard and _guarded(
                    m.group(0), text, m.start(), rule.false_positive_guard
                ):
                    continue
                lo = max(0, m.start() - 30)
                hi = min(len(text), m.end() + 30)
                hits.append(Hit(
                    rule_id=rule.id,
                    label=rule.label,
                    status=rule.status,
                    action=rule.action,
                    lead_blocking=rule.lead_blocking,
                    matched=m.group(0),
                    context="…" + text[lo:hi].replace("\n", " ") + "…",
                ))
    return hits


def has_blocking_hit(text: str, registry: list[Rule] | None = None) -> bool:
    return any(h.lead_blocking for h in lint_text(text, registry))


def _main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        emit("usage: python -m mamey.rules [FILE]\n"
              "  Lint text for retired/excluded claims (NAPAA, saccharide, hglE-KS, BRYO-HGT-001).\n"
              "  FILE: path to scan; if omitted, reads stdin.\n"
              "  Exit 1 if any lead-blocking claim is found, else 0.")
        return 0
    if len(argv) < 2:
        text = sys.stdin.read()
    else:
        text = pathlib.Path(argv[1]).read_text(encoding="utf-8")
    hits = lint_text(text)
    blocking = [h for h in hits if h.lead_blocking]
    for h in hits:
        flag = "BLOCK" if h.lead_blocking else "warn "
        emit(f"[{flag}] {h.rule_id} ({h.status}/{h.action}): {h.matched}  {h.context}")
    if not hits:
        emit("rules lint OK — no retired/excluded claims found")
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
