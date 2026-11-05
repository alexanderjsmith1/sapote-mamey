"""The split detector finds a contig terminus from antiSMASH's own edge record.

A region GBK is a slice of its contig. The detector measured distance to the slice ends, so a
PKS gene near the end of an interior region looked like it ran off the contig. On a complete
Amycolatopsis chromosome two regions 4.5 and 4.7 Mb from the contig end were flagged. It now
needs /contig_edge="True" on the region feature, and uses "Orig. start" to tell which end.
"""
from pathlib import Path

import pytest

pytest.importorskip("Bio")

from Bio.Seq import Seq  # noqa: E402
from Bio.SeqFeature import FeatureLocation, SeqFeature  # noqa: E402
from Bio.SeqRecord import SeqRecord  # noqa: E402
from Bio import SeqIO  # noqa: E402

from mamey import split_detector as sd  # noqa: E402


def _region_gbk(path: Path, *, contig_edge, orig_start, length=20000):
    rec = SeqRecord(Seq("A" * length), id="CTG1", name="CTG1", description="slice")
    rec.annotations["molecule_type"] = "DNA"
    rec.annotations["structured_comment"] = {"antiSMASH-Data": {
        "Version": "8.0.4", "Orig. start": str(orig_start), "Orig. end": str(orig_start + length)}}
    region_q = {"product": ["T1PKS"]}
    if contig_edge is not None:
        region_q["contig_edge"] = ["True" if contig_edge else "False"]
    rec.features.append(SeqFeature(FeatureLocation(0, length), type="region", qualifiers=region_q))
    # one KS gene that ends 500 bp before the slice end
    rec.features.append(SeqFeature(FeatureLocation(length - 4500, length - 500, strand=1), type="CDS",
                                   qualifiers={"locus_tag": ["CTG1_1"], "sec_met_domain": ["PKS_KS (E-value: 1e-100)"],
                                               "translation": ["M" * 1300]}))
    SeqIO.write([rec], str(path), "genbank")
    return path


def test_interior_region_is_not_a_terminus(tmp_path):
    p = sd._profile(_region_gbk(tmp_path / "a.region016.gbk", contig_edge=False, orig_start=1705188))
    assert p["contig_edge"] is False and p["orig_start"] == 1705188
    assert sd._terminal_pks_gene(p) is None


def test_edge_region_at_contig_end_is_a_terminus(tmp_path):
    p = sd._profile(_region_gbk(tmp_path / "b.region001.gbk", contig_edge=True, orig_start=80000))
    term = sd._terminal_pks_gene(p)
    assert term is not None and term["which"] == "end"


def _start_gene_profile(tmp_path, orig_start):
    p = sd._profile(_region_gbk(tmp_path / f"c{orig_start}.region001.gbk", contig_edge=True, orig_start=orig_start))
    g = p["bio"][0]
    g["s"], g["e"] = 200, 4200   # KS gene 200 bp after the slice start
    return p


def test_slice_start_counts_only_when_the_region_starts_at_base_zero(tmp_path):
    assert sd._terminal_pks_gene(_start_gene_profile(tmp_path, 0))["which"] == "start"
    assert sd._terminal_pks_gene(_start_gene_profile(tmp_path, 52000)) is None


def test_whole_contig_region_keeps_its_end_terminus(tmp_path):
    # A 20 kb contig that is all one region: both ends are contig edges.
    p = sd._profile(_region_gbk(tmp_path / "w.region001.gbk", contig_edge=True, orig_start=0))
    assert sd._terminal_pks_gene(p)["which"] == "end"


def test_gbk_without_edge_record_keeps_slice_rule(tmp_path):
    p = sd._profile(_region_gbk(tmp_path / "d.region001.gbk", contig_edge=None, orig_start=0))
    assert p["contig_edge"] is None
    assert sd._terminal_pks_gene(p)["which"] == "end"
