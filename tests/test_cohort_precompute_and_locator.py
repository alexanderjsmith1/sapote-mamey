"""v9.7.224: Part B (list-bgcs --json emits the cohort join-key assembly_locator natively) +
Part A (cohort-precompute consolidation reproduces the golden tables). Golden pack lives under the
verification pack; this test uses a small synthetic fixture for the locator + smoke-checks the tool."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from mamey.package_inspector import _cohort_locator

def test_cohort_locator_matches_architecture_format():
    # full contig + region label, NO bgc_id parenthetical — must equal the architecture Assembly_Locator
    r = {"BGC_ID": "BGC065", "Contig": "NODE_9_length_167436_cov_37", "antiSMASH_Region": "region003"}
    assert _cohort_locator(r) == "NODE_9_length_167436_cov_37 region003"

def test_cohort_locator_normalizes_bare_region_number():
    r = {"Contig": "NODE_5_length_1000_cov_10", "antiSMASH_Region": "2"}
    assert _cohort_locator(r) == "NODE_5_length_1000_cov_10 region002"

def test_cohort_locator_differs_from_bosslabel_helper():
    # the join key (full contig, no paren) is intentionally NOT the boss-facing crosswalk label
    from mamey.crosswalk import assembly_locator
    r = {"BGC_ID": "BGC065", "Contig": "NODE_9_length_167436_cov_37",
         "Node_ID": "NODE_9", "antiSMASH_Region": "region003"}
    assert _cohort_locator(r) != assembly_locator(r)   # full-contig key vs truncated boss label

def test_cohort_precompute_tool_imports_and_has_all_tables():
    import build_cohort_precompute as B
    for fn in ("build_nrps", "build_resistance", "build_tally", "_concat", "_locus_to_bgc"):
        assert hasattr(B, fn), fn
