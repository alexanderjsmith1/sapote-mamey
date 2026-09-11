"""test_gene_context_scoping.py — regression coverage for the v9.7.105 closed-genome
gene-context scoping fix (extract_cds_features).

Two failure modes are pinned:
  (1) Per-region GBKs carry REGION-LOCAL coordinates; mixing them into the genome-wide CDS
      inventory duplicates every CDS at a shifted frame. Fix: build the inventory from the
      full-assembly GBK(s) only (exclude_regions).
  (2) Origin-spanning genes on a circular chromosome have a compound join() location whose
      naive min..max span brackets the whole contig and false-overlaps every region. Fix: use
      the dominant (longest) part as the representative coordinates.

The fixtures are built in-memory with BioPython and zipped, so the test is self-contained.
"""
import io
import zipfile
import pytest

SeqIO = pytest.importorskip("Bio.SeqIO")
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.SeqFeature import SeqFeature, FeatureLocation, CompoundLocation

from mamey.parsers import extract_cds_features


def _cds(start, end, strand, locus, seqlen):
    f = SeqFeature(FeatureLocation(start, end, strand=strand), type="CDS")
    f.qualifiers["locus_tag"] = [locus]
    f.qualifiers["translation"] = ["M" * (((end - start) // 3) - 1)]
    return f


def _make_zip(tmp_path):
    """Full-assembly GBK (global coords, incl. an origin-spanning gene) + a region GBK
    (region-LOCAL coords for the same normal gene) — the closed-genome failure setup."""
    L = 10000
    seq = Seq("ATGC" * (L // 4))

    full = SeqRecord(seq, id="CHR1", name="CHR1", annotations={"molecule_type": "DNA",
                                                               "topology": "circular"})
    # normal gene at global 2000-2300
    full.features.append(_cds(2000, 2300, 1, "G_NORMAL", L))
    # origin-spanning gene: join(9500..10000, 0..200)  → BioPython min..max = 0..10000
    span = CompoundLocation([FeatureLocation(9500, L, strand=1),
                             FeatureLocation(0, 200, strand=1)])
    of = SeqFeature(span, type="CDS")
    of.qualifiers["locus_tag"] = ["G_ORIGIN"]
    of.qualifiers["translation"] = ["M" * 232]
    full.features.append(of)

    # region GBK: the SAME normal gene, but at region-LOCAL coords (shifted) → frame-mixing
    region = SeqRecord(seq[:3000], id="CHR1", name="CHR1",
                       annotations={"molecule_type": "DNA"})
    region.features.append(_cds(500, 800, 1, "G_NORMAL", 3000))  # local frame, different coords

    zp = tmp_path / "as.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        b = io.StringIO(); SeqIO.write(full, b, "genbank")
        zf.writestr("CHR1.gbk", b.getvalue())
        b = io.StringIO(); SeqIO.write(region, b, "genbank")
        zf.writestr("CHR1.region001.gbk", b.getvalue())
    return str(zp)


def test_region_local_frame_not_mixed(tmp_path):
    cds = extract_cds_features(_make_zip(tmp_path))
    by_locus = {}
    for c in cds:
        by_locus.setdefault(c.locus_tag, []).append(c)
    # G_NORMAL must appear exactly once (region-local copy excluded), at its GLOBAL coords
    assert "G_NORMAL" in by_locus
    assert len(by_locus["G_NORMAL"]) == 1, "region-local duplicate leaked into the inventory"
    g = by_locus["G_NORMAL"][0]
    assert (g.start, g.end) == (2001, 2300), "kept the wrong (region-local) coordinate frame"


def test_origin_spanning_uses_dominant_part(tmp_path):
    cds = extract_cds_features(_make_zip(tmp_path))
    origin = [c for c in cds if c.locus_tag == "G_ORIGIN"]
    assert origin, "origin-spanning gene dropped entirely"
    o = origin[0]
    # dominant part is 9500..10000 (len 500) — NOT the whole-contig 1..10000 span
    assert (o.end - o.start) < 1000, "origin-spanning gene still brackets the whole contig"
    assert o.start >= 9000, "did not select the dominant part"


def test_no_whole_contig_cds(tmp_path):
    cds = extract_cds_features(_make_zip(tmp_path))
    assert not any((c.end - c.start) > 5000 for c in cds), "a whole-contig CDS leaked through"
