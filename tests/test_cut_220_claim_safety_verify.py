"""v9.7.220: verify-modeb now runs claim-safety (Finding 1) + robust linter matches multi-word
compound names (Finding 2). Coordinated per MODEB_STRENGTHEN."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from mamey.modeb_structure_gate import lint_card

def _cs(findings):
    return [x for x in findings if (x.get("code") if isinstance(x, dict) else "") == "CLAIM_SAFETY"]

def test_verify_modeb_now_runs_claim_safety():
    card = "# §1 Identity\n" + "x " * 60 + "\nThis BGC produces phosphonoacetic acid at high titer.\n"
    assert _cs(lint_card(card, check_depth=False)) == []                     # off by default
    assert _cs(lint_card(card, check_depth=False, check_claim_safety=True))  # on -> caught

def test_robust_linter_matches_multiword_names():
    from claim_safety_linter import lint_claim_safety_report as lint
    cn = {"fosfomycin", "phosphonoacetic acid", "heat-stable antifungal factor"}
    ident = lambda t: bool([r for r in lint(t, compound_names=cn) if r["violation_type"] == "identity_overclaim"])
    assert ident("This BGC produces fosfomycin.")                            # single-word (keep)
    assert ident("This BGC produces phosphonoacetic acid.")                  # multi-word (new)
    assert ident("This cluster synthesizes heat-stable antifungal factor.")  # multi-word (new)
    assert not ident("does not support that this produces phosphonoacetic acid")  # negated
    assert not ident("capacity consistent with phosphonoacetic acid biosynthesis")  # capacity
    assert not ident("This produces a signal peptide.")                      # non-compound, no FP
