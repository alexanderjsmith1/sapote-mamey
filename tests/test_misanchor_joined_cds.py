"""Mis-anchor guard checks every segment of a joined CDS in a linear region.

Adapted from Codex Patch Series patch 24's test. Legacy results are pinned to the pre-patch output."""
from types import SimpleNamespace as NS
import pytest
from mamey import source_scans

def region(start=99, end=200, circular=None):
    return NS(bgc_id='BGC_TEST', contig='chr', start=start, end=end, contig_length=1000,
              validated_circular_span_bp=circular, kcb_top='', closest_candidate_kcb_product='gentamicin',
              products=['aminoglycoside'], ks_domain_count=0, ene_ks_count=0)

def gene(start, end, parts=(), contig='chr'):
    return NS(contig=contig, start=start, end=end, location_parts=parts, product='2-deoxy-scyllo-inosose synthase')

def result(g, b=None):
    return source_scans.scan_misanchor_guards([g], [b or region()])['per_bgc']['BGC_TEST']

def test_joined_segment_inside_region_is_not_lost():
    r = result(gene(700, 800, ((120, 130), (700, 800))))
    assert r['dois_present'] and not r['aminoglycoside_misanchor']

def test_gap_does_not_create_overlap():
    assert result(gene(10, 20, ((10, 20), (700, 800))))['aminoglycoside_misanchor']

# (gene, dois_present, aminoglycoside_misanchor) as the guard reported them before patch 24
@pytest.mark.parametrize('g,dois,mis', [
    (gene(100, 150), True, False), (gene(1, 98), False, True), (gene(200, 210), False, True),
    (gene(120, 130, ((120, 130),)), True, False), (gene(120, 130, contig='other'), False, True)])
def test_single_part_legacy_behavior_preserved(g, dois, mis):
    r = result(g)
    assert (r['dois_present'], r['aminoglycoside_misanchor']) == (dois, mis)
    assert r['aminoglycoside_anchor'] and not r['class_mismatch']

def test_circular_behavior_preserved():
    r = result(gene(950, 970, ((950, 970), (1, 20))), region(900, 100, 200))
    assert r['dois_present'] and not r['aminoglycoside_misanchor']
