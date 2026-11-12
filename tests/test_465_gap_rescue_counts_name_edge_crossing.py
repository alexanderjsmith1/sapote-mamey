"""9.7.465: the gap-rescue counts say how many core genes cross the region edge.

Fail-before on sealed 9.7.464: a core gene with only part of its length inside the region counted in "N of M
reference genes in the core" with no word in the caption, the map footnote or gene_table_counts.tsv; only that gene's
own table row said so. Pass-after: the gene still counts
in the core (region membership is by overlap, as the table rows say), gene_table_counts.tsv carries core_crossing,
and the gene-table caption ends with "N of the M core genes cross the region edge". The map footnote is unchanged.
"""
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
if "mamey" not in sys.modules:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gap_rescue_locus_map as M      # noqa: E402

CORE = {"contig": "ctgA", "start": 10000, "end": 20000, "identity": "S / ctgA / region001 / BGC001"}


def _gp(tag, start, end):
    return {"tag": tag, "contig": "ctgA", "start": start, "end": end, "strand": 1, "contig_len": 200000}


def _core(pid, locus):
    return {"status": "PRESENT_IN_CORE", "best_protein": pid, "best_locus": locus, "best_identity_pct": "70",
            "reciprocal_best": "True"}


PROTS = {"q1": _gp("a_1", 9500, 10500), "q2": _gp("a_2", 12000, 12900)}   # a_1: 50% inside the region
ROWS = [dict(_core("q1", "a_1"), name="abcA"), dict(_core("q2", "a_2"), name="abcB"),
        {"status": "MISSING_NOT_FOUND", "name": "abcC"}]


def test_crossing_gene_stays_in_the_core_and_is_named():
    c = M.count_summary(ROWS, edge={"a_1": 50})
    assert (c["core"], c["core_proteins"], c["core_crossing"]) == (2, 2, 1)
    assert c["core"] + c["clear"] + c["ambiguous"] + c["not_found"] + c["other"] == c["reference_genes"] == 3
    s = M.count_sentence(c)
    assert s.startswith("2 of 3 reference genes in the core, on 2 distinct proteins;")
    assert "1 of the 2 core genes crosses the region edge and lies partly outside it" in s


def test_without_edge_shares_nothing_changes():
    c = M.count_summary(ROWS)
    assert c["core_crossing"] == 0
    assert "region edge" not in M.count_sentence(c)


def test_gene_table_counts_and_caption_carry_the_crossing(tmp_path):
    T = pytest.importorskip("gap_rescue_gene_table")
    pytest.importorskip("Bio.SeqIO")
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqFeature import FeatureLocation, SeqFeature
    from Bio.SeqRecord import SeqRecord
    rec = SeqRecord(Seq("A" * 3000), id="REF1", name="REF1", description="test cluster",
                    annotations={"molecule_type": "DNA"})
    for i in range(3):
        rec.features.append(SeqFeature(FeatureLocation(i * 1000, i * 1000 + 900, strand=1), type="CDS",
                                       qualifiers={"gene": ["abc" + "ABC"[i]], "translation": ["M" * 290]}))
    gbk = tmp_path / "REF1.gbk"
    SeqIO.write(rec, str(gbk), "genbank")
    edge = T.edge_shares(ROWS, PROTS, CORE)
    assert edge == {"a_1": 50}
    res = T.write_gene_table(tmp_path, ROWS, [], CORE["identity"], "S", gbk, {}, "test", edge, render=False)
    got = next(csv.DictReader(open(tmp_path / "gene_table_counts.tsv"), delimiter="\t"))
    assert (got["core"], got["core_crossing"]) == ("2", "1")
    assert "1 of the 2 core genes crosses the region edge" in res["caption"]


def test_map_footnote_is_unchanged(tmp_path):
    pytest.importorskip("matplotlib")
    pytest.importorskip("gap_rescue_gene_table")
    pytest.importorskip("Bio.SeqIO")
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqFeature import FeatureLocation, SeqFeature
    from Bio.SeqRecord import SeqRecord
    rec = SeqRecord(Seq("A" * 3000), id="REF1", name="REF1", description="test cluster",
                    annotations={"molecule_type": "DNA"})
    for i in range(3):
        rec.features.append(SeqFeature(FeatureLocation(i * 1000, i * 1000 + 900, strand=1), type="CDS",
                                       qualifiers={"gene": ["abc" + "ABC"[i]], "translation": ["M" * 290]}))
    gbk = tmp_path / "REF1.gbk"
    SeqIO.write(rec, str(gbk), "genbank")
    res = M.draw_locus_map(gbk, ROWS, [], PROTS, [CORE], CORE, "S", "test", tmp_path / "m.png", tmp_path / "m.pdf")
    # The map draws the region boundary and keeps its counts sentence, so a redraw of a run made before this card
    # still agrees with that run's saved table; the crossing sentence lives in the gene table.
    assert res["footnote"].startswith("2 of 3 reference genes in S / ctgA / region001 / BGC001, on 2 distinct proteins;")
    assert "region edge" not in res["footnote"]


def test_crossing_sentence_comes_last():
    rows = ROWS + [{"status": "MISSING_FOUND_CLEAR", "best_protein": f"x{i}", "partner_verdict": "PARALOG_FAMILY"}
                   for i in range(3)]
    s = M.count_sentence(M.count_summary(rows, edge={"a_1": 50}))
    assert s.index("Of these, 3 were set aside") < s.index("1 of the 2 core genes crosses the region edge")
    assert s.endswith("lies partly outside it")
