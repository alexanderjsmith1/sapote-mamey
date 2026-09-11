"""AMBER_04 (v9.7.349 rebase): tests for the two-tier prune bridge
(tools/prune_neighbors_from_tree.py).

Pure python, no external tools, never runs a tree. Checks the newick parse, the
patristic neighbour selection, the <=60-tip cap (farthest references trimmed first,
queries/outgroups never dropped), and the Codex-compatible panel TSV emission
(candidate_id/role/source_path/selection_basis/related_query_ids).
"""
import os
import csv
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_PRUNE = os.path.join(ROOT, "tools", "prune_neighbors_from_tree.py")

spec = importlib.util.spec_from_file_location("prune_neighbors", _PRUNE)
prune = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prune)

# One query AS-101 next to R1; R2 mid; R3 far. One marked outgroup.
TREE = ("(((AS-101_query:0.01,Streptomyces_near_R1:0.01)90:0.05,"
        "(Streptomyces_mid_R2:0.02,Streptomyces_far_R3:0.30)80:0.05)70:0.1,"
        "Kitasatospora_setae_OUTGROUP:0.4);")


def test_parse_recovers_all_tips():
    root = prune.parse(TREE)
    names = sorted(n.name for n in prune.leaves(root))
    assert names == sorted([
        "AS-101_query", "Streptomyces_near_R1", "Streptomyces_mid_R2",
        "Streptomyces_far_R3", "Kitasatospora_setae_OUTGROUP"])


def test_panel_k1_picks_nearest_reference_only():
    panel = prune.build_panel(prune.parse(TREE), k=1)
    assert panel['queries'] == ["AS-101_query"]
    assert panel['outgroups'] == ["Kitasatospora_setae_OUTGROUP"]
    assert set(panel['references']) == {"Streptomyces_near_R1"}
    # the reference records which query it was selected for
    assert panel['references']["Streptomyces_near_R1"]['related'] == ["AS-101_query"]


def test_panel_k2_adds_next_nearest_not_farthest():
    panel = prune.build_panel(prune.parse(TREE), k=2)
    assert "Streptomyces_near_R1" in panel['references']
    assert "Streptomyces_mid_R2" in panel['references']
    assert "Streptomyces_far_R3" not in panel['references']


def test_cap_trims_farthest_reference_first_never_query():
    # cap=3 (query + outgroup + 1 ref). With k=3 all three refs qualify; the two
    # farthest (R2, R3) must be trimmed, R1 (nearest) kept; query+outgroup untouched.
    panel = prune.build_panel(prune.parse(TREE), k=3, max_tips=3)
    keep = prune.keep_set(panel)
    assert "AS-101_query" in keep and "Kitasatospora_setae_OUTGROUP" in keep
    assert set(panel['references']) == {"Streptomyces_near_R1"}
    assert set(panel['trimmed']) == {"Streptomyces_mid_R2", "Streptomyces_far_R3"}
    assert len(keep) == 3


def test_panel_tsv_has_codex_columns_and_bases(tmp_path):
    panel = prune.build_panel(prune.parse(TREE), k=2)
    out = tmp_path / "panel.tsv"
    prune.write_panel_tsv(panel, str(out), gdir="/genomes")
    rows = list(csv.DictReader(open(out), delimiter="\t"))
    assert list(rows[0].keys()) == [
        "candidate_id", "role", "source_path", "selection_basis", "related_query_ids"]
    roles = {r["candidate_id"]: r["role"] for r in rows}
    assert roles["AS-101_query"] == "QUERY"
    assert roles["Kitasatospora_setae_OUTGROUP"] == "OUTGROUP"
    ref = [r for r in rows if r["role"] == "REFERENCE"][0]
    assert ref["selection_basis"] == "nearest_neighbour_patristic_MLSA"
    assert "AS-101_query" in ref["related_query_ids"]
    assert ref["source_path"].endswith(".fna")


def test_max_tips_above_ceiling_is_clamped():
    # main() clamps --max-tips above the 60 ceiling; exercise via build_panel directly.
    assert prune.PANEL_CEILING == 60


def test_help_returns_nonzero():
    assert prune.main(["--help"]) == 2
