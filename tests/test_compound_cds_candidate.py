from types import SimpleNamespace as NS
from pathlib import Path
import pytest
pytest.importorskip("Bio")
from Bio.SeqFeature import SeqFeature, SimpleLocation, CompoundLocation
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
import csv,json,hashlib
import pytest
from mamey import parsers
from mamey.models import CDSFeature,BGCRecord
from mamey.gene_context import build_gene_context,write_gene_context
from mamey.source_scans import _scan_patterns,bgc_coupling

CONTIG='CP000001.1'
def bgc(name,start,end,span=None):return BGCRecord(name,CONTIG,1,start,end,1000,validated_circular_span_bp=span)
def cds(parts):return CDSFeature(CONTIG,parts[0][0],parts[0][1],1,'joined','test resistance',translation='',nucleotide_seq='A'*sum(e-s+1 for s,e in parts),location_parts=tuple(parts))
def test_join_cds_attaches_each_segment_but_not_gap_and_length():
 c=cds([(1,10),(991,1000)]);bs=[bgc('BGC001',900,100,200),bgc('BGC002',990,1000),bgc('BGC003',0,10),bgc('BGC004',400,600)];result=build_gene_context(bs,[c]);assert set(result['bgcs'])=={'BGC001','BGC002','BGC003'}
 row=result['bgcs']['BGC001'][0];assert row['length_bp']==20 and row['location_parts']==[[1,10],[991,1000]] and row['coordinate_scope']=='longest_part' and row['aa_length']==5

def test_join_source_scan_hits_preserve_parts_for_coupling():
 c=cds([(1,10),(991,1000)]);h=_scan_patterns([c],{'marker':['resistance']});bs=[bgc('BGC001',990,1000),bgc('BGC002',400,600)];assert bgc_coupling(bs,h,flank=0)=={'BGC001':['marker']}

def test_parser_preserves_join_and_distinct_parts(monkeypatch):
 def f(x):return SeqFeature(CompoundLocation([SimpleLocation(a,b,strand=1) for a,b in x]),type='CDS',qualifiers={'locus_tag':['tag']})
 rec=SeqRecord(Seq('A'*1000),id=CONTIG,features=[f([(0,10),(990,1000)]),f([(0,10),(989,1000)])]);monkeypatch.setattr(parsers,'read_genbank_records',lambda *a,**kw:[('x.gbk',rec)]);monkeypatch.setattr(parsers,'_region_record_offsets',lambda *a:{})
 rows=parsers.extract_cds_features('fake.zip');assert len(rows)==2 and rows[0].location_parts==((1,10),(991,1000))

def test_parser_refuses_missing_segments_and_remote(monkeypatch):
 rec=NS(id=CONTIG,name=CONTIG,features=[NS(type='CDS',location=NS(start=0,end=10,strand=1))]);monkeypatch.setattr(parsers,'read_genbank_records',lambda *a,**kw:[('x',rec)]);monkeypatch.setattr(parsers,'_region_record_offsets',lambda *a:{})
 with pytest.raises(ValueError,match='CDS_LOCATION_SEGMENTS_UNAVAILABLE'):parsers.extract_cds_features('fake.zip')
 rec.features=[SeqFeature(SimpleLocation(0,10,ref='CP999999.1'),type='CDS')]
 with pytest.raises(ValueError,match='CDS_REMOTE_LOCATION_UNSUPPORTED'):parsers.extract_cds_features('fake.zip')

def test_writer_discloses_representative_coordinates_and_full_parts(tmp_path):
 b=bgc('BGC001',900,100,200);write_gene_context(tmp_path,'test',[b],[cds([(1,10),(991,1000)])]);rows=list(csv.DictReader((tmp_path/'test_cds_table.csv').open()));assert rows[0]['length_bp']=='20' and rows[0]['coordinate_scope']=='longest_part' and json.loads(rows[0]['location_parts_1based_inclusive'])==[[1,10],[991,1000]]

def test_real_graeca_origin_cds():
 root=__import__('os').environ.get('SAPOTE_TEST_REFERENCE_ROOT')
 if not root: pytest.skip('public Actinomadura graeca antiSMASH zip unavailable: set SAPOTE_TEST_REFERENCE_ROOT to a folder holding Actinomadura_graeca__CP059572__antiSMASH8.0.4_loose.zip')
 src=Path(root).expanduser()/'Actinomadura_graeca__CP059572__antiSMASH8.0.4_loose.zip'
 if not src.is_file(): pytest.skip('public Actinomadura graeca antiSMASH zip not found under SAPOTE_TEST_REFERENCE_ROOT')
 assert hashlib.sha256(src.read_bytes()).hexdigest()=='1b1632fce6d7d28d61987208652013e1e6f0373ae5af487424f116ad557dabc1';rows=parsers.extract_cds_features(src);c=next(x for x in rows if x.locus_tag=='AGRA3207_000001');assert c.location_parts==((8944623,8944773),(1,3704)) and len(c.nucleotide_seq)==3855
 b=BGCRecord('BGC001','CP059572.1',1,8895909,18704,8944773,validated_circular_span_bp=67568);r=build_gene_context([b],[c])['bgcs']['BGC001'][0];assert r['length_bp']==3855 and r['coordinate_scope']=='longest_part' and r['start']==1 and r['end']==3704

def test_shim_simple_location_supported_and_compound_refused():
    from mamey._gbk_shim import _parse_features
    simple=_parse_features("     CDS             complement(1..10)\n                     /locus_tag=\"x\"")[0]
    assert [(x.start,x.end) for x in simple.location.parts]==[(0,10)]
    joined=_parse_features("     CDS             join(991..1000,1..10)\n                     /locus_tag=\"y\"")[0]
    with pytest.raises(ValueError,match='GENBANK_LOCATION_SEGMENTS_UNAVAILABLE'): _=joined.location.parts

def test_linear_one_base_missing_translation_keeps_prior_unknown_length():
    b=bgc('BGC001',0,10); c=CDSFeature(CONTIG,1,1,1,'single','test');r=build_gene_context([b],[c])['bgcs']['BGC001'][0];assert r['aa_length'] is None
