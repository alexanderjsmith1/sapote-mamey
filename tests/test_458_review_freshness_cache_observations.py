from pathlib import Path
import hashlib
import importlib.util
import inspect
import os
import pytest
ROOT=Path(os.environ.get('FRESHNESS_REVIEW_BASE',Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('freshness_cache_review',ROOT/'tools/evidence_freshness.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
def prepared(tmp_path):
    source=tmp_path/'shared';source.write_bytes(b'baseline');report=tmp_path/'report';report.write_bytes(b'out')
    def row(key,path,deps):return {'id':key,'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'unit':'artifact','source_revision':'fixture-v1','depends_on':deps}
    return source,{'schema':tool.SCHEMA,'artifacts':[row('first',source,[]),row('second',source,[]),row('report',report,['second'])]}
@pytest.mark.parametrize('mode',['resize','same_size','replacement_preserved_times'])
def test_cached_digest_does_not_validate_a_later_changed_observation(tmp_path,monkeypatch,mode):
    source,manifest=prepared(tmp_path);original=Path.stat;seen=[]
    def observe(path,*args,**kwargs):
        actual=original(path,*args,**kwargs)
        if path==source and inspect.currentframe().f_back.f_code.co_name=='audit':
            seen.append(True)
            if len(seen)==2:
                if mode=='replacement_preserved_times':
                    other=tmp_path/'replacement';other.write_bytes(b'modified');os.utime(other,ns=(actual.st_atime_ns,actual.st_mtime_ns));os.replace(other,source)
                else:
                    source.write_bytes(b'changed size' if mode=='resize' else b'modified');os.utime(source,ns=(actual.st_atime_ns,actual.st_mtime_ns+1000000000))
        return actual
    monkeypatch.setattr(Path,'stat',observe)
    result=tool.audit(manifest,tmp_path);rows={x['id']:x for x in result['artifacts']}
    assert rows['first']['state']=='CURRENT_BYTES'
    assert rows['second']['direct_state']=='UNVERIFIED_CHANGED_SINCE_HASH'
    assert rows['second']['observed_sha256']=='' and rows['second']['state']=='HOLD_DIRECT'
    assert rows['report']['state']=='INVALIDATED_DEPENDENCY' and rows['report']['blocking_ancestors']==['second']
    assert result['status']=='HOLD'

def test_unchanged_shared_path_is_still_hashed_once(tmp_path,monkeypatch):
    source,manifest=prepared(tmp_path);original=tool.bounded_digest;calls=[]
    def hashed(path,*args):calls.append(Path(path));return original(path,*args)
    monkeypatch.setattr(tool,'bounded_digest',hashed)
    result=tool.audit(manifest,tmp_path)
    assert result['status']=='PASS_BYTES_AND_DECLARED_DEPENDENCIES'
    assert calls.count(source)==1 and result['hashed_bytes']==len(b'baseline')+len(b'out')
