from pathlib import Path
import hashlib
import importlib.util
import os
import pytest
ROOT=Path(os.environ.get('FRESHNESS_REVIEW_BASE',Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('freshness_budget_review',ROOT/'tools/evidence_freshness.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
def prepared(tmp_path,empty=False):
    path=tmp_path/'source';path.write_bytes(b'' if empty else b'ab')
    return path,{'schema':tool.SCHEMA,'artifacts':[{'id':'source','path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'unit':'artifact','source_revision':'fixture-v1','depends_on':[]}]}
def instrument(monkeypatch,path,when=None):
    original=Path.open;counts={'bytes':0,'edited':False}
    def grow():
        if not counts['edited']:
            counts['edited']=True
            with original(path,'wb') as target:target.write(b'abcdefgh')
    def opening(selected,*args,**kwargs):
        mode=args[0] if args else kwargs.get('mode','r')
        if selected!=path or 'b' not in mode:return original(selected,*args,**kwargs)
        if when=='before_open':grow()
        raw=original(selected,*args,**kwargs)
        class Read:
            def __enter__(self):raw.__enter__();return self
            def __exit__(self,*exc):return raw.__exit__(*exc)
            def fileno(self):return raw.fileno()
            def read(self,size=-1):
                if when=='first_read':grow()
                value=raw.read(size);counts['bytes']+=len(value);return value
        return Read()
    monkeypatch.setattr(Path,'open',opening);return counts
@pytest.mark.parametrize('budget',['file','total'])
@pytest.mark.parametrize('when',['before_open','first_read'])
def test_growth_cannot_exceed_actual_read_budget(tmp_path,monkeypatch,budget,when):
    path,manifest=prepared(tmp_path);counts=instrument(monkeypatch,path,when)
    result=tool.audit(manifest,tmp_path,max_file_bytes=2 if budget=='file' else 100,max_total_bytes=2 if budget=='total' else 100)
    assert counts['bytes']<=2,'ACTUAL_READ_EXCEEDED_DECLARED_BUDGET'
    assert result['hashed_bytes']==counts['bytes']
    assert result['artifacts'][0]['observed_sha256']=='' and result['status']=='HOLD'
    assert result['artifacts'][0]['direct_state']==('UNVERIFIED_FILE_BUDGET' if budget=='file' else 'UNVERIFIED_TOTAL_BUDGET')
@pytest.mark.parametrize('empty',[False,True])
def test_exact_limit_and_empty_file_controls(tmp_path,monkeypatch,empty):
    path,manifest=prepared(tmp_path,empty);expected=path.stat().st_size;counts=instrument(monkeypatch,path)
    result=tool.audit(manifest,tmp_path,max_file_bytes=2,max_total_bytes=2)
    assert result['status']=='PASS_BYTES_AND_DECLARED_DEPENDENCIES'
    assert counts['bytes']==expected and result['hashed_bytes']==expected
@pytest.mark.parametrize('field',['max_file_bytes','max_total_bytes'])
@pytest.mark.parametrize('value',[True,float('nan')])
def test_public_api_refuses_noninteger_budgets_before_payload_read(tmp_path,monkeypatch,field,value):
    path,manifest=prepared(tmp_path);counts=instrument(monkeypatch,path)
    with pytest.raises(ValueError,match='positive integers'):tool.audit(manifest,tmp_path,**{field:value})
    assert counts['bytes']==0
