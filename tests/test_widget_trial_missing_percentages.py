import pytest
from mamey import widget_deliverable as w

@pytest.mark.parametrize('value',[None,'','  '])
def test_missing_blast_percentages_are_not_zero(value):
    hit=w._top_blastp_hit(dict.fromkeys(['pct_identity','pct_positives','query_coverage'],value))
    assert all(hit[k] is None for k in ['pct_identity','pct_positives','query_coverage'])

@pytest.mark.parametrize('value',['0','75.5'])
def test_reported_blast_percentages_preserved(value):
    assert w._top_blastp_hit({'pct_identity':value})['pct_identity']==float(value)

@pytest.mark.parametrize('channel',['mibig','clusterblast'])
def test_missing_comparator_percentages_remain_missing(channel):
    kwargs=dict(strain='TEST',genes=[{'bgc_id':'region_alias','locus_tag':'gene1','aa_length':'20'}],inventory=[],mibig=[],clusterblast=[],blastp_batches={})
    kwargs[channel]=[{'bgc_id':'region_alias','query_gene':'gene1','pct_identity':'','pct_coverage':''}]
    rows,_=w._gene_evidence_rows(**kwargs)
    hit=rows[0][channel+'_hits'][0]
    assert hit['pct_identity'] is None and hit['pct_coverage'] is None

@pytest.mark.parametrize('value',['nan','inf','not-a-number'])
def test_malformed_percentage_is_diagnostic(value):
    with pytest.raises(ValueError,match='WIDGET_PERCENTAGE_INVALID'):
        w._top_blastp_hit({'pct_identity':value})
