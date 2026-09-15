"""TREES_432 — the established Amycolatopsis refpkg carries two FASTA headers on one line.

Root cause (verified on the local ncbi_16S_RefSeq BLAST DB): NR_109504.1 and NR_118259.1 are the
same strain (YIM 75904) with an identical sequence, so makeblastdb stores ONE entry with two
deflines and `blastdbcmd -entry` prints them on a single header line joined by " >". A harvester
copied that line verbatim; the dedup writer then re-emitted it and every rebuild was held by the
admission gate (MULTIPLE_FASTA_DEFINITIONS_OR_ACCESSIONS). The writer now keeps the FIRST
definition, records each trailing definition in reference_dedup.tsv as a dropped merged-defline
row, and can never emit a header containing '>'.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import phylo_place as pp  # noqa: E402

MERGED = (">NR_109504.1 Amycolatopsis dongchuanensis strain YIM 75904 16S ribosomal RNA, partial sequence "
          ">NR_118259.1 Amycolatopsis dongchuanensis strain YIM 75904 16S ribosomal RNA, partial sequence")
OTHER = ">NR_024884.1 Amycolatopsis orientalis strain DSM 40040 16S ribosomal RNA, partial sequence"
SEQ_A = "ACGT" * 380
SEQ_B = "TTGA" * 380


def test_split_merged_deflines_keeps_first_and_hands_back_the_rest():
    recs, merged = pp._split_merged_deflines([(MERGED[1:], SEQ_A), (OTHER[1:], SEQ_B)])
    assert recs == [(MERGED[1:].split(" >")[0], SEQ_A), (OTHER[1:], SEQ_B)]
    assert merged == [("NR_118259.1 Amycolatopsis dongchuanensis strain YIM 75904 16S ribosomal RNA, partial sequence",
                       "NR_109504.1 Amycolatopsis dongchuanensis strain YIM 75904 16S ribosomal RNA, partial sequence")]


def test_dedup_writer_emits_one_definition_and_reports_the_merged_one(tmp_path):
    src = tmp_path / "ref.fasta"; src.write_text(f"{MERGED}\n{SEQ_A}\n{OTHER}\n{SEQ_B}\n")
    dst = tmp_path / "ref.dedup.fasta"; rep = tmp_path / "reference_dedup.tsv"
    n_kept, n_dropped = pp._dedup_reference(str(src), str(dst), str(rep), strain_aliases="")
    assert (n_kept, n_dropped) == (2, 1)
    headers = [ln for ln in dst.read_text().splitlines() if ln.startswith(">")]
    assert headers == [MERGED.split(" >")[0], OTHER]
    assert all(h.count(">") == 1 for h in headers)
    assert pp.screen_reference_definitions(str(dst)) == []          # the rebuilt set passes the gate
    rows = [ln.split("\t") for ln in rep.read_text().splitlines()[1:]]
    by_acc = {r[3]: r for r in rows}
    assert by_acc["NR_109504"][0] == "kept"
    assert by_acc["NR_118259"][0] == "dropped:merged-defline-same-strain"
    assert by_acc["NR_118259"][8] == MERGED.split(" >")[0][1:]       # representative = the kept header
    assert by_acc["NR_118259"][5] == "0"                              # no sequence of its own


def test_dedup_writer_flags_a_merged_defline_that_is_not_the_same_strain(tmp_path, capsys):
    foreign = (">NR_109504.1 Amycolatopsis dongchuanensis strain YIM 75904 16S ribosomal RNA "
               ">NR_024884.1 Amycolatopsis orientalis strain DSM 40040 16S ribosomal RNA")
    src = tmp_path / "ref.fasta"; src.write_text(f"{foreign}\n{SEQ_A}\n")
    dst = tmp_path / "out.fasta"; rep = tmp_path / "rep.tsv"
    pp._dedup_reference(str(src), str(dst), str(rep), strain_aliases="")
    assert "dropped:merged-defline-unresolved" in rep.read_text()
    assert "NOT provably the same strain" in capsys.readouterr().out
    assert pp.screen_reference_definitions(str(dst)) == []


def test_writer_can_never_emit_a_header_with_a_second_definition(tmp_path, monkeypatch):
    # belt and braces: if a caller bypasses the split, the writer refuses rather than propagates
    monkeypatch.setattr(pp, "_split_merged_deflines", lambda recs: (recs, []))
    src = tmp_path / "ref.fasta"; src.write_text(f"{MERGED}\n{SEQ_A}\n")
    with pytest.raises(ValueError, match="REFERENCE_HEADER_MULTIPLE_DEFINITIONS"):
        pp._dedup_reference(str(src), str(tmp_path / "o.fasta"), str(tmp_path / "r.tsv"), strain_aliases="")
