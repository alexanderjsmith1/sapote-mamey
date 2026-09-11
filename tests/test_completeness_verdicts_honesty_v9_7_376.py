"""v9.7.376 (ACT-02): A4_Completeness_Audit must report REAL extraction state, not hardcoded PASS.

The prior code stamped A2/B1/B4/C1/C2/D1/F1 = PASS and overall = PASS_EXTRACTION before checking
anything, so a governed handoff asserted success it never verified. These tests pin that a run
whose extraction stages did not run does NOT report PASS_EXTRACTION.
"""
from types import SimpleNamespace
from mamey.master_workbook import _completeness_verdicts


def _ctx(strain_id="AS-TEST", source="bee-associated"):
    return SimpleNamespace(strain_id=strain_id, source=source)


def test_incomplete_run_no_scans_is_not_pass_extraction():
    run = SimpleNamespace(context=_ctx(), bgcs=[object()], source_scans=None)
    v = _completeness_verdicts(run, triage=[])
    assert v["overall"] != "PASS_EXTRACTION", "a run with no source_scans must not report PASS_EXTRACTION"
    assert v["overall"] == "INCOMPLETE_EXTRACTION"
    assert v["B4_scans"] == "NOT_LOADED"
    assert v["D1_rggmci"] == "NOT_COMPUTED"
    assert v["C1_dapr_ab"] == "NOT_LOADED" and v["C2_dapr_af"] == "NOT_LOADED"


def test_full_run_is_pass_extraction():
    ss = SimpleNamespace(rggmci={"pairs": []})
    run = SimpleNamespace(context=_ctx(), bgcs=[object(), object()], source_scans=ss)
    v = _completeness_verdicts(run, triage=[object()])
    assert v["overall"] == "PASS_EXTRACTION"
    for k in ("A2_registry", "B1_bgc_master", "B4_scans", "C1_dapr_ab", "C2_dapr_af", "D1_rggmci"):
        assert v[k] == "PASS", f"{k} should PASS on a full run"
    assert v["E1_mode_b"] == "JUDGMENT_PENDING"


def test_no_source_reports_ecology_unknown_not_pass():
    ss = SimpleNamespace(rggmci={})
    run = SimpleNamespace(context=_ctx(source="not supplied"), bgcs=[object()], source_scans=ss)
    v = _completeness_verdicts(run, triage=[object()])
    assert v["F1_ecology"] == "UNKNOWN", "unsupplied source must not report ecology PASS"
    # ecology is metadata, not extraction-core, so overall can still PASS
    assert v["overall"] == "PASS_EXTRACTION"


def test_missing_strain_id_fails_registry_and_overall():
    ss = SimpleNamespace(rggmci={})
    run = SimpleNamespace(context=_ctx(strain_id=""), bgcs=[object()], source_scans=ss)
    v = _completeness_verdicts(run, triage=[object()])
    assert v["A2_registry"] == "FAIL"
    assert v["overall"] == "INCOMPLETE_EXTRACTION"
