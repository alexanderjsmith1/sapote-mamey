"""A contig on a gap-rescue or pair map is turned by its strand evidence; facing rules never turn it back.

The owner, 2026-10-03, on a strain's bottromycin-like region (core contig NODE_69) against the bottromycin A2 cluster:
"this is still totally wrong, where the first contig is reversed". All nine core matches lay on the strand opposite their
reference genes, so the strand rule turned the contig; then the split-gene rule (the two pieces of a split gene face each
other) turned it back, and the core was drawn backwards with crossing ribbons. Facing now applies only to a contig whose
strand evidence is even or absent.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gap_rescue_locus_map", ROOT / "tools" / "gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glm)


def _gbk(tmp_path):
    SeqIO = pytest.importorskip("Bio.SeqIO")
    from Bio.Seq import Seq
    from Bio.SeqFeature import FeatureLocation, SeqFeature
    from Bio.SeqRecord import SeqRecord
    rec = SeqRecord(Seq("A" * 4000), id="REF1", name="REF1", description="test cluster", annotations={"molecule_type": "DNA"})
    for i, n in enumerate(["abcA", "abcB", "abcC", "abcD"]):
        rec.features.append(SeqFeature(FeatureLocation(i * 1000, i * 1000 + 900, strand=1), type="CDS",
                                       qualifiers={"gene": [n], "translation": ["M" * 290]}))
    gbk = tmp_path / "REF1.gbk"
    SeqIO.write(rec, str(gbk), "genbank")
    return gbk


def _prot(tag, contig, start, strand):
    return {"tag": tag, "contig": contig, "start": start, "end": start + 900, "strand": strand, "contig_len": 20000}


def _row(pid, ident):
    return {"status": "PRESENT_IN_CORE", "best_protein": pid, "best_identity_pct": ident, "reciprocal_best": True}


def test_a_core_on_the_opposite_strand_is_turned_even_when_its_end_already_faces_the_link(tmp_path):
    pytest.importorskip("matplotlib")
    gbk = _gbk(tmp_path)
    # core genes abcA-abcC on the minus strand, in reverse order, at the RIGHT end of ctgA (facing would keep it unturned)
    prots = {"q1": _prot("a_3", "ctgA", 19000, -1), "q2": _prot("a_2", "ctgA", 18000, -1), "q3": _prot("a_1", "ctgA", 17000, -1),
             "q4": _prot("b_1", "ctgB", 500, 1)}
    core = {"contig": "ctgA", "start": 16500, "end": 20000, "identity": "S / ctgA / region001 / BGC001"}
    partner = {"contig": "ctgB", "start": 0, "end": 3000, "identity": "S / ctgB / region001 / BGC002"}
    rows = [_row("q1", 60.0), _row("q2", 60.0), _row("q3", 60.0), {"status": "MISSING_NOT_FOUND"}]
    rows_b = [{"status": "MISSING_NOT_FOUND"}] * 3 + [_row("q4", 50.0)]
    res = glm.draw_locus_map(gbk, rows, [], prots, [core, partner], core, "S", "test", tmp_path / "m.png",
                             tmp_path / "m.pdf", partner=partner, pair_note="pair", partner_rows=rows_b)
    assert res["flipped"]["ctgA"] is True     # strand evidence: 3 of 3 matches disagree with the reference
    assert res["flipped"]["ctgB"] is False    # its one match agrees with the reference strand


def test_contigs_run_in_reference_order_with_the_core_wherever_it_falls(tmp_path):
    """The owner, 3 Oct: "you could have put node 8 first on the left??" NODE_8 held botT and botOMT, the reference's first
    genes, but the core contig was always drawn first, so their ribbons crossed the whole figure."""
    pytest.importorskip("matplotlib")
    gbk = _gbk(tmp_path)
    prots = {"q1": _prot("a_1", "ctgA", 10000, 1), "q2": _prot("a_2", "ctgA", 11000, 1),       # core: abcC, abcD
             "q3": _prot("b_1", "ctgB", 5000, 1), "q4": _prot("b_2", "ctgB", 6000, 1)}         # elsewhere: abcA, abcB
    core = {"contig": "ctgA", "start": 9500, "end": 12500, "identity": "S / ctgA / region001 / BGC001"}
    rows = [dict(_row("q3", 80.0), status="MISSING_FOUND_CLEAR", partner_verdict="SUPPORTED"),
            dict(_row("q4", 80.0), status="MISSING_FOUND_CLEAR", partner_verdict="SUPPORTED"),
            _row("q1", 80.0), _row("q2", 80.0)]
    res = glm.draw_locus_map(gbk, rows, [], prots, [core], core, "S", "test", tmp_path / "m.png", tmp_path / "m.pdf")
    assert res["contigs_drawn"] == ["ctgB", "ctgA"]
    assert res["flipped"] == {"ctgA": False, "ctgB": False}
