"""extract_cluster counts markers on distinct predicted genes, not marker names."""
import importlib.util
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "extract_cluster.py"


def _module():
    spec = importlib.util.spec_from_file_location("ec_464r3", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_two_names_on_one_gene_count_once():
    m = _module()
    assert m.distinct_gene_assignments([(40, "markA", 99.0, 0), (40, "markB", 99.0, 0)]) == 1


def test_distinct_genes_count_separately_and_matching_is_maximal():
    m = _module()
    hits = [(40, "markA", 99.0, 0), (40, "markB", 99.0, 0), (41, "markB", 95.0, 1)]
    assert m.distinct_gene_assignments(hits) == 2


def test_shared_hit_does_not_reach_two_marker_threshold():
    from tests.test_extract_cluster import _load, _synthetic_prots, MARK_A
    m = _load()
    prots, _ = _synthetic_prots()
    cl = m.find_cluster(prots, [("markA", MARK_A), ("markA_copy", MARK_A)], min_identity=90, window=25)
    assert cl["n_marker_names_matched"] == 2
    assert cl["n_markers"] == 1
    assert cl["shared_target_genes"] == [[40, ["markA", "markA_copy"]]]
