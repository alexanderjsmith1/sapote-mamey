import copy, csv, json, xml.etree.ElementTree as ET
import pytest
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('bee_main_figures',Path(__file__).resolve().parents[1]/'tools'/'bee_review_main_set.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def fixture():
    owners=[dict(strain='DEMO-'+str(i),host_raw='Bombus sp.',Candida='positive',MRSA='not_tested',source_row=i+2,source_sha256='a'*64) for i in range(2)]
    rows=[dict(binding=dict(strain=o['strain'],package_variant='DEMO-variant'),assay=o,comparison=dict(disposition='REVIEW_CANDIDATE',genome_input_sha256='b'*64,product_counts={'NRPS':i+1}),chitin=dict({f:i for f in module.FAMILIES},input_sha256='b'*64,receipt_sha256='c'*64),boundary_counts={'Interior':1,'Edge':i,'Full-contig':0},pks_boundary_counts={} if i==0 else {'Interior':1,'Edge':0}) for i,o in enumerate(owners)]
    rows[0]['comparison']['disposition']='ASSEMBLY_VARIANT_NOT_INDEPENDENT_STRAIN'
    rows[0]['representative_selection']={'authorized_by':'user','selected_variant':'DEMO-variant'}
    return dict(selected=rows,bee_owner_rows=owners,excluded_packages=[{'strain':'DEMO-0','reason':'VARIANT'}],references=[{'name':'Example species type reference','product_counts':{'NRPS':2}}])

def test_authorized_variant(): assert len(module.validate(fixture()))==2

@pytest.mark.parametrize('mutation,code',[
    ('duplicate','EMPTY_OR_DUPLICATE_GENOME_STRAINS'),('wasp','NON_BEE_OWNER_RECORD'),
    ('hold','GENOME_HOLD_NOT_CLEARED'),('unauthorized','GENOME_HOLD_NOT_CLEARED'),
    ('wrong_variant','GENOME_HOLD_NOT_CLEARED'),('content','GENOME_CONTENT_MISMATCH'),
    ('negative','INVALID_FAMILY_COUNT')])
def test_refusals(mutation,code):
    d=copy.deepcopy(fixture()); r=d['selected'][0]
    if mutation=='duplicate': d['selected'].append(r)
    if mutation=='wasp': d['bee_owner_rows'][0]['host_raw']='Wasp'
    if mutation=='hold': r['comparison']['disposition']='QC_HOLD_AUDIT_ONLY'
    if mutation=='unauthorized': r['representative_selection']['authorized_by']='inferred'
    if mutation=='wrong_variant': r['representative_selection']['selected_variant']='another'
    if mutation=='content': r['chitin']['input_sha256']='d'*64
    if mutation=='negative': r['chitin'][module.FAMILIES[0]]=-1
    with pytest.raises(ValueError,match=code): module.validate(d)

def test_render_and_regressions(tmp_path):
    p=tmp_path/'input.json';p.write_text(json.dumps(fixture()));out=tmp_path/'out'
    figures=module.render(p,out);assert len(figures)==7
    for f in figures:
        root=ET.parse(out/f['svg']).getroot()
        assert not any(x.tag.endswith('image') for x in root.iter())
        assert any(x.tag.endswith('text') for x in root.iter())
        assert f['minimum_font_pt']>=8 and f['width_inches']==7.2
    rates=list(csv.DictReader((out/'BEE-P06_data.csv').open()))
    assert rates[0]['strict_edge_pct']=='' and rates[0]['rate_state']=='NOT_ESTIMABLE'
    assert rates[1]['strict_edge_pct']=='0.0' and rates[1]['rate_state']=='ESTIMABLE'
    coverage=list(csv.DictReader((out/'BEE-P04_data.csv').open()))
    assert sum(int(r['isolates']) for r in coverage)==2
    assert sum(int(r['isolates']) for r in coverage if r['coverage']=='Genome held')==0
    with pytest.raises(ValueError,match='OUTPUT_ALREADY_EXISTS'): module.render(p,out)
