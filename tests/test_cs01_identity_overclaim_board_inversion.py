"""CS-01 — the identity-overclaim check was INVERTED when a compound board was supplied.

`mamey claim-safety --package <dir>` derives the strain's compound names from its triage board and
prints that it is "using the robust check path". That path then evaluated

    if cnames is not None:
        return t in cnames            # lint_claim_safety
        return any(cn in probe ...)   # lint_claim_safety_report._identity_hit

so a production verb on a compound NOT on the board returned False — i.e. supplying the real
compound list *disabled* the check for every other name. The more likely a compound name was an LLM
hallucination, the less likely it was to be caught.

Measured before the fix, with a board that does not list the named compounds:
    "BGC041 produces zorbamycin. The cluster synthesizes vancomycin and yields teicoplanin."
    -> 0 findings.

The fix is verb-class-aware, and the split is measured rather than assumed:

  * PRODUCTION verbs (produces / synthesizes / yields) are inherently identity assertions, so a
    compound-shaped token falls through to the shape heuristic whether or not it is on the board.
  * COPULA (is / are) keeps the board gate. Removing it there fired **192** findings across the ten
    shipped claim-safe exemplars ("is that", "are read", "is expected", "makes fragmentation") —
    the board really is the only thing separating "is colibrimycin" from "is Edge-status".

Net effect on the ten shipped exemplars with a board supplied: 1 -> 2 findings (+1, a genuine
false positive on "makes fragmentation risk low" in the RiPP exemplar, documented not tuned away).
True positives on the hallucination case: 0 -> 3.
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("csl", ROOT / "tools" / "claim_safety_linter.py")
csl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(csl)

# A board that does NOT contain any of the compounds named in the overclaim below — this is the
# realistic case, because a hallucinated name is by definition not in the strain's evidence.
BOARD = {"kirromycin", "colibrimycin", "selvamicin"}

OVERCLAIM = ("BGC041 (NODE_6_length_204811 - region002) produces zorbamycin. "
             "The cluster synthesizes vancomycin and yields teicoplanin.")

CLAIM_SAFE = ("BGC041 (NODE_6_length_204811 - region002) shows biosynthetic capacity consistent "
              "with a glycopeptide-like compound. KnownClusterBlast similarity to the vancomycin "
              "reference is an upper bound, not identity; no production is claimed.")

NEGATED = "This cluster does not produce vancomycin, and the region is Edge-status."


# ── the known-bad input ────────────────────────────────────────────────────────────────────────

def test_production_overclaim_flags_even_when_compound_is_not_on_the_board():
    """KNOWN-BAD: three flagrant production claims, board lists none of them."""
    findings = csl.lint_claim_safety(OVERCLAIM, compound_names=BOARD)
    assert len(findings) == 3, (
        "supplying a compound board must not exempt compounds absent from it — that is the "
        f"inversion CS-01 fixes. Got: {findings}"
    )
    joined = " ".join(findings).lower()
    for name in ("zorbamycin", "vancomycin", "teicoplanin"):
        assert name in joined, f"{name} not flagged: {findings}"


def test_report_api_flags_the_same_overclaim_with_a_non_matching_board():
    """The row-emitting API has its own copy of the logic; both must be fixed."""
    rows = csl.lint_claim_safety_report(OVERCLAIM, card_id="AS-TEST_BGC041", section="4",
                                        compound_names=BOARD)
    assert len(rows) == 3, rows
    assert all(r["violation_type"] == "identity_overclaim" for r in rows), rows


def test_board_match_still_flags():
    """Control: a compound that IS on the board is still an overclaim, as before."""
    assert len(csl.lint_claim_safety("BGC041 produces kirromycin.", compound_names=BOARD)) == 1


# ── the controls that stop the fix from over-firing ────────────────────────────────────────────

def test_capacity_framed_text_stays_clean():
    """Control: correctly hedged capacity language must not flag, board or no board."""
    assert csl.lint_claim_safety(CLAIM_SAFE, compound_names=BOARD) == []
    assert csl.lint_claim_safety(CLAIM_SAFE) == []


def test_negated_production_stays_clean():
    """Control: a denial is not an overclaim."""
    assert csl.lint_claim_safety(NEGATED, compound_names=BOARD) == []


def test_copula_keeps_the_board_gate():
    """Control: the copula branch is NOT opened up — that is what caused the 192-finding flood.

    Ordinary prose full of `is`/`are` must stay clean when a board is supplied.
    """
    prose = ("The expectation is that the two-component system is recognised by the protease. "
             "The reads are read in order and the signal is concentrated at the interior. "
             "Placement is internal and the risk is low.")
    assert csl.lint_claim_safety(prose, compound_names=BOARD) == [], (
        "opening the copula branch floods claim-safe prose; the board gate must stay for `is/are`"
    )


@pytest.mark.parametrize("exemplar", [
    "docs/reference/modeb_exemplars/nrps_exemplar.md",
    "docs/reference/modeb_exemplars/t1pks_exemplar.md",
    "docs/reference/modeb_exemplars/terpene_exemplar.md",
    "docs/reference/modeb_exemplars/siderophore_exemplar.md",
])
def test_shipped_exemplars_stay_clean_under_the_fix(exemplar):
    """Calibration lock: the shipped claim-safe exemplars must not start firing.

    These four were measured at 0 findings both before and after the fix. The RiPP exemplar and the
    bench guide are deliberately excluded — they carry one known finding each, documented in the
    module docstring rather than tuned away.
    """
    path = ROOT / exemplar
    if not path.exists():
        pytest.skip(f"{exemplar} not present in this tier")
    text = path.read_text(encoding="utf-8")
    assert csl.lint_claim_safety(text, compound_names=BOARD) == [], (
        f"{exemplar} started firing under the CS-01 fix — re-measure before shipping"
    )
