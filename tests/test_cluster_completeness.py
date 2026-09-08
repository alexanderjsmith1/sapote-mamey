"""Tests for cluster_completeness — synthetic clusters, no network.

Checks: completeness score; strict-majority cluster-gene filter (singleton flanking excluded);
and truncation-awareness (missing genes at the END read as truncation; an INTERIOR gap reads as
divergence).
"""
import importlib.util
from pathlib import Path
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cluster_completeness.py"

# five distinct proteins
A = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKR"
B = "MPQLAFDIGFFAELPKLQPPVRRGVLEAWEKFDRLTLDQLFRDPGLKLESLKNARDKQIRTIRIDRFWRGVVLAPPSG"
C = "MSDNKQTLVRALKAGDLTAAEELLADLGVDVNAQDDDGRTPLHLAAYNGHLEIVKLLLAKGADVNAKDNDGWTPLHA"
D = "MADEEKLPPGWEKRMSRSSGRVYYFNHITNASQWERPSGNSSSGGKNGQGEPARVRCSHLLVKHSQSRRPSSWRQEK"
E = "MGSSHHHHHHSSGLVPRGSHMLEDPYVKEAENLKKYFNAGHSDVADNGTLFLGILKNWKEESDRKIMQSQIVSFYFK"


def _load():
    pytest.importorskip("Bio")
    spec = importlib.util.spec_from_file_location("cc", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _mk(path, seqs):
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


def _genes(m, path): return m._genes(path)


def test_completeness_and_end_truncation(tmp_path):
    m = _load()
    # references complete: A B C D E ; query has A B C (missing D E at the END)
    _mk(tmp_path / "r1.gbk", [A, B, C, D, E])
    _mk(tmp_path / "r2.gbk", [A, B, C, D, E])
    _mk(tmp_path / "q.gbk", [A, B, C])
    rep = m.assess(_genes(m, tmp_path / "q.gbk"),
                   [("r1", _genes(m, tmp_path / "r1.gbk")), ("r2", _genes(m, tmp_path / "r2.gbk"))])
    assert rep["n_cluster_genes"] == 5 and rep["n_present"] == 3 and rep["n_missing"] == 2
    assert rep["completeness_pct"] == 60.0
    assert rep["interior_missing"] == 0 and rep["end_missing"] == 2
    assert rep["missing_end_loaded"] is True          # truncation-consistent


def test_interior_gap_reads_as_divergence(tmp_path):
    m = _load()
    # query has A B _ D E (missing C in the MIDDLE) -> interior loss, not truncation
    _mk(tmp_path / "r1.gbk", [A, B, C, D, E])
    _mk(tmp_path / "r2.gbk", [A, B, C, D, E])
    _mk(tmp_path / "q.gbk", [A, B, D, E])
    rep = m.assess(_genes(m, tmp_path / "q.gbk"),
                   [("r1", _genes(m, tmp_path / "r1.gbk")), ("r2", _genes(m, tmp_path / "r2.gbk"))])
    assert rep["n_missing"] == 1
    assert rep["interior_missing"] == 1               # C is between present genes
    assert rep["missing_end_loaded"] is False


def test_singleton_flanking_excluded(tmp_path):
    m = _load()
    # E is only in ONE reference (flanking) -> not a cluster gene; completeness unaffected by it
    _mk(tmp_path / "r1.gbk", [A, B, C, E])
    _mk(tmp_path / "r2.gbk", [A, B, C])
    _mk(tmp_path / "q.gbk", [A, B, C])
    rep = m.assess(_genes(m, tmp_path / "q.gbk"),
                   [("r1", _genes(m, tmp_path / "r1.gbk")), ("r2", _genes(m, tmp_path / "r2.gbk"))])
    assert rep["n_cluster_genes"] == 3                # E excluded (singleton)
    assert rep["completeness_pct"] == 100.0
