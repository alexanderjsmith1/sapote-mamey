"""F4 — KCB sweep surfaces the composite-aggregation signal ON THE ROW (not only in §3b)."""
from tools.build_first_pass_scans import _kcb_sweep


def test_composite_region_flagged_on_row():
    m = {"bgcs": [{"bgc_id": "BGC018", "kcb_cumulative": 29593, "kcb_protein_hits": 29,
                   "kcb_top": "spore pigment | x", "composite_region": True,
                   "single_protocluster_count": 5}]}
    out = _kcb_sweep(m)
    assert "COMPOSITE" in out and "5 protoclusters" in out


def test_thin_still_flags_inflated():
    m = {"bgcs": [{"bgc_id": "BGC003", "kcb_cumulative": 5000, "kcb_protein_hits": 2,
                   "kcb_top": "x | y", "composite_region": False}]}
    assert "INFLATED" in _kcb_sweep(m)


def test_clean_single_cluster_no_flag():
    m = {"bgcs": [{"bgc_id": "BGC009", "kcb_cumulative": 8000, "kcb_protein_hits": 18,
                   "kcb_top": "x | y", "composite_region": False}]}
    out = _kcb_sweep(m)
    # the data row for BGC009 carries no inflation/composite token
    row = [l for l in out.splitlines() if l.startswith("| BGC009")][0]
    assert "INFLATED" not in row and "COMPOSITE" not in row
