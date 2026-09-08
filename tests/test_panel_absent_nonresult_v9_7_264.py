"""v9.7.264 follow-on — the PANEL_ABSENT_CLAIM non-result exemption must cover the new
selected-but-no-results branch, not just the no-panel branch.

.264 extended PANEL_ABSENT_CLAIM to flag a per-gene BLASTp *result* claimed for a BGC that is selected
but has no returned-alignments artifact. That branch fires on exactly the selected-but-not-run BGCs whose
correct §4 says the panel is deferred / recommended / N-A — so the topic-mention false positive
(_PANEL_RESULT_RE matches a bare "per-gene BLASTp") is *widened* onto the population the extension targets.
Since PANEL_ABSENT_CLAIM is ERROR and release-blocking, that keeps a correctly-authored selected-not-run
card out of RELEASE_READY.

The panel non-result exemption (deferred / recommended / N-A / pending / to-be-run) must skip before BOTH
branches; a stated RESULT ("overturned two of ten") must still fire on both.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from mamey.modeb_structure_gate import _panel_absent_claim_findings

SELECTED_NOT_RUN = {"panels_present": {"BGC031"}, "blastp_results_present": set()}
NO_PANEL = {"panels_present": set()}


def _codes(card, ctx):
    return [f["code"] for f in _panel_absent_claim_findings(card, ctx)]


def test_deferred_or_na_on_selected_not_run_bgc_is_not_a_claim():
    for sent in (
        "Per-gene BLASTp for BGC031 is deferred pending the run.",
        "§4 per-gene BLASTp: N/A for BGC031.",
        "A per-gene BLASTp panel is recommended for BGC031 before promotion.",
        "A per-gene BLASTp panel would be needed to settle BGC031.",
    ):
        assert "PANEL_ABSENT_CLAIM" not in _codes(sent, SELECTED_NOT_RUN), sent


def test_real_result_still_fires_on_selected_not_run_branch():
    card = "Per-gene BLASTp overturned two of ten on BGC031."
    assert "PANEL_ABSENT_CLAIM" in _codes(card, SELECTED_NOT_RUN)


def test_real_result_still_fires_on_no_panel_branch():
    card = "Per-gene BLASTp overturned two of ten on BGC031."
    assert "PANEL_ABSENT_CLAIM" in _codes(card, NO_PANEL)


def test_deferred_on_no_panel_bgc_is_not_a_claim():
    assert "PANEL_ABSENT_CLAIM" not in _codes(
        "A per-gene BLASTp panel is recommended for BGC031.", NO_PANEL)
