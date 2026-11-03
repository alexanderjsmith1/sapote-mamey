from mamey.models import BGCRecord, CDSFeature, DomainFeature
from mamey.source_scans import scan_domain_architecture, scan_orphan_megasynthase_motifs, scan_misanchor_guards

def _bgc():
    return BGCRecord('BGC001','CP000001.1',1,90000,10000,100000,products=['NRPS'],edge_status='Interior',closest_candidate_kcb_product='kanamycin',validated_circular_span_bp=20000)

def _cds(tag,start,product='hypothetical protein'):
    return CDSFeature('CP000001.1',start,start+5,1,tag,product,translation='M'+'A'*250+'DTACSSS')

def test_orphan_scan_excludes_wrap_and_both_flanks():
    x=[_cds('head',10),_cds('tail',99990),_cds('flankhead',15000),_cds('flanktail',85000),_cds('outside',50000)]
    found=scan_orphan_megasynthase_motifs(x,[_bgc()]);assert {x['locus_tag'] for x in found['ks_bearing']}=={'outside'}

def test_domain_architecture_assigns_both_wrap_segments():
    ds=[DomainFeature('CP000001.1',x,x+2,1,'aSDomain',tag,'PKS_KS','antiSMASH') for tag,x in [('head',100),('tail',99000),('outside',50000)]]
    per=scan_domain_architecture([_bgc()],ds)['per_bgc']['BGC001'];assert per['domain_counts']['PKS_KS']==2

def test_misanchor_guard_sees_annotation_on_wrapped_segment():
    result=scan_misanchor_guards([_cds('dois',100,'2-deoxy-scyllo-inosose synthase')],[_bgc()])['per_bgc']['BGC001']
    assert result['aminoglycoside_anchor'] and result['dois_present'] and not result['aminoglycoside_misanchor']
