from pathlib import Path
import importlib.util
import json
import os
import pytest
ROOT=Path(os.environ.get('CHECKPOINT_REVIEW_BASE',Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('checkpoint_edge_fixture',ROOT/'tests/test_checkpoint_status.py')
fx=importlib.util.module_from_spec(spec);spec.loader.exec_module(fx)
@pytest.fixture
def checkpoint():
    value=fx.Check();value.setUp();value.goal()
    try:yield value
    finally:value.tearDown()

@pytest.mark.parametrize('kind',['inbox','allocation'])
@pytest.mark.parametrize('age_limit',[float('nan'),float('inf')])
def test_nonfinite_age_policy_cannot_make_old_evidence_current(checkpoint,kind,age_limit):
    old=(checkpoint.now-fx.dt.timedelta(days=1)).isoformat()
    if kind=='inbox':checkpoint.inbox(old)
    else:checkpoint.allocation(observed_at=old)
    manifest=checkpoint.manifest();manifest['max_'+kind+'_age_minutes']=age_limit
    with pytest.raises(ValueError,match='FINITE_NONNEGATIVE_AGE_BOUND_REQUIRED'):
        fx.m.build(manifest,checkpoint.p,checkpoint.now,checkpoint.p)

@pytest.mark.parametrize('kind',['inbox','allocation'])
def test_zero_age_bound_keeps_exact_timestamp_control(checkpoint,kind):
    if kind=='inbox':checkpoint.inbox()
    else:checkpoint.allocation()
    manifest=checkpoint.manifest();manifest['max_'+kind+'_age_minutes']=0
    result=fx.m.build(manifest,checkpoint.p,checkpoint.now,checkpoint.p)
    if kind=='inbox':assert result['inbox']['current_open_count']==23
    else:assert result['resources']['allocated_cores']==2
