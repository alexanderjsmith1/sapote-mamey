"""v9.7.218: EBI alignments-enum fix (owned bug) + cnames slash-split (Diff A) regression."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

def test_ebi_alignments_snaps_to_valid_enum():
    from mamey.blastp_ebi import _snap_alignments, _EBI_ALIGN_ENUM
    assert _snap_alignments(6) == "10"   # 6 is NOT a valid EBI enum (caused HTTP 400 in v215-217)
    assert _snap_alignments(5) == "5"
    assert _snap_alignments(30) == "50"
    assert int(_snap_alignments(6)) in _EBI_ALIGN_ENUM

def test_cnames_slash_split_flags_base_compound():
    from claim_safety_linter import lint_claim_safety_report as lint
    hit = lambda t, cn: [r for r in lint(t, compound_names=cn) if r["violation_type"] == "identity_overclaim"]
    # base name derivable -> overclaim flags
    assert hit("This cluster synthesizes bombyxamycin.", {"bombyxamycin"})
    # negation still passes (guard from .217 intact)
    assert not hit("does not support that BGC041 produces bombyxamycin", {"bombyxamycin"})
