import pytest
import pandas as pd
from mamey.strain_modeb import _identity_index


def test_native_triage_identity():
    row={"BGC_ID":"BGC001","Contig":"NODE_1_length_12345_cov_20.5","Node_ID":"NODE_1_length_12345_cov_20","Region":1,"antiSMASH_Region":"region001"}
    result=_identity_index("TEST-01",pd.DataFrame([row]))
    assert result["BGC001"]=="TEST-01 / NODE_1_length_12345_cov_20.5 / region001 / BGC001"


@pytest.mark.parametrize("change",[{"Node_ID":"NODE_2"},{"Region":2},{"Contig":""},{"Full_Node_ID":"NODE_2_length_12345_cov_20.5"}])
def test_native_triage_conflict_refusal(change):
    row={"BGC_ID":"BGC001","Contig":"NODE_1_length_12345_cov_20.5","Node_ID":"NODE_1_length_12345_cov_20","Region":1,"antiSMASH_Region":"region001"}
    row.update(change)
    with pytest.raises(ValueError):_identity_index("TEST-01",pd.DataFrame([row]))
