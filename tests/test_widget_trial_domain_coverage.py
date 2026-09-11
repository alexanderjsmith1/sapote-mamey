import json
import pytest
from mamey import widget_deliverable as w

@pytest.mark.parametrize('sidecar,expected',[(None,'NOT_PROVIDED'),('bgc_id,PKS_KS\nr1,0\n','PARTIAL'),('bgc_id,PKS_KS\nr1,0\nr2,1\n','COMPLETE'),('bgc_id,PKS_KS\nr1,0\nr1,0\n','INCONSISTENT')])
def test_domain_coverage_reports_inventory_gaps(tmp_path,sidecar,expected):
    p=tmp_path/'package';p.mkdir()
    (p/'manifest.json').write_text(json.dumps({'strain_id':'TEST'}))
    (p/'TEST_2_inventory.csv').write_text('BGC_ID,Contig,Region\nr1,NODE_1_length_5000_cov_20,1\nr2,NODE_2_length_4000_cov_10,1\n')
    if sidecar is not None:(p/'TEST_perBGC_domain_heatmap_data.csv').write_text(sidecar)
    source=w.PackageSource(p)
    try:model=w._load_model(source)
    finally:source.close()
    coverage=model['domain_coverage']
    assert coverage['status']==expected
    assert coverage['inventory_rows']==2
    assert coverage['represented_inventory_rows'] + coverage['not_represented_rows']==2
    assert ('Domain sidecar coverage' in w._domains_page(model))
    if expected=='PARTIAL':
        assert coverage['represented_inventory_rows']==1
        assert len(model['domains'])==1 and model['domains'][0]['total']==0
    if expected=='INCONSISTENT':assert coverage['unmapped_rows']==0 and coverage['duplicate_rows']==1
