"""A CDS with joined segments (an origin-spanning or spliced annotation) gets gene context.

The overlap test for joined segments lives in the engine's source_scans.py. The package lifts it into
_gene_context.py; before that, any genome with such a CDS inside a region failed with ModuleNotFoundError.
"""
from types import SimpleNamespace

from rggmci._gene_context import build_gene_context


def _bgc(start=100, end=5000):
    return SimpleNamespace(bgc_id="BGC001", contig="c1", start=start, end=end, contig_length=10000)


def _cds(parts):
    return SimpleNamespace(contig="c1", start=parts[0][0], end=parts[-1][1], strand=1, locus_tag="g1",
                           product="test protein", translation="M" * 100, qualifiers={}, location_parts=parts)


def test_joined_cds_inside_region_is_assigned():
    context = build_gene_context([_bgc()], [_cds(((200, 400), (500, 900)))])
    assert context["n_cds"] == 1
    row = context["bgcs"]["BGC001"][0]
    assert row["location_parts"] == [[200, 400], [500, 900]]
    assert row["length_bp"] == 201 + 401


def test_joined_cds_outside_region_is_not_assigned():
    context = build_gene_context([_bgc(100, 1000)], [_cds(((6000, 6200), (6300, 6500)))])
    assert context["n_cds"] == 0
