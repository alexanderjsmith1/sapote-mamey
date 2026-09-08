"""Tests for cluster_gene_compare (v9.7.299).

DB-free / network-free: build tiny synthetic GBKs in a temp dir and exercise the pipeline.
Covers: global-identity metric, annotation propagation to the /gene qualifier (the clinker
label feature), ortholog grouping, and CSV emission.
"""
import importlib.util, os, tempfile
from pathlib import Path
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cluster_gene_compare.py"


def _load():
    pytest.importorskip("Bio")
    spec = importlib.util.spec_from_file_location("cgc", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _make_gbk(path, genes, annotate=None):
    """genes: list of (locus_tag, aa). annotate: dict locus_tag->sec_met_domain label."""
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    from Bio import SeqIO
    annotate = annotate or {}
    rec = SeqRecord(Seq("N" * (len(genes) * 1000 + 100)), id="syn", name="syn",
                    description="synthetic")
    rec.annotations["molecule_type"] = "DNA"
    for i, (lt, aa) in enumerate(genes):
        f = SeqFeature(FeatureLocation(i * 1000, i * 1000 + 900, strand=1), type="CDS")
        f.qualifiers["locus_tag"] = [lt]
        f.qualifiers["translation"] = [aa]
        if lt in annotate:
            f.qualifiers["sec_met_domain"] = [annotate[lt]]
        rec.features.append(f)
    SeqIO.write(rec, str(path), "genbank")


# two real-ish homologous proteins (near-identical) and a dissimilar one
SEQ_A = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKR"
SEQ_A2 = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKQ"  # 1 sub
SEQ_B = "MPQLAFDIGFFAELPKLQPPVRRGVLEAWEKFDRLTLDQLFRDPGLKLESLKNARDKQIRTIRIDRFWRGVVLAPPSG"


def test_global_identity_metric():
    m = _load(); al = m._aligner()
    gid, cov = m.global_identity(al, SEQ_A, SEQ_A2)
    assert gid > 90 and gid <= 100
    gid2, _ = m.global_identity(al, SEQ_A, SEQ_B)
    assert gid2 < 30  # unrelated pair below the confident bar


def test_annotation_propagates_to_gene_qualifier():
    """A gene annotated in ONE cluster should label its ortholog's /gene in another (clinker uses /gene)."""
    m = _load()
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        a = d / "A.gbk"; b = d / "B.gbk"
        _make_gbk(a, [("a1", SEQ_A), ("a2", SEQ_B)], annotate={"a1": "nikJ"})
        _make_gbk(b, [("b1", SEQ_A2), ("b2", "MGGGGGGKKKKKKPPPPPPWWWWWWDDDDDDEEEEEE")])  # b1 ~ a1
        labels = ["A", "B"]
        clusters, recs, pairs, groups, resolved = m.compare(labels, [str(a), str(b)], min_id=30)
        m.write_annotated_gbks(labels, [str(a), str(b)], clusters, recs, resolved, str(d))
        txt = (d / "annotated_gbks" / "B.gbk").read_text()
        assert 'gene="nikJ"' in txt, "annotation did not propagate to the ortholog's /gene qualifier"


def test_ortholog_grouping_and_csv(tmp_path):
    m = _load()
    a = tmp_path / "A.gbk"; b = tmp_path / "B.gbk"
    _make_gbk(a, [("a1", SEQ_A), ("a2", SEQ_B)])
    _make_gbk(b, [("b1", SEQ_A2)])  # only b1, ortholog of a1
    labels = ["A", "B"]
    clusters, recs, pairs, groups, resolved = m.compare(labels, [str(a), str(b)], min_id=30)
    # exactly one confident cross-cluster pair (a1<->b1)
    assert len(pairs) == 1
    rows = m.write_csvs(labels, clusters, pairs, groups, resolved, str(tmp_path))
    assert (tmp_path / "gene_pairs.csv").exists()
    assert (tmp_path / "ortholog_matrix.csv").exists()
    # one group present in both clusters
    assert any(r[0] == 2 for r in rows)


# ── F03 (v9.7.353): unmeasured identity must be NaN, never a fabricated 60 ────────────
def test_unmeasured_identity_is_nan_not_fabricated():
    """build_identity_matrix must leave an unmeasured pairwise identity as NaN (and flag the
    cell), never back-fill it with the old hard-coded 60 that read as real data."""
    import numpy as np
    m = _load()
    # one ortholog group of 3 members across clusters 0,1,2; anchor = member on cluster 0.
    # pairs measures anchor(0)->cluster1 at 87%, but NOT anchor(0)->cluster2 (unmeasured).
    #   pair tuple = (ci, gi, cj, gj, gid, cov)
    disp = [(3, "groupA", {}, [(0, 0), (1, 0), (2, 0)])]
    pairs = [(0, 0, 1, 0, 87.0, 100.0)]
    M, unmeasured = m.build_identity_matrix(disp, pairs, n=3)
    assert M[0, 0] == 100                      # anchor
    assert M[0, 1] == 87.0                      # measured
    assert np.isnan(M[0, 2])                    # unmeasured -> NaN, not 60
    assert 60 not in np.nan_to_num(M, nan=-1)   # the fabricated 60 must not appear anywhere
    assert (0, 2) in unmeasured                 # flagged distinctly for the renderer
    assert (0, 1) not in unmeasured             # a measured cell is not flagged
