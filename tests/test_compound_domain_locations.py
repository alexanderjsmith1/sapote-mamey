"""Compound (joined) domain locations: parts are kept and overlap is checked per segment.

Adapted from Codex Patch Series patch 11's test. Its real-archive case needs files outside the bundle and is not shipped."""
from types import SimpleNamespace as NS
from pathlib import Path
import pytest
pytest.importorskip("Bio")
from Bio.SeqFeature import SeqFeature, SimpleLocation, CompoundLocation
from mamey.models import DomainFeature
from mamey import parsers
from mamey.source_scans import _bgc_overlap_or_near, scan_domain_architecture

CONTIG='CP059572.1'
def bgc(name,start,end,length=1000,span=None):
    return NS(bgc_id=name,contig=CONTIG,start=start,end=end,contig_length=length,validated_circular_span_bp=span,node_id=None,antismash_region=None)
def feature(parts,domain='AMP-binding'):
    f=DomainFeature(CONTIG,min(a for a,b in parts),max(b for a,b in parts),1,'aSDomain','x',domain,'antiSMASH')
    f.location_parts=tuple(parts);return f

def test_origin_join_assigns_one_feature_to_wrapped_region_only():
    f=feature([(991,1000),(1,10)])
    bs=[bgc('wrap',900,100,span=200),bgc('middle',400,600),bgc('head',0,5),bgc('tail',995,1000)]
    result=scan_domain_architecture(bs,[f])['per_bgc']
    assert [len(result[b.bgc_id]['domains']) for b in bs]==[1,0,1,1]
    assert result['wrap']['domain_counts']['NRPS_A']==1

def test_join_with_internal_gap_does_not_fill_it():
    f=feature([(100,120),(200,220)])
    assert not _bgc_overlap_or_near(f,bgc('gap',140,160),flank=0)
    assert _bgc_overlap_or_near(f,bgc('left',110,115),flank=0)
    assert _bgc_overlap_or_near(f,bgc('right',210,215),flank=0)
    assert _bgc_overlap_or_near(f,bgc('gap',140,160),flank=25)

def test_parser_keeps_parts_and_distinguishes_same_bbox(monkeypatch):
    def loc(pairs):return CompoundLocation([SimpleLocation(a,b,strand=1) for a,b in pairs])
    features=[SeqFeature(loc([(0,10),(90,100)]),type='aSDomain',qualifiers={'aSDomain':['AMP-binding']}),SeqFeature(loc([(0,20),(80,100)]),type='aSDomain',qualifiers={'aSDomain':['AMP-binding']})]
    rec=NS(id=CONTIG,name=CONTIG,features=features)
    monkeypatch.setattr(parsers,'read_genbank_records',lambda *a,**kw:[('x.gbk',rec)])
    monkeypatch.setattr(parsers,'_region_record_offsets',lambda *a:{})
    rows=parsers.extract_domain_features('fake.zip');assert len(rows)==2
    assert rows[0].location_parts==((1,10),(91,100)) and rows[1].location_parts==((1,20),(81,100))

def test_parser_refuses_remote_segment(monkeypatch):
    f=SeqFeature(SimpleLocation(0,10,ref='CP999999.1'),type='aSDomain',qualifiers={'aSDomain':['AMP-binding']})
    rec=NS(id=CONTIG,name=CONTIG,features=[f]);monkeypatch.setattr(parsers,'read_genbank_records',lambda *a,**kw:[('x',rec)]);monkeypatch.setattr(parsers,'_region_record_offsets',lambda *a:{})
    with pytest.raises(ValueError,match='DOMAIN_REMOTE_LOCATION_UNSUPPORTED'):parsers.extract_domain_features('fake.zip')

def test_half_open_edges_do_not_touch():
    f=feature([(1,100),(201,300)])
    assert not _bgc_overlap_or_near(f,bgc('gap',100,200),0)
    assert _bgc_overlap_or_near(f,bgc('leftedge',99,100),0)
    assert _bgc_overlap_or_near(f,bgc('rightedge',200,201),0)

def test_parser_refuses_location_without_segments(monkeypatch):
    f=NS(type='aSDomain',location=NS(start=0,end=10,strand=1),qualifiers={})
    rec=NS(id=CONTIG,name=CONTIG,features=[f])
    monkeypatch.setattr(parsers,'read_genbank_records',lambda *a,**kw:[('x',rec)])
    monkeypatch.setattr(parsers,'_region_record_offsets',lambda *a:{})
    with pytest.raises(ValueError,match='DOMAIN_LOCATION_SEGMENTS_UNAVAILABLE'):
        parsers.extract_domain_features('fake.zip')
