"""v9.7.264 — PANEL_ABSENT_CLAIM extended: a per-gene BLASTp result claimed for a BGC that has a
panel *selection* but no returned-alignments artifact (selected-but-never-run) is flagged, but only
when the package tracks results (a blastp_online/ dir exists). If results aren't tracked, the stricter
case stays silent — it cannot tell 'never run' from 'results not shipped here'. Closes the S_erythraea
BGC017 residual gap the earlier selection-only check missed."""
from mamey.modeb_structure_gate import _panel_absent_claim_findings

CARD = "In §4, per-gene BLASTp for BGC017 overturned the antiSMASH call on ctg1_5."

def _codes(ctx):
    return [f["code"] for f in _panel_absent_claim_findings(CARD, ctx)]

def test_selected_but_never_run_flags_when_results_tracked():
    # BGC017 is selected (in panels) but has no results artifact; results ARE tracked -> flag.
    ctx = {"panels_present": {"BGC017"}, "blastp_results_present": set()}
    assert "PANEL_ABSENT_CLAIM" in _codes(ctx)

def test_run_bgc_with_results_artifact_passes():
    # BGC017 selected AND has a results artifact -> no finding.
    ctx = {"panels_present": {"BGC017"}, "blastp_results_present": {"BGC017"}}
    assert "PANEL_ABSENT_CLAIM" not in _codes(ctx)

def test_results_not_tracked_stays_silent_on_the_stricter_case():
    # Selected, no results key at all -> cannot judge -> silent (preserves pre-.264 behavior).
    ctx = {"panels_present": {"BGC017"}}
    assert "PANEL_ABSENT_CLAIM" not in _codes(ctx)

def test_no_panel_at_all_still_flags_existing_behavior():
    # BGC017 not selected -> original no-panel ERROR still fires.
    ctx = {"panels_present": {"BGC001"}, "blastp_results_present": {"BGC001"}}
    assert "PANEL_ABSENT_CLAIM" in _codes(ctx)
