import importlib.util
from pathlib import Path
import pytest
SPEC=importlib.util.spec_from_file_location('bioassay_overlay', Path(__file__).resolve().parents[1]/'tools/build_placement_ggtree_inputs.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

@pytest.mark.parametrize('rows,code', [
 ('SYNTHETIC_REFERENCE_01,positive,negative\nSYNTHETIC_REFERENCE_01,negative,negative\n','BIOASSAY_METADATA_CONFLICT'),
 ('SYNTHETIC_REFERENCE_01,positive,negative\nSYNTHETIC_REFERENCE_01,positive,negative\n','BIOASSAY_METADATA_DUPLICATE'),
 ('SYNTHETIC_REFERENCE_01,synthetic_invalid_state,negative\n','BIOASSAY_METADATA_VALUE'),
 ('SYNTHETIC_REFERENCE_01,not tested,negative\n','BIOASSAY_METADATA_VALUE'),
 (',positive,negative\n','BIOASSAY_METADATA_IDENTITY'),
])
def test_invalid_or_ambiguous_rows_refuse(tmp_path, rows, code):
 p=tmp_path/'data.csv';p.write_text('strain,anti_Candida,anti_MRSA\n'+rows)
 with pytest.raises(ValueError,match=code):M._load_bioassay(p)

def test_explicit_not_tested_stays_distinct_from_blank(tmp_path):
 p=tmp_path/'data.csv';p.write_text('strain,anti_Candida,anti_MRSA\nSYNTHETIC_REFERENCE_01,not_tested,\n')
 assert M._load_bioassay(p)['SYNTHETIC_REFERENCE_01']=={'anti_candida':'not_tested','anti_mrsa':''}


@pytest.mark.parametrize('data', [
 'strain,anti_Candida,anti_MRSA,ANTI_MRSA\nAS-9001,positive,negative,positive\n',
 'strain,anti_Candida,anti_MRSA\nAS-9001,positive\n',
 'strain,anti_Candida,anti_MRSA\nAS-9001,positive,negative,unexpected\n',
])
def test_ambiguous_or_ragged_schema_refuses(tmp_path, data):
 p=tmp_path/'data.csv';p.write_text(data)
 with pytest.raises(ValueError, match='BIOASSAY_METADATA_SCHEMA'): M._load_bioassay(p)
