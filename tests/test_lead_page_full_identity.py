import csv
from pathlib import Path
import pytest
from mamey import lead_pages as lead

def package(tmp_path, change=None):
    p=tmp_path/'package';p.mkdir()
    row={'BGC_ID':'r1','Contig':'NODE_1_length_5000_cov_20.5','Node_ID':'NODE_1','Region':'1','antiSMASH_Region':'region001','Strain':'TEST','Products':'NRPS'}
    if change=='missing_contig':row['Contig']=''
    if change=='missing_region':row['Region']=row['antiSMASH_Region']=''
    inventory=[row,dict(row)] if change=='duplicate' else [row]
    tri=dict(row,Lead_tier_auto='Medium')
    if change=='conflict':tri['Contig']='other'
    for suffix,rows in [('_2_inventory.csv',inventory),('_4_triage_board.csv',[tri])]:
        with (p/('TEST'+suffix)).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    lead._clear_cache()
    return str(p)

def test_lead_identity_in_content_filename_and_index(tmp_path):
    output,_,index=lead.build(package(tmp_path),'r1',str(tmp_path/'out'))
    text=Path(output).read_text();full='TEST / NODE_1_length_5000_cov_20.5 / region001 / r1'
    assert text.startswith('# '+full+' —')
    assert '**Locus:** '+full in text
    assert 'TEST_NODE_1_length_5000_cov_20.5_region001_r1_LEAD.md'==Path(output).name
    assert index['full_identity']==full

@pytest.mark.parametrize('change',['missing_contig','missing_region','duplicate','conflict'])
def test_lead_identity_refuses_missing_or_conflicting_sources(tmp_path,change):
    with pytest.raises(ValueError,match='LEAD_IDENTITY_'):
        lead.build(package(tmp_path,change),'r1',str(tmp_path/'out'))
    assert not list((tmp_path/'out').glob('*.md'))
