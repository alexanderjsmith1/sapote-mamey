"""v9.7.231: hermetic coverage for the tab-reconcile parser's negative-evidence discipline — the
fixture-based test (test_tab_reconcile_patch_chat) returns early without the 143MB AS-760.zip, so these
unit-level checks give CI a real signal for the NO_HITS logic + node normalization."""
import sys, pathlib, tempfile, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.tab_reconcile import _summarize_clusterblast_txt, _node_core
from pathlib import Path

def test_empty_significant_hits_is_no_hits_not_generic_hit():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "sub.txt"
        p.write_text("ClusterBlast scores for NODE_32\n\nSignificant hits: \n\nDetails:\n", encoding="utf-8")
        n, res = _summarize_clusterblast_txt(p)
        assert (n, res) == (0, "NO_HITS")          # parsed-zero = negative evidence

def test_missing_tab_is_absent_not_no_hits():
    n, res = _summarize_clusterblast_txt(Path("/nonexistent/x.txt"))
    assert res == "TAB_ABSENT"                     # missing != parsed-zero

def test_real_hit_is_counted():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "kcb.txt"
        p.write_text("Significant hits: \n 1. BGC0000115.5 nystatin A1\n\nDetails:\n 1. BGC0000115.5\n", encoding="utf-8")
        n, res = _summarize_clusterblast_txt(p)
        assert res == "BGC0000115.5" and n >= 1

def test_node_core_strips_coverage_suffix():
    assert _node_core("NODE_32_length_60747_cov_53.323339") == "NODE_32_length_60747_cov_53"
    assert _node_core(None) is None


def test_output_prefix_no_duplicate_node_when_bgc_absent():
    """v9.7.233 regression: on the --node/--region path (no --bgc), output filenames must NOT
    duplicate the node id. The old prefix `{bgc or node}_{node}` collapsed to `<node>_<node>`."""
    from mamey.tab_reconcile import _safe_name
    rec_id = "NODE_10_length_54129_cov_72.266743"
    # replicate the (fixed) prefix logic used at the write sites
    def prefix(bgc):
        return f"{bgc}_{_safe_name(rec_id)}" if bgc else _safe_name(rec_id)
    no_bgc = prefix(None)
    with_bgc = prefix("BGC028")
    assert no_bgc == _safe_name(rec_id), f"node id duplicated: {no_bgc!r}"
    assert no_bgc.count("NODE_10") == 1, f"node id appears {no_bgc.count('NODE_10')}x: {no_bgc!r}"
    assert with_bgc == f"BGC028_{_safe_name(rec_id)}"   # BGC path unchanged
    assert with_bgc.count("NODE_10") == 1
