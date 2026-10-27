import csv
import pytest
from mamey.blastp_followup import parse_hit_table_csv
HEADER=['qseqid','sseqid','pident','length','mismatch','gapopen','qstart','qend','sstart','send','evalue','bitscore']
BASE=['synthetic_query','synthetic_subject','45.2','310','160','4','1','300','12','318','1e-50','180']

@pytest.mark.parametrize('column',[2,11])
@pytest.mark.parametrize('value',['nan','NaN','inf','-inf'])
def test_nonfinite_identity_or_bitscore_is_not_a_hit(tmp_path,column,value):
    row=BASE.copy();row[column]=value;p=tmp_path/'hits.csv'
    with p.open('w',newline='') as f:w=csv.writer(f);w.writerow(HEADER);w.writerow(row)
    assert parse_hit_table_csv(p)==[]

@pytest.mark.parametrize('column',[2,11])
def test_headerless_nonfinite_is_not_a_hit(tmp_path,column):
    row=BASE.copy();row[column]='nan';p=tmp_path/'hits.csv';p.write_text(','.join(row)+'\n')
    assert parse_hit_table_csv(p)==[]

@pytest.mark.parametrize('value',['0','45.2'])
def test_finite_values_including_zero_are_preserved(tmp_path,value):
    row=BASE.copy();row[2]=value;row[11]='0';p=tmp_path/'hits.csv'
    with p.open('w',newline='') as f:w=csv.writer(f);w.writerow(HEADER);w.writerow(row)
    result=parse_hit_table_csv(p)
    assert len(result)==1 and result[0].pct_identity==float(value) and result[0].bitscore==0
