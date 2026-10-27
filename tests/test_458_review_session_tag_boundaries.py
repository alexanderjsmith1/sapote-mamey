"""Session-tag boundary and immutable-allowlist checks; no renderer execution."""
from pathlib import Path
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('session_tag_review_guard',ROOT/'tests/test_448_no_owner_or_lane_names_in_shipped_text.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
IDS=['018c'+'0f08','7288'+'f3e5','8e93'+'0c18']
@pytest.mark.parametrize('token',IDS)
@pytest.mark.parametrize('prefix',['','card_'])
def test_underscore_tag_detected(token,prefix):
    assert guard.PATTERNS['session id'].search(prefix+token+'_458_example')
def test_prior_id_underscore_tag_detected():
    assert guard.PATTERNS['session id'].search('88fd'+'ad06'+'_441')
@pytest.mark.parametrize('token',IDS)
@pytest.mark.parametrize('context',['bare','long_hash','identifier','unicode'])
def test_boundary_controls(token,context):
    text={'bare':'('+token+')','long_hash':token+'a'*56,'identifier':'prefix'+token+'suffix','unicode':'é'+token+'β'}[context]
    assert bool(guard.PATTERNS['session id'].search(text)) == (context=='bare')
def test_real_file_scan_detects_tag(tmp_path,monkeypatch):
    monkeypatch.setattr(guard,'ROOT',tmp_path)
    (tmp_path/'source.py').write_text('# card '+IDS[0]+'_458_example\n',encoding='utf-8')
    assert len(guard._hits())==1
def test_immutable_contract_allowlist_unchanged(tmp_path,monkeypatch):
    monkeypatch.setattr(guard,'ROOT',tmp_path)
    p=tmp_path/'mamey/data/mode_b/modeb_current50_v2_contract.json';p.parent.mkdir(parents=True)
    p.write_text('"'+IDS[0]+'_458_example"',encoding='utf-8')
    assert guard._hits()==[]
