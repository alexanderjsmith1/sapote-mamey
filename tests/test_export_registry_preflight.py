"""Portable tiny metadata fixtures; no real registry, tier builder or release execution."""
import hashlib,importlib.util,json,os,shutil,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];BASE_TOOLS=Path(os.environ.get('EXPORT_REGISTRY_BASE_TOOLS',str(ROOT/'tools')));TOOL=ROOT/'tools/verify_export_registry.py'
spec=importlib.util.spec_from_file_location('q2_preflight',TOOL);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@pytest.fixture
def inputs(tmp_path):
 root=tmp_path/'source';(root/'tools').mkdir(parents=True)
 shutil.copy2(BASE_TOOLS/'synthetic_id_registry_guard.py',root/'tools/synthetic_id_registry_guard.py')
 (root/'tools/test_synthetic_ids.txt').write_text('AS-971\n')
 registry=tmp_path/'registry.tsv';registry.write_text('strain_id\nAS-973\n')
 return root,registry

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def audit(root,registry,sha):
 return m.audit_export(root,registry,sha,guard_sha256=digest(root/'tools/synthetic_id_registry_guard.py'),allowlist_sha256=digest(root/'tools/test_synthetic_ids.txt'))

@pytest.mark.parametrize('case',['unbound','bad_digest','mismatch','linked','inside_source'])
def test_missing_or_unbound_metadata_holds_without_source_writes(inputs,case):
 root,registry=inputs;before={p.name:p.read_bytes() for p in (root/'tools').iterdir()}
 sha=digest(registry)
 if case=='unbound':registry=None
 elif case=='bad_digest':sha='invalid'
 elif case=='mismatch':sha='0'*64
 elif case=='linked':p=registry.with_name('linked.tsv');p.symlink_to(registry);registry=p
 elif case=='inside_source':p=root/'registry.tsv';p.write_bytes(registry.read_bytes());registry=p
 result=audit(root,registry,sha)
 assert result['state']=='HOLD' and result['issues']
 assert {p.name:p.read_bytes() for p in (root/'tools').iterdir()}==before


def test_clean_snapshot_pass_is_explicitly_not_export_clearance(inputs):
 root,registry=inputs;r=audit(root,registry,digest(registry))
 assert r['state']=='PASS_BOUND_SNAPSHOT'
 assert 'literal/reference/history gates remain required' in r['scope']

@pytest.mark.parametrize('case',['removed_genuine','negative_canary','public_product','public_reference','zero_alias_duplicate'])
def test_forbidden_list_roles_or_registry_collisions_do_not_pass(inputs,case):
 root,registry=inputs
 token={'removed_genuine':'AS-705','negative_canary':'AS-821','public_product':'AS-48','public_reference':'AJS-327','zero_alias_duplicate':'AS-001\nAS-1'}[case]
 (root/'tools/test_synthetic_ids.txt').write_text(token+'\n')
 if case in ('removed_genuine','negative_canary'):registry.write_text('strain_id\n'+token+'\n')
 r=audit(root,registry,digest(registry))
 assert r['state']=='FAIL' and r['issues']
 assert token not in json.dumps(r)

@pytest.mark.parametrize('token',['AS-705','AS-821'])
def test_clean_registry_snapshot_permits_names_but_not_staged_byte_drift(inputs,token):
 root,registry=inputs
 assert audit(root,registry,digest(registry))['state']=='PASS_BOUND_SNAPSHOT'
 stage=registry.parent/'stage';(stage/'tests').mkdir(parents=True)
 (stage/'tests/test_control.py').write_text('SUBJECT = '+repr(token)+'\n')
 text=(ROOT/'tools/make_public_tier.sh').read_text()
 selection=text.split('# BEGIN TEST SOURCE SNAPSHOT\n',1)[1].split('# END TEST SOURCE SNAPSHOT',1)[0]
 # Names need no occurrence table. A real post-selection source mutation still refuses.
 code=('set -euo pipefail\n'+selection+'\nverify_staged_test_snapshot\n'
       +'printf "%s\\n" "$SOURCE_TEST_ROLE_SHA256"\n'
       +'printf "# changed after selection\\n" >> "$STAGE/tests/test_control.py"\n'
       +'verify_staged_test_snapshot\n')
 r=subprocess.run(['bash','-c',code],env=dict(os.environ,PYTHON=sys.executable,SRC=str(ROOT),STAGE=str(stage),TIER='code'),capture_output=True,text=True,timeout=15)
 assert len(r.stdout.strip())==64 and all(c in '0123456789abcdef' for c in r.stdout.strip())
 assert r.returncode==2 and 'staged test-source bytes or namespace changed after selection' in r.stderr
 assert token not in r.stdout+r.stderr


def test_actual_preflight_cli_redacts_and_keeps_stdout_empty(inputs):
 root,registry=inputs;(root/'tools/test_synthetic_ids.txt').write_text('AS-705\n');registry.write_text('strain_id\nAS-705\n')
 r=subprocess.run([sys.executable,'-B',str(TOOL),'--root',str(root),'--registry',str(registry),'--registry-sha256',digest(registry),'--guard-sha256',digest(root/'tools/synthetic_id_registry_guard.py'),'--allowlist-sha256',digest(root/'tools/test_synthetic_ids.txt')],capture_output=True,text=True,timeout=15)
 assert r.returncode==1 and r.stdout=='' and 'AS-705' not in r.stderr and str(registry) not in r.stderr
 assert json.loads(r.stderr)['collision_count']==1


def test_guard_wiring_precedes_stage_and_cannot_be_bypassed_by_pytest_skip():
 text=(ROOT/'tools/make_public_tier.sh').read_text()
 block=text.split('# BEGIN EXPLICIT SYNTHETIC REGISTRY PREFLIGHT',1)[1].split('# END EXPLICIT SYNTHETIC REGISTRY PREFLIGHT',1)[0]
 assert '--registry-sha256' in block and 'SKIP_INTIER_PYTEST' not in block
 assert text.index('# BEGIN EXPLICIT SYNTHETIC REGISTRY PREFLIGHT')<text.index('WORK="$(mktemp -d)"')
