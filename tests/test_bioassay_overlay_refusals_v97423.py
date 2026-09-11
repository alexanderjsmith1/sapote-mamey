import importlib.util
from pathlib import Path
import pytest
SPEC=importlib.util.spec_from_file_location('bioassay_overlay', Path(__file__).resolve().parents[1]/'tools/build_placement_ggtree_inputs.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

@pytest.mark.parametrize('rows,code', [
 ('AS-9001,positive,negative\nAS-9001,negative,positive\n','BIOASSAY_METADATA_CONFLICT'),
 ('AS-9001,positive,negative\nAS-9001,positive,negative\n','BIOASSAY_METADATA_DUPLICATE'),
 ('AS-9001,posiitve,negative\n','BIOASSAY_METADATA_VALUE'),
 ('AS-9001,0.5,negative\n','BIOASSAY_METADATA_VALUE'),
 (',positive,negative\n','BIOASSAY_METADATA_IDENTITY'),
])
def test_invalid_or_ambiguous_rows_refuse(tmp_path, rows, code):
 p=tmp_path/'data.csv';p.write_text('strain,anti_Candida,anti_MRSA\n'+rows)
 with pytest.raises(ValueError,match=code):M._load_bioassay(p)

def test_explicit_not_tested_stays_distinct_from_blank(tmp_path):
 p=tmp_path/'data.csv';p.write_text('strain,anti_Candida,anti_MRSA\nAS-9001,not_tested,\n')
 assert M._load_bioassay(p)['AS-9001']=={'anti_candida':'not_tested','anti_mrsa':''}


@pytest.mark.parametrize('data', [
 'strain,anti_Candida,anti_MRSA,ANTI_MRSA\nAS-9001,positive,negative,positive\n',
 'strain,anti_Candida,anti_MRSA\nAS-9001,positive\n',
 'strain,anti_Candida,anti_MRSA\nAS-9001,positive,negative,unexpected\n',
])
def test_ambiguous_or_ragged_schema_refuses(tmp_path, data):
 p=tmp_path/'data.csv';p.write_text(data)
 with pytest.raises(ValueError, match='BIOASSAY_METADATA_SCHEMA'): M._load_bioassay(p)
