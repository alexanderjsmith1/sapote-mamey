import pytest
from mamey.models import BGCRecord, CDSFeature
from mamey.source_scans import _bgc_overlap_or_near,bgc_coupling

def _gene(start,end=None,contig='CP000001.1'):
    return CDSFeature(contig,start,end or start,1,'gene','protein')

def test_wrapped_interval_and_flank_boundaries():
    b=BGCRecord('BGC001','CP000001.1',1,900,100,1000,validated_circular_span_bp=200)
    for pos in [1,100,901,1000]:assert _bgc_overlap_or_near(_gene(pos),b,0)
    for pos in [101,900,500]:assert not _bgc_overlap_or_near(_gene(pos),b,0)
    for pos in [110,891]:assert _bgc_overlap_or_near(_gene(pos),b,10)
    for pos in [111,890]:assert not _bgc_overlap_or_near(_gene(pos),b,10)
    assert _bgc_overlap_or_near(_gene(500),b,400)
    assert not _bgc_overlap_or_near(_gene(1,contig='other'),b,400)
    with pytest.raises(ValueError,match='CIRCULAR_NEGATIVE_FLANK'):_bgc_overlap_or_near(_gene(1),b,-1)

def test_wrapped_coupling_assigns_both_segments_only():
    b=BGCRecord('BGC001','CP000001.1',1,900,100,1000,validated_circular_span_bp=200)
    def hit(pos):return {'contig':b.contig,'start':pos,'end':pos,'locus_tag':'x','product':'protein'}
    assert bgc_coupling([b],{'hits':{'head':[hit(10)],'tail':[hit(990)],'outside':[hit(500)]}},flank=0)=={'BGC001':['head','tail']}

def test_linear_behavior_unchanged():
    b=BGCRecord('BGC001','CP000001.1',1,100,300,1000)
    assert _bgc_overlap_or_near(_gene(100),b,0)
    assert not _bgc_overlap_or_near(_gene(301),b,0)
