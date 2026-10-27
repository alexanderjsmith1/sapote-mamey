import pytest
from mamey.blastp_followup import parse_hit_table_csv
M10='45.2,310,160,4,1,300,12,318,1e-50,180'

@pytest.mark.parametrize('title',['synthetic, title','synthetic, second, title'])
def test_numeric_subject_does_not_become_identity(tmp_path,title):
    p=tmp_path/'hits.csv';p.write_text(title+',123456,'+M10+'\n')
    rows=parse_hit_table_csv(p)
    assert len(rows)==1
    r=rows[0]
    assert (r.query_id,r.subject_id,r.pct_identity,r.bitscore,r.pct_positive)==(title,'123456',45.2,180,None)

@pytest.mark.parametrize('positives',[False,True])
def test_plain_numeric_subject_keeps_supported_format(tmp_path,positives):
    p=tmp_path/'hits.csv';p.write_text('synthetic,123456,'+M10+(',61' if positives else '')+'\n')
    r=parse_hit_table_csv(p)[0]
    assert r.subject_id=='123456' and r.pct_identity==45.2 and r.bitscore==180
    assert r.pct_positive==(61 if positives else None)

def test_two_syntactically_valid_suffixes_need_a_header(tmp_path):
    # This tests layout ambiguity only, not biological alignment consistency.
    p=tmp_path/'hits.csv';p.write_text('synthetic,subject,30,20,10,2,2,19,20,37,45,8,90\n')
    with pytest.raises(ValueError,match='HIT_TABLE_LAYOUT_UNRESOLVED'):parse_hit_table_csv(p)

def test_corrupt_multi_fragment_title_cannot_create_a_shifted_hit(tmp_path):
    p=tmp_path/'hits.csv';p.write_text('synthetic,12,52.5,subject,45.2,310,160,4,1,300,12,318,1e-50,NA\n')
    with pytest.raises(ValueError,match='HIT_TABLE_LAYOUT_UNRESOLVED'):parse_hit_table_csv(p)
