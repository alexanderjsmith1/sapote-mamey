"""Tests for cluster_relate — synthetic clusters with a known relationship, no network."""
import importlib.util, tempfile
from pathlib import Path
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cluster_relate.py"


def _load():
    pytest.importorskip("Bio"); pytest.importorskip("scipy")
    spec = importlib.util.spec_from_file_location("cr", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


G1 = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKR"
G1b = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKQ"  # ~G1
G2 = "MPQLAFDIGFFAELPKLQPPVRRGVLEAWEKFDRLTLDQLFRDPGLKLESLKNARDKQIRTIRIDRFWRGVVLAPPSG"
G3 = "MSDNKQTLVRALKAGDLTAAEELLADLGVDVNAQDDDGRTPLHLAAYNGHLEIVKLLLAKGADVNAKDNDGWTPLHA"


def _gbk(path, seqs):
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    from Bio import SeqIO
    rec = SeqRecord(Seq("N" * (len(seqs) * 1000 + 100)), id="s", name="s", description="")
    rec.annotations["molecule_type"] = "DNA"
    for i, aa in enumerate(seqs):
        f = SeqFeature(FeatureLocation(i * 1000, i * 1000 + 900, strand=1), type="CDS")
        f.qualifiers["locus_tag"] = [f"g{i}"]; f.qualifiers["translation"] = [aa]
        rec.features.append(f)
    SeqIO.write(rec, str(path), "genbank")


def test_distance_reflects_similarity(tmp_path):
    m = _load()
    # A and B nearly identical (all 3 genes), C shares 1 gene, D shares none
    _gbk(tmp_path / "A.gbk", [G1, G2, G3])
    _gbk(tmp_path / "B.gbk", [G1b, G2, G3])
    _gbk(tmp_path / "C.gbk", [G1, "WWWWWWYYYYYYCCCCCCMMMMMM", "KPKPKPKPKPKPKPKPKPKP"])
    labels = ["A", "B", "C"]
    clusters, D, S, detail = m.pairwise_distances(
        labels, [str(tmp_path / f"{x}.gbk") for x in labels], min_id=30)
    # A-B (near-identical) closer than A-C
    assert D[0][1] < D[0][2]
    assert S[0][1] > S[0][2]


def test_newick_and_topology(tmp_path):
    m = _load()
    _gbk(tmp_path / "A.gbk", [G1, G2, G3])
    _gbk(tmp_path / "B.gbk", [G1b, G2, G3])   # sister of A
    _gbk(tmp_path / "D.gbk", ["WYWYWYWYWYWYWYWY", "CMCMCMCMCMCMCMCM", "KPKPKPKPKPKPKPKP"])  # outgroup
    labels = ["A", "B", "D"]
    clusters, D, S, detail = m.pairwise_distances(
        labels, [str(tmp_path / f"{x}.gbk") for x in labels], min_id=30)
    nwk = m.upgma_newick(labels, D)
    assert nwk.endswith(";") and "A" in nwk and "B" in nwk and "D" in nwk
    # A and B group together (both share the (A,B) subtree before D joins)
    assert "(A:" in nwk and "B:" in nwk
