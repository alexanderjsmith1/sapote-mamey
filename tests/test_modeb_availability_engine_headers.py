import csv
import pytest
from mamey.mode_b.availability import load_inventory

@pytest.mark.parametrize('node_key,region_key',[('Contig','Region'),('Contig','antiSMASH_Region'),('contig','region'),('full_node','region_id')])
def test_engine_and_normalized_identity_headers(tmp_path,node_key,region_key):
    path=tmp_path/'inventory.csv'
    row={'Strain':'TEST','BGC_ID':'BGC001',node_key:'NODE_1_length_5000_cov_20.5',region_key:'region001'}
    with path.open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    item=load_inventory(path)[0]
    assert item.full_node=='NODE_1_LENGTH_5000_COV_20.5'
    assert item.region=='region001'

def test_missing_locator_remains_unresolved(tmp_path):
    path=tmp_path/'inventory.csv';path.write_text('Strain,BGC_ID\nTEST,BGC001\n')
    item=load_inventory(path)[0]
    assert item.full_node=='' and item.region==''
