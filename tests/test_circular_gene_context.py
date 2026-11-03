from types import SimpleNamespace as NS
from mamey.models import BGCRecord
from mamey.gene_context import build_gene_context

def test_wrap_region_assigns_both_sides_and_preserves_boundary_conventions():
    b=BGCRecord('BGC001','CP000001.1',1,900,100,1000,validated_circular_span_bp=200)
    cs=[NS(contig=b.contig,start=a,end=z,locus_tag=tag,strand=1,translation='',nucleotide_seq='',product='',qualifiers={}) for tag,a,z in [('first',1,1),('end',100,100),('outside_left',101,101),('outside_right',900,900),('tail',901,901),('last',1000,1000)]]
    observed={x['locus_tag'] for x in build_gene_context([b],cs)['bgcs']['BGC001']}
    assert observed=={'first','end','tail','last'}

def test_linear_region_keeps_legacy_overlap():
    b=BGCRecord('BGC001','CP000001.1',1,100,300,1000)
    cs=[NS(contig=b.contig,start=a,end=z,locus_tag=tag,strand=1,translation='',nucleotide_seq='',product='',qualifiers={}) for tag,a,z in [('before',1,50),('inside',150,160),('after',350,360)]]
    assert {x['locus_tag'] for x in build_gene_context([b],cs)['bgcs']['BGC001']}=={'inside'}
