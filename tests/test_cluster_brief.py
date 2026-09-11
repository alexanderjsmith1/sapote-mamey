"""cluster_brief: comparative-chain driver. Hermetic — tests the pure parsers + render.

The end-to-end subprocess orchestration is verified on real GBKs in the session (provided-GBK,
NCBI, and --category scope ingress); those need biopython + real GBKs and are not re-run here.
These lock the parsing + the degenerate-completeness honesty + the fetched-label regression.
"""
import csv
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("cluster_brief", ROOT / "tools" / "cluster_brief.py")
cb = importlib.util.module_from_spec(_s)
_s.loader.exec_module(cb)


def test_fetched_label_takes_part_after_colon():
    # regression: --ncbi ACCESSION:label -> the GBK is <label>.gbk, not <accession>.gbk
    assert cb._fetched_label("X62690.1:probe_ref") == "probe_ref"
    assert cb._fetched_label("MF055656.1:nikkomycin") == "nikkomycin"
    assert cb._fetched_label("bare") == "bare"


def test_split_labelpath():
    assert cb._split_labelpath("r001:/a/b.gbk") == ("r001", "/a/b.gbk")
    assert cb._split_labelpath("/a/b.gbk") == (None, "/a/b.gbk")


def test_parse_compare():
    line = "[cluster_gene_compare] 3 clusters, 7 confident gene pairs, 90 ortholog groups (0 core in all 3)."
    r = cb._parse_compare(line)
    assert r == dict(n_clusters=3, n_pairs=7, n_groups=90, n_core=0)
    assert cb._parse_compare("nothing here") is None


def test_parse_relate_closest():
    line = "[cluster_relate] Closest pair: r001 and r007 (5 shared genes at 65.5% mean identity; similarity 0.11)."
    r = cb._parse_relate_closest(line)
    assert r["a"] == "r001" and r["b"] == "r007" and r["shared"] == 5
    assert r["mean_id"] == 65.5 and r["similarity"] == 0.11


def test_closest_ref_from_matrix():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "distance_matrix.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["", "q", "refA", "refB"])
            w.writerow(["q", "0.0", "0.9", "0.4"])
            w.writerow(["refA", "0.9", "0.0", "0.7"])
            w.writerow(["refB", "0.4", "0.7", "0.0"])
        r = cb._closest_ref_from_matrix(str(p), "q")
        assert r["label"] == "refB" and r["distance"] == 0.4 and r["similarity"] == 0.6


def test_render_degenerate_completeness_is_undefined_not_zero():
    """0/0 (references share no recurrent gene set) must read 'undefined', never '0%'."""
    res = dict(query="q", n_refs=2, outdir="x",
               completeness={"n_cluster_genes": 0, "n_present": 0, "n_missing": 0, "completeness_pct": 0.0},
               closest_ref=None, closest_pair=None, compare=None, steps=[])
    md = cb.render_md(res)
    assert "undefined" in md
    assert "0%" not in md
    # no over-reaching 'Read:' line when completeness is undefined
    assert "**Read:**" not in md


def test_render_defined_completeness_emits_read():
    res = dict(query="q", n_refs=1, outdir="x",
               completeness={"n_cluster_genes": 30, "n_present": 27, "n_missing": 3, "completeness_pct": 90.0},
               interior_note="", closest_ref=None, closest_pair=None, compare=None, steps=[])
    md = cb.render_md(res)
    assert "90.0%" in md and "27/30" in md
    assert "**Read:**" in md


def test_render_error_path():
    res = dict(query="q", outdir="x", steps=[("fetch_reference_cluster", False, "boom")],
               error="no references (supply --reference / --ncbi / --acc)")
    md = cb.render_md(res)
    assert "cannot run" in md and "no references" in md
