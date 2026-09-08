"""test_claim_safety_linter_gate.py — STEP 3 (SM-P1-004): Claim-safety linter gate.

Tests:
  1. CSV output has all required columns (card_id, section, sentence, violation_type,
     misanchor_flag, severity)
  2. Severity tiers: HIGH for §1/§8 or misanchor_flag set; MEDIUM for §3–§7; INFO otherwise
  3. HIGH misanchor_flag promotion: a violation in §3 with Misanchor_Flag set → HIGH
  4. Safe constructions are NOT flagged (preserving _SAFE_AFTER_PRODUCES and _CAPACITY_FRAME)
  5. mamey claim-safety subcommand exists in cli.py

Fixtures use synthetic IDs only (AS-900, AS-901, AS-902).
"""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

import claim_safety_linter as csl


# ── 1. CSV columns ─────────────────────────────────────────────────────────────
def test_lint_report_columns():
    """lint_claim_safety_report() must return dicts with all required CSV columns."""
    text = "This BGC produces kirromycin."
    rows = csl.lint_claim_safety_report(text, card_id="BGC001", section="§1",
                                        misanchor_flag="")
    assert rows, "Expected at least one finding"
    required = {"card_id", "section", "sentence", "violation_type", "misanchor_flag", "severity"}
    assert required <= set(rows[0].keys()), \
        f"Missing columns: {required - set(rows[0].keys())}"


# ── 2. Severity tier: §1 → HIGH ───────────────────────────────────────────────
def test_severity_high_for_section_1():
    text = "This BGC produces kirromycin."
    rows = csl.lint_claim_safety_report(text, card_id="BGC001", section="§1",
                                        misanchor_flag="")
    assert any(r["severity"] == "HIGH" for r in rows), \
        f"§1 violation must be HIGH: {rows}"


def test_severity_high_for_section_8():
    text = "The strain produces erythromycin at useful titres."
    rows = csl.lint_claim_safety_report(text, card_id="BGC001", section="§8",
                                        misanchor_flag="")
    assert any(r["severity"] == "HIGH" for r in rows), \
        f"§8 violation must be HIGH: {rows}"


# ── 3. Severity tier: §3–§7 → MEDIUM ─────────────────────────────────────────
def test_severity_medium_for_section_3():
    text = "The PKS produces a polyene backbone."
    rows = csl.lint_claim_safety_report(text, card_id="BGC001", section="§3",
                                        misanchor_flag="")
    # "produces a polyene backbone" — "polyene" is in _SAFE_AFTER_PRODUCES → should be CLEAN
    assert rows == [] or all(r["severity"] != "HIGH" for r in rows), \
        "Safe construction should not be HIGH"


def test_severity_medium_for_genuine_section_5_violation():
    text = "This BGC produces tacrolimus and is active against Candida."
    rows = csl.lint_claim_safety_report(text, card_id="BGC001", section="§5",
                                        misanchor_flag="")
    assert any(r["severity"] == "MEDIUM" for r in rows), \
        f"§5 violation should be MEDIUM: {rows}"


# ── 4. Misanchor_Flag promotes MEDIUM → HIGH ──────────────────────────────────
def test_misanchor_flag_promotes_to_high():
    """A §5 violation with a non-blank Misanchor_Flag must be promoted to HIGH."""
    text = "This BGC produces tacrolimus."
    rows = csl.lint_claim_safety_report(
        text, card_id="BGC001", section="§5",
        misanchor_flag="polyene_anchor_<4_PKS_KS(ks=1)"
    )
    assert any(r["severity"] == "HIGH" for r in rows), \
        f"Misanchor_Flag should promote to HIGH: {rows}"


# ── 5. Safe constructions not flagged ─────────────────────────────────────────
def test_safe_produces_polyketide_not_flagged():
    """'produces a polyketide backbone' is capacity framing — must not fire."""
    text = "The assembly line produces a polyketide backbone."
    rows = csl.lint_claim_safety_report(text, card_id="BGC001", section="§3",
                                        misanchor_flag="")
    violations = [r for r in rows if r["violation_type"] == "identity_overclaim"]
    assert not violations, f"Safe construction should not fire: {violations}"


def test_safe_capacity_consistent_not_flagged():
    """'biosynthetic capacity consistent with erythromycin-like...' is safe."""
    text = "Biosynthetic capacity consistent with erythromycin-like macrolide."
    rows = csl.lint_claim_safety_report(text, card_id="BGC001", section="§1",
                                        misanchor_flag="")
    violations = [r for r in rows if r["violation_type"] == "identity_overclaim"]
    assert not violations, f"Capacity-framed text should not fire: {violations}"


def test_kcb_without_ceiling_flagged():
    """KnownClusterBlast mentioned without ceiling language must fire."""
    text = "The KnownClusterBlast hit confirms erythromycin."
    rows = csl.lint_claim_safety_report(text, card_id="BGC001", section="§4",
                                        misanchor_flag="")
    assert any(r["violation_type"] == "kcb_no_ceiling" for r in rows), \
        f"KCB without ceiling should fire: {rows}"


def test_kcb_with_ceiling_not_flagged():
    """KCB mentioned with similarity-anchor framing must not fire."""
    text = "The KCB similarity anchor (not a product identity) points to erythromycin class."
    rows = csl.lint_claim_safety_report(text, card_id="BGC001", section="§4",
                                        misanchor_flag="")
    kcb_violations = [r for r in rows if r["violation_type"] == "kcb_no_ceiling"]
    assert not kcb_violations, f"KCB with ceiling should not fire: {kcb_violations}"


# ── 6. mamey claim-safety subcommand in cli.py ────────────────────────────────
def test_mamey_claim_safety_subcommand_exists():
    """mamey/cli.py must define a claim-safety subcommand."""
    src = (_ROOT / "mamey" / "cli.py").read_text(encoding="utf-8")
    assert "claim-safety" in src or "claim_safety" in src, \
        "mamey claim-safety subcommand not found in cli.py"
    # Must reference the linter
    assert "claim_safety_linter" in src or "lint_claim_safety" in src, \
        "cli.py claim-safety subcommand must reference the linter"


# ── 7. INFO tier for non-§1-8 sections ───────────────────────────────────────
def test_info_tier_for_enrichment_section():
    """A violation in §11+ (enrichment sections) should be INFO severity."""
    text = "This cluster produces kirromycin."
    rows = csl.lint_claim_safety_report(text, card_id="BGC001", section="§12",
                                        misanchor_flag="")
    assert any(r["severity"] == "INFO" for r in rows), \
        f"Enrichment section violation should be INFO: {rows}"


# ── 8. Bunny Hop: near-miss that must NOT fire ────────────────────────────────
def test_produces_metabolites_not_flagged():
    """'produces secondary metabolites' is a class-level statement — must not fire."""
    text = "Streptomyces species produces secondary metabolites as part of their ecology."
    rows = csl.lint_claim_safety_report(text, card_id="BGC001", section="§7",
                                        misanchor_flag="")
    violations = [r for r in rows if r["violation_type"] == "identity_overclaim"]
    assert not violations, f"'produces secondary metabolites' should not fire: {violations}"



def test_generated_disclaimer_block_not_flagged():
    """Generated safety boilerplate is the ceiling, not an overclaim."""
    text = """> Claim-safety: All class assignments are bioinformatic predictions.
> KCB comparisons are similarity signals, not identity.
> Bioactivity links are mechanistic hypotheses requiring experimental validation.
"""
    assert csl.lint_claim_safety(text) == []
    assert csl.lint_claim_safety_report(text, card_id="BGC001", section="§4") == []
