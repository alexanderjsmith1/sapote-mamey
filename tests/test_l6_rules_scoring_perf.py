"""L6 companion tests — rules/scoring/perf hardening staged for the next cut.

Covers the four L6 fixes:
  RG-01  NAPAA fallback branch removed from scoring.py (VERDICT-CHANGING) — an
         own-product NAPAA BGC is no longer floored to Inventory / excluded from
         the corrected lead order; NAPAA is driven only through standing_rule_for,
         which honours the registry SSOT (status=neutral / action=none).
  RG-03  the inert SACCHARIDE false_positive_guard was removed; the \\bsaccharide\\b
         word boundary is what actually protects polysaccharide/lipopolysaccharide/
         aminoglycoside.
  RG-04  rules.load_registry now validates status/action against the allowed enum
         sets (a typo raises instead of silently dropping the rule); the exact set
         of lead-blocking downgrade rules is pinned.
  PERF-05 source_scans precompiles marker patterns once (cached) instead of calling
         re.search on uncompiled strings per CDS x marker; output stays byte-identical.

Standalone: python3 tests/test_l6_rules_scoring_perf.py
"""
from __future__ import annotations
import json
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import mamey.rules as R
from mamey.models import BGCRecord
from mamey.scoring import triage_bgcs, standing_rule_for, _downgrade_rules


def _scans(cctt=None):
    return SimpleNamespace(
        primary_metabolism={"per_bgc": {}},
        cctt={"per_bgc": cctt or {}, "context_uncorroborated_by_bgc": {}},
        resistance_tiers={"per_bgc": {}},
    )


# ── RG-01 — own-product NAPAA is no longer floored / excluded (VERDICT-CHANGING) ──

def test_rg01_own_product_napaa_not_floored_to_inventory():
    """A NAPAA-own-product BGC whose diagnostic evidence floors it to Medium must
    KEEP Medium. Pre-fix the hardcoded NAPAA-exclusion overrode it back to Inventory
    and dropped it from the corrected lead order."""
    bgc = BGCRecord(
        bgc_id="BGC099", contig="c1", region_number=1, start=1, end=40000,
        contig_length=200000, products=["NAPAA", "nucleoside"],
        edge_status="Interior", architecture_confidence="A", kcb_cumulative=90000,
    )
    # a corroborated CCTT AF-diagnostic trigger floors the natural tier to Medium
    r = triage_bgcs([bgc], None, _scans(cctt={"BGC099": ["T43-NUC"]}))[0]
    assert r.lead_tier == "Medium", f"NAPAA floored back to {r.lead_tier}"
    assert "NAPAA" not in r.standing_rule_flag
    assert r.corrected_rank is not None, "NAPAA wrongly excluded from corrected lead order"


def test_rg01_plain_own_product_napaa_has_no_standing_rule_flag():
    bgc = BGCRecord(
        bgc_id="BGC100", contig="c1", region_number=1, start=1, end=9000,
        contig_length=20000, products=["NAPAA"], edge_status="Interior",
        architecture_confidence="A", kcb_cumulative=90000,
    )
    r = triage_bgcs([bgc], None, _scans())[0]
    assert r.standing_rule_flag == ""            # no NAPAA-exclusion fires
    assert r.corrected_rank is not None          # stays in the corrected lead order


def test_rg01_standing_rule_for_napaa_returns_empty():
    assert standing_rule_for("napaa", "napaa") == ""


def test_rg01_hgle_ks_own_product_still_downgraded():
    """The sibling hglE-KS branch is intentionally retained — deleting NAPAA must not
    disturb it."""
    assert standing_rule_for("saccharide", "saccharide") == "saccharide-exclusion"
    bgc = BGCRecord(
        bgc_id="BGC013", contig="NODE_43", region_number=1, start=1, end=40000,
        contig_length=80000, products=["hglE-KS"], edge_status="Interior",
        architecture_confidence="A", kcb_top="hglE-KS PREV-001 glycolipid",
    )
    r = triage_bgcs([bgc], None, _scans())[0]
    assert "hgle" in r.standing_rule_flag.lower()


# ── RG-03 — word boundary, not a guard list, protects the saccharide superstrings ──

def test_rg03_saccharide_rule_has_no_guard_list():
    reg = R.load_registry()
    sacc = next(r for r in reg if r.id == "SACCHARIDE")
    assert sacc.false_positive_guard == (), "the inert guard list should be gone"


@pytest.mark.parametrize("text", ["polysaccharide", "lipopolysaccharide", "aminoglycoside"])
def test_rg03_word_boundary_protects_superstrings(text):
    # the \bsaccharide\b boundary alone must keep these from firing SACCHARIDE
    hits = [h for h in R.lint_text(f"a {text} biosynthesis region") if h.rule_id == "SACCHARIDE"]
    assert hits == [], f"{text} wrongly flagged as saccharide"
    assert standing_rule_for(text, text) == ""


def test_rg03_bare_saccharide_still_fires():
    assert R.has_blocking_hit("BGC11 saccharide cluster")
    assert standing_rule_for("saccharide", "saccharide") == "saccharide-exclusion"


# ── RG-04 — enum validation + pinned lead-blocking downgrade-rule id set ──

def test_rg04_lead_blocking_downgrade_rule_ids_are_exactly_pinned():
    ids = {r.id for r in _downgrade_rules()}
    assert ids == {"SACCHARIDE", "NI-SIDEROPHORE", "NRP-METALLOPHORE"}


def test_rg04_live_registry_loads_clean():
    # the shipped registry uses the live values neutral/noted/none — must load
    reg = R.load_registry()
    assert {r.status for r in reg} <= R._ALLOWED_STATUS
    assert {r.action for r in reg} <= R._ALLOWED_ACTION


def _write_registry(tmp_path, status="excluded", action="downgrade"):
    payload = {
        "schema_version": "1.0",
        "rules": [{
            "id": "X", "label": "x", "status": status, "action": action,
            "scope": "s", "rationale": "r", "date": "2026-07", "lead_blocking": True,
            "patterns": ["\\bx\\b"],
        }],
    }
    p = tmp_path / "reg.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_rg04_unknown_action_raises(tmp_path):
    p = _write_registry(tmp_path, action="downgrde")   # typo
    with pytest.raises(ValueError):
        R.load_registry(p)


def test_rg04_unknown_status_raises(tmp_path):
    p = _write_registry(tmp_path, status="excldued")   # typo
    with pytest.raises(ValueError):
        R.load_registry(p)


def test_rg04_live_enum_values_are_allowed(tmp_path):
    # neutral/noted/none are real live values and must NOT raise
    for status, action in [("neutral", "none"), ("noted", "flag")]:
        R.load_registry(_write_registry(tmp_path, status=status, action=action))


# ── PERF-05 — precompiled marker patterns, byte-identical scan output ──

def test_perf05_compiled_pattern_cache_is_reused():
    import mamey.source_scans as ss
    patterns = {"g1": [r"chitinase", r"\bglx\b"], "g2": [r"transport"]}
    a = ss._compiled_patterns(patterns)
    b = ss._compiled_patterns(patterns)
    assert a is b, "compiled patterns should be cached by dict identity"
    assert all(isinstance(p, re.Pattern) for pats in a.values() for p in pats)


def test_perf05_scan_output_matches_naive_implementation():
    import mamey.source_scans as ss
    from mamey.models import CDSFeature

    cds_list = [
        CDSFeature("c1", 10, 500, 1, "L1", "chitinase family 18", None, {}),
        CDSFeature("c1", 600, 900, 1, "L2", "ABC transporter permease", None, {}),
        CDSFeature("c1", 1000, 1400, -1, "L3", "hypothetical protein", None, {}),
        CDSFeature("c2", 50, 400, 1, "L4", "CHITINASE-like glycoside hydrolase", None, {}),
    ]
    patterns = {"chitinase": [r"chitinase"], "transport": [r"transport", r"permease"]}

    got = ss._scan_patterns(cds_list, patterns)

    # naive reference (uncompiled re.search, the pre-fix behaviour)
    buckets = {k: [] for k in patterns}
    for cds in cds_list:
        h = ss._hay(cds)
        for group, pats in patterns.items():
            if any(re.search(p, h, flags=re.I) for p in pats):
                buckets[group].append({"contig": cds.contig, "start": cds.start, "end": cds.end,
                                       "strand": cds.strand, "locus_tag": cds.locus_tag, "product": cds.product})
    expected = {"status": "SOURCE_DERIVED", "counts": {k: len(v) for k, v in buckets.items()},
                "hits": buckets,
                "claim_safety": "Annotation/keyword-derived first pass; confirm with HMMER/BLAST before manuscript use."}
    assert got == expected


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            # skip fixtures/parametrized in bare mode
            import inspect
            params = inspect.signature(fn).parameters
            if params:
                print(f"SKIP {fn.__name__} (needs pytest fixture/param)")
                continue
            fn(); passed += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{passed} bare tests passed")
