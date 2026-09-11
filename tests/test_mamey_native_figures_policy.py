from mamey.mamey_native_figures import FIGURE_SET_SPEC, RAW_BGC_COUNT_POLICY


def test_mamey_native_figure_spec_has_mamey_logic_panels():
    ids = {row[0] for row in FIGURE_SET_SPEC}
    assert "ab_af_portfolio" in ids
    assert "dual_track_leads" in ids
    assert "rggmci_state_summary" in ids
    assert "module_completeness" in ids
    assert "class_presence" in ids


def test_raw_bgc_count_is_qc_only_in_policy_and_spec():
    assert "must not be used as a headline biological ranking" in RAW_BGC_COUNT_POLICY
    raw_rows = [row for row in FIGURE_SET_SPEC if "raw_bgc" in row[0]]
    assert raw_rows
    assert all(row[2] == "qc_only" for row in raw_rows)
