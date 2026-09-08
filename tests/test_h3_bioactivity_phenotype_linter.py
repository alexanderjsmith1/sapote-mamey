"""H3: claim_safety_linter must flag per-BGC bioactivity-PHENOTYPE overclaims.

"Bioactivity is extract-level only — never a per-BGC phenotype claim." Before the fix the
linter only had the compound-scoped identity checks (_PRODUCTION_RE / _COPULA_RE), so a card
saying "BGC059 shows potent antibacterial activity against MRSA ... is a confirmed producer"
returned clean. The new `bioactivity_phenotype` WARN closes that (not compound-scoped;
hedge/negation/capacity/extract-level exempt).
"""
import importlib.util, pathlib

_root = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "claim_safety_linter", _root / "tools" / "claim_safety_linter.py")
csl = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(csl)


def _flags(text):
    rows = csl.lint_claim_safety_report(text, card_id="BGC059", section="§5")
    return {r["violation_type"] for r in rows}


def test_flags_per_bgc_activity_and_producer():
    assert "bioactivity_phenotype" in _flags(
        "BGC059 shows potent antibacterial activity against MRSA and is a confirmed producer.")


def test_flags_inhibits_and_kills():
    assert "bioactivity_phenotype" in _flags("BGC012 inhibits cell wall synthesis in Candida.")
    assert "bioactivity_phenotype" in _flags("This cluster kills Gram-positive pathogens.")


def test_extract_level_is_allowed():
    # extract-level bioactivity is permitted -> must NOT flag
    assert "bioactivity_phenotype" not in _flags(
        "The crude extract shows antibacterial activity against MRSA.")


def test_negated_is_exempt():
    assert "bioactivity_phenotype" not in _flags("This locus does not show antibacterial activity.")


def test_capacity_and_hedged_are_exempt():
    assert "bioactivity_phenotype" not in _flags(
        "Capacity consistent with a bioactive-target hypothesis; not a phenotype.")
    assert "bioactivity_phenotype" not in _flags(
        "BGC012 may have antifungal potential pending experimental assays.")


def test_warn_severity_band():
    rows = csl.lint_claim_safety_report(
        "BGC059 is active against MRSA.", card_id="BGC059", section="§5")
    bio = [r for r in rows if r["violation_type"] == "bioactivity_phenotype"]
    assert bio and all(r["severity"] == "WARN" for r in bio)
