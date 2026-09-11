import pytest
from mamey import widget_deliverable as w


@pytest.mark.parametrize('field',['AB_auto','AF_auto','Novelty_auto','Length_kb','KCB_score'])
@pytest.mark.parametrize('value',['bad','NaN','Infinity'])
def test_priority_invalid_present_number_refused(field,value):
    with pytest.raises(ValueError,match='WIDGET_NUMBER_INVALID'):
        w._join_rows([{field:value}],[])


@pytest.mark.parametrize('field',['Corrected_rank','KCB_proteins'])
@pytest.mark.parametrize('value',['bad','NaN','Infinity','2.5'])
def test_priority_invalid_present_integer_refused(field,value):
    with pytest.raises(ValueError,match='WIDGET_INTEGER_INVALID'):
        w._join_rows([{field:value}],[])


def test_valid_numeric_zero_and_fraction_preserved():
    row=w._join_rows([{'AB_auto':'0','Length_kb':'12.5','KCB_proteins':'2.0'}],[])[0]
    assert row['ab']==0 and row['length_kb']==12.5 and row['kcb_proteins']==2


@pytest.mark.parametrize('value',[None,'','  '])
def test_missing_kcb_measurements_remain_unreported(value):
    row=w._join_rows([{'KCB_score':value,'KCB_proteins':value}],[])[0]
    assert row['kcb_score'] is None and row['kcb_proteins'] is None


def test_kcb_measured_zero_is_preserved():
    row=w._join_rows([{'KCB_score':'0','KCB_proteins':'0'}],[])[0]
    assert row['kcb_score']==0 and row['kcb_proteins']==0
