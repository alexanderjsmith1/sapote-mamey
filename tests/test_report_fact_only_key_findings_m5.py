"""Fact-only key findings retain exclusions and distinguish zero from missing."""
import csv
import pytest
from mamey.compile_report import _key_findings


def write(pkg, rows):
    fields=['BGC_ID','Contig','antiSMASH_Region','Corrected_rank','Standing_rule','Primary_metab_flag','KCB_score','KCB_top','Products']
    with (pkg/'SYNTHETIC_4_triage_board.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)


def row(score='0', **changes):
    r=dict(BGC_ID='BGC001',Contig='SYNTHETIC_FULL.1',antiSMASH_Region='region001',Corrected_rank='1',KCB_score=score,KCB_top='sentinel-comparator',Products='NRPS')
    r.update(changes);return r


@pytest.mark.parametrize('changes',[{'Corrected_rank':''},{'Standing_rule':'saccharide'},{'Primary_metab_flag':'1'}])
def test_all_excluded_records_are_not_restored_as_leads(tmp_path,changes):
    write(tmp_path,[row('10',**changes)])
    text=_key_findings(tmp_path,{})
    assert 'No BGCs are eligible' in text and 'sentinel-comparator' not in text
    assert 'BGC001' not in text
    assert 'BGC001' in (tmp_path/'SYNTHETIC_4_triage_board.csv').read_text()


def test_zero_score_is_an_observation_not_novelty_or_priority(tmp_path):
    write(tmp_path,[row()]);text=_key_findings(tmp_path,{})
    assert '1 low/zero-KCB BGC(s)' in text and 'recorded KCB score is zero' in text
    assert 'no protein-level MIBiG comparator' not in text and 'highest discovery value' not in text
    assert 'does not establish an absent comparator, chemical novelty or experimental priority' in text


@pytest.mark.parametrize('value',['','not-a-number','NaN','inf','-inf','-1'])
def test_missing_malformed_nonfinite_and_negative_scores_are_unresolved(tmp_path,value):
    write(tmp_path,[row(value)]);text=_key_findings(tmp_path,{})
    assert 'KCB_SCORE_INPUT_INVALID: 1 row(s)' in text
    assert 'low/zero-KCB' not in text
