import hashlib,importlib.util,json,os,shutil,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];BASE_TOOLS=Path(os.environ.get('EXPORT_REGISTRY_BASE_TOOLS',str(ROOT/'tools')));TOOL=ROOT/'tools/verify_export_registry.py'
s=importlib.util.spec_from_file_location('q8_helper',TOOL);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
@pytest.fixture
def fixture(tmp_path):
 root=tmp_path/'source';(root/'tools').mkdir(parents=True)
 guard=root/'tools/synthetic_id_registry_guard.py';shutil.copy2(BASE_TOOLS/'synthetic_id_registry_guard.py',guard)
 listing=root/'tools/test_synthetic_ids.txt';listing.write_text('AS-971\n');reg=tmp_path/'registry.tsv';reg.write_text('strain_id\nAS-973\n')
 return root,reg,{'guard_sha256':sha(guard),'allowlist_sha256':sha(listing)}
@pytest.mark.parametrize('field,value',[('guard_sha256',None),('allowlist_sha256',None),('guard_sha256','bad'),('allowlist_sha256','bad')])
def test_missing_selected_bindings_hold(fixture,field,value):
 root,reg,kw=fixture;kw[field]=value
 r=m.audit_export(root,reg,sha(reg),**kw);assert r['state']=='HOLD'
@pytest.mark.parametrize('field',['guard','list'])
def test_changed_selected_source_refuses_before_import(fixture,field):
 root,reg,kw=fixture;marker=root/'executed';guard=root/'tools/synthetic_id_registry_guard.py'
 guard.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("must not execute")\n')
 if field=='list':
  kw['guard_sha256']=sha(guard);(root/'tools/test_synthetic_ids.txt').write_text('AS-972\n')
 r=m.audit_export(root,reg,sha(reg),**kw)
 assert r['state']=='HOLD' and r['issues']==['SELECTED_SOURCE_DIGEST_MISMATCH'] and not marker.exists()
@pytest.mark.parametrize('mutation',['list','registry'])
def test_guard_changes_bound_input_holds(fixture,mutation):
 root,reg,kw=fixture;path=root/'tools/test_synthetic_ids.txt' if mutation=='list' else reg;guard=root/'tools/synthetic_id_registry_guard.py';guard.write_text('from pathlib import Path\ndef audit(a,b):\n Path('+repr(str(path))+').write_text("changed")\n return {}\ndef redacted_result(x): return {"state":"PASS_BOUND_SNAPSHOT"}\n');kw['guard_sha256']=sha(guard)
 r=m.audit_export(root,reg,sha(reg),**kw);assert r['state']=='HOLD' and r['issues']==['REGISTRY_GUARD_INPUT_CHANGED']
@pytest.mark.parametrize('bad', [{'state':'PASS_BOUND_SNAPSHOT'}, {'state':'PASS_BOUND_SNAPSHOT','schema':'sapote.synthetic-registry-audit.v1','issues':['RAW_PRIVATE_TEST_VALUE'],'collision_count':0}, {'state':'UNRECOGNIZED','issues':[],'collision_count':0}])
def test_unrecognized_result_refuses_redacted(fixture,bad):
 root,reg,kw=fixture;guard=root/'tools/synthetic_id_registry_guard.py';guard.write_text('def audit(a,b): return {}\ndef redacted_result(x): return '+repr(bad)+'\n');kw['guard_sha256']=sha(guard)
 r=m.audit_export(root,reg,sha(reg),**kw);assert r['state']=='HOLD' and 'RAW_PRIVATE_TEST_VALUE' not in json.dumps(r)
@pytest.mark.parametrize('mode,expected',[('clean',0),('collision',1),('missing_binding',2)])
def test_exact_shell_preflight_propagates_typed_exit(fixture,mode,expected):
 root,reg,kw=fixture;shutil.copy2(TOOL,root/'tools/verify_export_registry.py')
 if mode=='collision':reg.write_text('strain_id\nAS-971\n')
 text=(ROOT/'tools/make_public_tier.sh').read_text();block=text.split('# BEGIN EXPLICIT SYNTHETIC REGISTRY PREFLIGHT',1)[1].split('# END EXPLICIT SYNTHETIC REGISTRY PREFLIGHT',1)[0]
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',SRC=str(root),PYTHON=sys.executable,TIER='code',SYNTHETIC_REGISTRY=str(reg),SYNTHETIC_REGISTRY_SHA256=sha(reg),SYNTHETIC_GUARD_SHA256=kw['guard_sha256'] if mode!='missing_binding' else '',SYNTHETIC_ALLOWLIST_SHA256=kw['allowlist_sha256'])
 r=subprocess.run(['bash','-eu','-c',block],env=env,capture_output=True,text=True,timeout=15)
 assert r.returncode==expected and r.stdout==''
 record=json.loads(r.stderr);assert record['state']=={0:'PASS_BOUND_SNAPSHOT',1:'FAIL',2:'HOLD'}[expected]
 assert str(reg) not in r.stderr and 'AS-971' not in r.stderr


@pytest.mark.parametrize('contradiction',['missing_registry_digest','false_registry_bound','missing_registry_bound','wrong_registry_digest','nonboolean_registry_bound'])
def test_pass_requires_exact_returned_registry_binding(fixture,contradiction):
 root,reg,kw=fixture;guard=root/'tools/synthetic_id_registry_guard.py'
 script="""import hashlib
from pathlib import Path
def audit(a,b):
 r={'schema':'sapote.synthetic-registry-audit.v1','state':'PASS_BOUND_SNAPSHOT','issues':[],'collision_count':0,'allowlist_sha256':hashlib.sha256(Path(a).read_bytes()).hexdigest(),'registry_sha256':hashlib.sha256(Path(b).read_bytes()).hexdigest(),'registry_bound':True}
 CASE
 return r
def redacted_result(x):return x
"""
 change={'missing_registry_digest':"r.pop('registry_sha256')",'false_registry_bound':"r['registry_bound']=False",'missing_registry_bound':"r.pop('registry_bound')",'wrong_registry_digest':"r['registry_sha256']='0'*64",'nonboolean_registry_bound':"r['registry_bound']=1"}[contradiction]
 guard.write_text(script.replace('CASE',change));kw['guard_sha256']=sha(guard)
 result=m.audit_export(root,reg,sha(reg),**kw)
 assert result['state']=='HOLD' and result['issues']==['REGISTRY_GUARD_RESULT_CONTRACT_REFUSED']
 assert str(reg) not in json.dumps(result) and 'AS-971' not in json.dumps(result)
