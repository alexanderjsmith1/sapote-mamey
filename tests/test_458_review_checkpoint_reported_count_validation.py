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

@pytest.mark.parametrize('count',[-1,True,'23',None])
def test_invalid_reported_count_stays_unknown(checkpoint,count):
    checkpoint.inbox();source=next(x for x in checkpoint.rows if x['kind']=='inbox');path=Path(source['path']);data=json.loads(path.read_text());data['open_unique_id_count']=count;path.write_text(json.dumps(data));source['sha256']=fx.m.digest(path)
    result=checkpoint.runcheck();inbox=result['inbox']
    assert inbox['current_open_count'] is None and inbox['state']=='REFRESH_REQUIRED'
    assert inbox['count_state']=='INVALID_OR_MISSING_REPORTED_COUNT'
    assert inbox['reported_open_count']==count and inbox['native_check']['status']=='FAIL'
    assert 'Current pending count: **unknown**' in fx.m.markdown(result)

@pytest.mark.parametrize('count',[0,23])
def test_valid_integer_count_remains_a_reported_byte_bound_fact(checkpoint,count):
    checkpoint.inbox();source=next(x for x in checkpoint.rows if x['kind']=='inbox');path=Path(source['path']);data=json.loads(path.read_text());data['open_unique_id_count']=count;path.write_text(json.dumps(data));source['sha256']=fx.m.digest(path)
    result=checkpoint.runcheck();assert result['inbox']['current_open_count']==count
    assert result['inbox']['state']=='CURRENT_SNAPSHOT'
    assert result['inbox']['native_check']['status']=='FAIL'
