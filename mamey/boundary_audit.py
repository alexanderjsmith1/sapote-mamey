"""mamey.boundary_audit — enforce the deterministic↔judgment contract on real data (W4/W23).

Diffs a records payload (BGCRecord side) against a verdicts payload (TriageRecord side),
both keyed by the real primary key `bgc_id`. Catches the failure classes that the
count-only completeness audit cannot:

  DROPPED   — a deterministic BGC with no verdict (the AS-XXX silent-omission class).
  ORPHAN    — a verdict for a bgc_id the extractor never produced.
  STRAIN    — the two payloads describe different strains (a copy-paste bus error, W12).
  TIER      — a verdict whose lead_tier / claim_confidence is outside the known vocabulary.
  DOWNGRADE — a verdict flagged standing-rule / primary-metabolism / mobile-element that
              STILL kept a corrected lead rank (the exclusion was recorded but not honoured).
  EXCLUSION — a record whose products trip a lead-blocking *excluded* rule
              (NAPAA / saccharide / hglE-KS) but whose verdict shows no downgrade
              (the exclusion did not fire — a retired-class claim leaking as a clean lead).
  RETIRED   — a record carrying a *retired* id (e.g. BRYO-HGT-001) at all.

Any problem -> exit 1.

RELATION TO EXISTING TOOLS (read this before assuming it's standalone)
---------------------------------------------------------------------
This is NOT the first completeness check in the bundle. It deliberately complements:
  * tools/sapote_judgment_receipt.py  — counts Mode B cards vs raw BGCs, flips
    gold_completeness. (COUNT-level completeness.)
  * tools/evidence_conservation_audit.py — catches biosynthetic evidence present in the
    raw antiSMASH output but dropped from the sealed package. (SOURCE->PACKAGE conservation.)
The genuinely new checks here are DOWNGRADE (a standing-rule/primary-metab BGC that kept a
corrected_rank) and EXCLUSION (an excluded class whose downgrade never fired) — neither of
which the receipt or the conservation auditor performs. DROPPED/ORPHAN overlap with the
receipt's count check but operate at bgc_id-correspondence granularity. Prefer wiring these
invariants INTO the existing receipt over running a fourth parallel audit.

    python3 -m mamey.boundary_audit STRAIN_records.json STRAIN_verdicts.json
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
import sys
import pathlib

try:
    from mamey.rules import load_registry, lint_text
    _HAVE_RULES = True
except Exception:  # pragma: no cover
    _HAVE_RULES = False

try:
    from mamey.scoring import standing_rule_for
    _HAVE_SCORING = True
except Exception:  # pragma: no cover
    _HAVE_SCORING = False

LEAD_TIERS = {"Exceptional", "High", "Medium", "Low", "Inventory"}  # inventory_review_01: 'Low' = specialized-but-low-scoring (class-gated bottom)
CLAIM_CONF = {"High", "Moderate-High", "Moderate", "Low-Moderate", "Low", "Unknown"}


def _admit_payloads(records, verdicts) -> list[str]:
    """P300-031: admit the payload shape before any correspondence check.

    `{}`, a missing strain, an undeclared collection or a wrongly typed one is malformed input,
    not a valid zero-BGC dataset. A declared empty list is a genuine empty roster (denominator 0).
    """
    problems: list[str] = []
    for side, payload in (("records", records), ("verdicts", verdicts)):
        if not isinstance(payload, dict):
            problems.append(f"SCHEMA {side}: payload is {type(payload).__name__}, not a JSON object")
            continue
        strain = payload.get("strain")
        if not isinstance(strain, str) or not strain.strip():
            problems.append(f"SCHEMA {side}: missing or empty strain identity ({strain!r})")
        if side not in payload:
            problems.append(f"SCHEMA {side}: {side!r} collection not declared "
                            "(absent is not an empty roster)")
            continue
        rows = payload[side]
        if not isinstance(rows, list):
            problems.append(f"SCHEMA {side}: {side!r} is {type(rows).__name__}, not a list")
            continue
        bad = [i for i, row in enumerate(rows)
               if not isinstance(row, dict) or not isinstance(row.get("bgc_id"), str)
               or not row["bgc_id"].strip()]
        if bad:
            problems.append(f"SCHEMA {side}: {len(bad)}/{len(rows)} row(s) lack an object with a "
                            f"string bgc_id (row index {bad[:12]})")
    return problems


def audit_payloads(records: dict, verdicts: dict, registry=None) -> tuple[int, list[str]]:
    problems: list[str] = []

    schema_problems = _admit_payloads(records, verdicts)
    if schema_problems:  # P300-031: malformed input is a hold, never a clean zero-BGC audit
        return 1, schema_problems

    r_strain, v_strain = records.get("strain"), verdicts.get("strain")
    if r_strain != v_strain:
        problems.append(f"STRAIN mismatch: records={r_strain!r} vs verdicts={v_strain!r}")

    _rec_list = records.get("records", [])
    recs = {r["bgc_id"]: r for r in _rec_list}
    if len(_rec_list) != len(recs):  # SCHEMA-P06: a duplicate bgc_id silently collapsed (extractor double-emit)
        from collections import Counter as _Counter
        _dups = sorted(k for k, n in _Counter(r["bgc_id"] for r in _rec_list).items() if n > 1)
        problems.append(f"DUPLICATE bgc_id in records (extractor double-emit): {_dups}")
    _verd_list = verdicts.get("verdicts", [])
    verds = {v["bgc_id"]: v for v in _verd_list}
    if len(_verd_list) != len(verds):  # P300-030: one verdict per BGC; a later row must not hide an earlier one
        _by_id: dict[str, list] = {}
        for v in _verd_list:
            _by_id.setdefault(v["bgc_id"], []).append(v)
        _multi = {k: rows for k, rows in _by_id.items() if len(rows) > 1}
        _conflicting = sorted(k for k, rows in _multi.items() if any(r != rows[0] for r in rows[1:]))
        _identical = sorted(k for k in _multi if k not in _conflicting)
        problems.append(
            f"DUPLICATE bgc_id in verdicts ({len(_verd_list)} verdict rows for {len(verds)} unique "
            f"loci; one verdict per BGC required): conflicting={_conflicting} identical={_identical}")

    dropped = sorted(set(recs) - set(verds))
    if dropped:
        problems.append(
            f"DROPPED {len(dropped)}/{len(recs)} BGC(s) have no verdict "
            f"(silent-omission / AS-XXX class): {', '.join(dropped[:12])}"
            + (" …" if len(dropped) > 12 else ""))

    orphan = sorted(set(verds) - set(recs))
    if orphan:
        problems.append(
            f"ORPHAN {len(orphan)} verdict(s) reference an unknown bgc_id: "
            f"{', '.join(orphan[:12])}" + (" …" if len(orphan) > 12 else ""))

    for uid, v in verds.items():
        if v.get("lead_tier") not in LEAD_TIERS:
            problems.append(f"TIER {uid}: lead_tier {v.get('lead_tier')!r} not in {sorted(LEAD_TIERS)}")
        if v.get("claim_confidence") not in CLAIM_CONF:
            problems.append(f"TIER {uid}: claim_confidence {v.get('claim_confidence')!r} not in {sorted(CLAIM_CONF)}")
        # v9.7.374: mobile_element_flag is a THIRD corrected_rank-gating flag in scoring.py
        # (`if not r.standing_rule_flag and not r.primary_metabolism_flag and not
        # r.mobile_element_flag: r.corrected_rank = rank`, scoring.py:686) — a verdict with
        # mobile_element_flag set must never carry a corrected_rank either. This check used to
        # test only the first two flags, so a mobile-element-downgraded verdict that still kept
        # a corrected_rank (scoring regression, or hand/LLM-edited verdict JSON) passed silently.
        downgraded = (bool(v.get("standing_rule_flag")) or bool(v.get("primary_metabolism_flag"))
                      or bool(v.get("mobile_element_flag")))
        if downgraded and v.get("corrected_rank") is not None:
            problems.append(
                f"DOWNGRADE {uid}: flagged "
                f"({v.get('standing_rule_flag') or v.get('mobile_element_flag') or 'primary-metab'}) "
                f"but kept corrected_rank={v.get('corrected_rank')} (exclusion not honoured)")

    if _HAVE_RULES:
        reg = registry or load_registry()
        for uid, r in recs.items():
            own_products = " ".join(r.get("products", []) or [])
            blob = " ".join([own_products,
                             str(r.get("kcb_top") or ""),
                             " ".join(r.get("mibig_hits", []) or [])])
            v = verds.get(uid, {})
            downgraded = (bool(v.get("standing_rule_flag")) or bool(v.get("primary_metabolism_flag"))
                          or bool(v.get("mobile_element_flag")))
            # Committed-class guard (mirrors scoring.standing_rule_for): an EXCLUSION miss is only a real
            # problem when a standing rule would actually fire on the BGC's OWN products. A committed
            # NRPS/PKS/RiPP that merely carries a saccharide tailoring arm returns "" from
            # standing_rule_for, so its no-downgrade verdict is CORRECT — not an exclusion miss. Without
            # this, boundary_audit over-flags every multi-class saccharide-tailored lead. Fail-open: if
            # scoring is unavailable, retain the prior (coarse) behaviour.
            rule_should_fire = bool(standing_rule_for(own_products, blob)) if _HAVE_SCORING else True
            for h in lint_text(blob, reg):
                if h.status == "retired":
                    problems.append(f"RETIRED {uid}: carries retired id '{h.matched}' ({h.rule_id})")
                elif h.status == "excluded" and h.lead_blocking and not downgraded and rule_should_fire:
                    problems.append(
                        f"EXCLUSION {uid}: products match excluded rule {h.rule_id} "
                        f"('{h.matched}') but verdict shows no downgrade (exclusion did not fire)")
    else:
        # SCHEMA-P05: mamey.rules failed to import -> the retired/exclusion leak checks were SKIPPED.
        # Surface that as a problem so a broken rules module can't masquerade as a clean audit.
        problems.append("RULES_UNAVAILABLE: mamey.rules import failed — retired/exclusion leak "
                        "checks did NOT run; this audit is INCOMPLETE, not clean")

    return (1 if problems else 0), problems


def audit_files(records_path: str, verdicts_path: str) -> tuple[int, list[str]]:
    r = json.loads(pathlib.Path(records_path).read_text(encoding="utf-8"))
    v = json.loads(pathlib.Path(verdicts_path).read_text(encoding="utf-8"))
    return audit_payloads(r, v)


def _main(argv: list[str]) -> int:
    if len(argv) != 3:
        emit(__doc__)
        return 2
    rc, problems = audit_files(argv[1], argv[2])
    if problems:
        emit("BOUNDARY AUDIT FAILED:")
        for p in problems:
            emit("  " + p)
    else:
        emit("boundary audit OK — every BGC has one non-orphan verdict; "
              "downgrades honoured; no retired/excluded leaks")
    return rc


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
