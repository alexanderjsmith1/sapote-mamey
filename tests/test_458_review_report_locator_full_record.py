import pytest
from mamey.report_card import _locator

@pytest.mark.parametrize('record',['NODE_5_length_90000_cov_20.0','synthetic_scaffold_cov_distinct_suffix','chromosome_complete_identifier'])
def test_report_locator_preserves_the_full_record_identifier(record):
    assert _locator({'Contig':record,'antiSMASH_Region':'region007'})==record+' · region007'
