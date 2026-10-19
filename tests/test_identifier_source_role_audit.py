"""Optional source-role diagnostics and independent finalizer integrity; no universal name admission."""
import hashlib,importlib.util,json,os,shutil,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import identifier_source_roles as roles
POLICY=ROOT/roles.POLICY
PUBFILE='tests/test_mibig_no_redaction_corruption.py'
FIXFILE='tests/test_ks_phylogeny.py'

def source_fixture(tmp_path):
 # Optional role diagnostics use a bounded valid fixture, not universal live-repo admission.
 source=tmp_path/'source';(source/'tests').mkdir(parents=True);(source/'tools').mkdir()
 manifest=json.loads(roles.read_regular(POLICY))
 manifest['files']=[e for e in manifest['files'] if e['path'] in [PUBFILE,FIXFILE]]
 (source/roles.POLICY).write_text(json.dumps(manifest))
 for rel in [PUBFILE,FIXFILE,'tools/test_synthetic_ids.txt','tools/test_public_reference_tokens.json','tools/synthetic_id_registry_guard.py']:
  shutil.copyfile(ROOT/rel,source/rel)
 return source


def stage(tmp_path,selected=(PUBFILE,FIXFILE)):
 source=source_fixture(tmp_path)
 root=tmp_path/'stage';(root/'tests').mkdir(parents=True)
 shutil.copyfile(source/roles.POLICY,root/roles.POLICY)
 for rel in selected:
  target=root/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/rel,target)
 return root


def audited(root):
 source=root.parent/'source'
 return roles.audit_test_identifiers(source,root,roles.digest(roles.read_regular(source/roles.POLICY)))


def test_selected_public_and_authored_sites_retain_diagnostic_roles(tmp_path):
 root=stage(tmp_path);record=audited(root)
 assert record['state']=='PASS_SOURCE_ROLE_SCOPE' and record['counts']['public_reference_sites']==4
 assert record['counts']['authored_fixture_sites']==8 and record['artifact_export_permission'] is False


@pytest.mark.parametrize('relative,expected',[(PUBFILE,'public_reference_sites'),(FIXFILE,'authored_fixture_sites')])
def test_each_authorized_artifact_passes_its_exact_role(tmp_path,relative,expected):
 root=stage(tmp_path,[relative]);r=audited(root);assert r['state']=='PASS_SOURCE_ROLE_SCOPE' and r['counts'][expected]>0


def fixture_token():
 # Use the existing source declaration; no extra identity table or empirical data.
 return next(l for l in roles.read_regular(ROOT/'tools/test_synthetic_ids.txt').decode().splitlines() if l.strip() and not l.startswith('#'))


@pytest.mark.parametrize('variant',['canonical','underscore','zero_alias','private_field','public_identity_field','copied_public','renamed_fixture'])
def test_unselected_same_spelling_or_identity_field_cannot_borrow_role(tmp_path,variant):
 root=stage(tmp_path);token=fixture_token()
 if variant=='underscore':token=token.replace('-','_')
 elif variant=='zero_alias':token=token.replace('-','-0')
 if variant=='public_identity_field':
  token=json.loads(roles.read_regular(ROOT/'tools/test_public_reference_tokens.json'))['tokens'][0]['token']
 if variant=='copied_public':shutil.copyfile(ROOT/PUBFILE,root/'tests/copied.py')
 elif variant=='renamed_fixture':shutil.copyfile(ROOT/FIXFILE,root/'tests/renamed.py')
 else:(root/'tests/foreign.py').write_text(('strain_id = ' if variant in ['private_field','public_identity_field'] else 'value = ')+repr(token)+'\n')
 r=audited(root);assert r['state']=='HOLD' and r['findings']
 text=json.dumps(r);assert token not in text
 if variant in ['canonical','private_field']:assert r['counts']['declared_unreviewed_sites']>=1


@pytest.mark.parametrize('change',['source_bytes','table_bytes','table_absent','file_symlink','table_symlink','binary'])
def test_stage_binding_drift_or_uncovered_inputs_are_explicit(tmp_path,change):
 root=stage(tmp_path)
 if change=='source_bytes':(root/PUBFILE).write_text((root/PUBFILE).read_text()+'\n# newgeneration\n')
 elif change=='table_bytes':(root/roles.POLICY).write_text((root/roles.POLICY).read_text()+'\n')
 elif change=='table_absent':(root/roles.POLICY).rename(root/'retained-policy.json')
 elif change=='table_symlink':
  (root/roles.POLICY).rename(root/'retained-policy.json');(root/roles.POLICY).symlink_to(root/'retained-policy.json')
 elif change=='file_symlink':
  (root/PUBFILE).rename(root/'retained-source.py');(root/PUBFILE).symlink_to(root/'retained-source.py')
 else:(root/'tests/opaque.bin').write_bytes(b'\0\xffOPAQUE_ONLY')
 r=audited(root)
 if change=='binary':
  assert r['state']=='PASS_SOURCE_ROLE_SCOPE' and r['counts']['binary_outside_source_scope']==1
  assert r['artifact_export_permission'] is False
 else:assert r['state']=='HOLD' and r['issues']==['SOURCE_ROLE_BINDING_OR_AUDIT_UNVERIFIED']


def test_policy_digest_mutation_after_selection_is_hold(tmp_path):
 root=stage(tmp_path)
 assert roles.audit_test_identifiers(root.parent/'source',root,'0'*64)['state']=='HOLD'


def test_no_policy_digest_no_permission(tmp_path):
 root=stage(tmp_path)
 assert roles.audit_test_identifiers(root.parent/'source',root,None)['state']=='HOLD'


def test_historical_site_records_preserve_original_provenance_separately():
 # These exact historical bytes are evidence; they no longer admit every current source file.
 raw=roles.read_regular(POLICY);manifest=json.loads(raw)
 entries={e["path"]:e for e in manifest["files"]}
 # Independent pins from completed H2 baseline and exact H6 fixture-table review.
 baseline_paths = [
  'tests/test_410_redactor_unicode_separators.py',
  'tests/test_452_test_ids_all_allowlisted.py',
  'tests/test_archive_leak_scan.py',
  'tests/test_as48_public_np_carveout.py',
  'tests/test_as_free_public_release_gate_v97390.py',
  'tests/test_ks_phylogeny.py',
  'tests/test_mamey_source_cohort_id_guard_v97401.py',
  'tests/test_mibig_no_redaction_corruption.py',
  'tests/test_phylo_place_root_and_gate.py',
  'tests/test_phylo_roster.py',
  'tests/test_redact_ajs_single_digit.py',
  'tests/test_redact_public_tier.py',
  'tests/test_redactor_path_audit_lowercase_bc2.py',
  'tests/test_redactor_path_audit_v97251.py',
  'tests/test_strain_id_derivation.py',
  'tests/test_strain_identity_accession_prefix_v97395.py',
  'tests/test_strain_identity_guard.py',
  'tests/test_strict_source_disclosure_audit_v97395.py',
  'tests/test_tailoring_extract.py',
  'tools/archive_leak_scan.py',
  'tools/redact_public_tier.py',
  'tools/verify_tier_derivation.py',
 ]
 assert set(baseline_paths) <= set(entries), "Original reviewed baseline files missing"
 # Original 100 site records remain exact prefixes; appended reviewed sites cannot replace them.
 baseline_site_counts = {
   "tests/test_410_redactor_unicode_separators.py": 3,
   "tests/test_452_test_ids_all_allowlisted.py": 10,
   "tests/test_archive_leak_scan.py": 3,
   "tests/test_as48_public_np_carveout.py": 13,
   "tests/test_as_free_public_release_gate_v97390.py": 1,
   "tests/test_ks_phylogeny.py": 8,
   "tests/test_mamey_source_cohort_id_guard_v97401.py": 3,
   "tests/test_mibig_no_redaction_corruption.py": 4,
   "tests/test_phylo_place_root_and_gate.py": 2,
   "tests/test_phylo_roster.py": 11,
   "tests/test_redact_ajs_single_digit.py": 6,
   "tests/test_redact_public_tier.py": 5,
   "tests/test_redactor_path_audit_lowercase_bc2.py": 1,
   "tests/test_redactor_path_audit_v97251.py": 2,
   "tests/test_strain_id_derivation.py": 2,
   "tests/test_strain_identity_accession_prefix_v97395.py": 2,
   "tests/test_strain_identity_guard.py": 6,
   "tests/test_strict_source_disclosure_audit_v97395.py": 2,
   "tests/test_tailoring_extract.py": 2,
   "tools/archive_leak_scan.py": 1,
   "tools/redact_public_tier.py": 11,
   "tools/verify_tier_derivation.py": 2
 }
 assert sum(baseline_site_counts.values())==100
 baseline_entries=[dict(entries[path],sites=entries[path]["sites"][:baseline_site_counts[path]]) for path in baseline_paths]
 baseline_bytes=json.dumps(baseline_entries,sort_keys=True,separators=(",",":")).encode()
 assert roles.digest(baseline_bytes)=='6553ab438eca3f77f265a6b1c54ef94ac6781435b2b521f37dbd0735360fe9fb', "Original reviewed baseline site bindings changed; explicit re-review required"
 assert roles.digest(raw)=='3910dbfa19d90c5844ad07553d01b7a9b745f851488c0bf2e7ddd36a9379d713', "Selected 237-site table changed; review exact added/source bindings"
 assert sum(s['role'] in roles._PUBLIC_KINDS.values() for e in entries.values() for s in e['sites'])==57
 assert sum(s['role']==roles._FIXTURE_ROLE for e in entries.values() for s in e['sites'])==180
 assert len(entries)==55 and roles.digest(raw)==roles.digest(roles.read_regular(POLICY))


def test_source_compatibility_arguments_cannot_override_declarations(tmp_path):
 spec=importlib.util.spec_from_file_location('source_role_test_bridge',ROOT/'tests/test_452_test_ids_all_allowlisted.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 allowed=module._allowlist();assert module._unreviewed_test_ids(ROOT,allowed|{'UNSELECTED'},POLICY)=={'SOURCE_POLICY_OVERRIDE_REFUSED':['tests/']}
 module.test_scan_matches_the_cut_audit_shapes()


class BrokenStream:
 def write(self,value):return 0
 def flush(self):raise OSError('PRIVATE_NO_PROGRESS')


def test_failed_digest_publication_is_nonzero(tmp_path,monkeypatch):
 source=source_fixture(tmp_path)
 monkeypatch.setattr(roles.sys,'stdout',BrokenStream());assert roles.main(['--source-root',str(source),'--policy-digest'])==2


def test_source_test_and_production_use_one_decision_for_same_bytes(tmp_path):
 source=tmp_path/'source';(source/'tests').mkdir(parents=True);(source/'tools').mkdir()
 manifest=json.loads(roles.read_regular(POLICY));manifest['files']=[e for e in manifest['files'] if e['path'] in [PUBFILE,FIXFILE]]
 (source/roles.POLICY).write_text(json.dumps(manifest))
 for rel in [PUBFILE,FIXFILE,'tools/test_synthetic_ids.txt','tools/test_public_reference_tokens.json','tools/synthetic_id_registry_guard.py','tools/identifier_source_roles.py']:
  shutil.copyfile(ROOT/rel,source/rel)
 spec=importlib.util.spec_from_file_location('single_decision_test_bridge',ROOT/'tests/test_452_test_ids_all_allowlisted.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 allowed={l.strip() for l in roles.read_regular(source/'tools/test_synthetic_ids.txt').decode().splitlines() if l.strip() and not l.startswith('#')}
 assert module._unreviewed_test_ids(source,allowed,source/roles.POLICY)=={}
 frozen=roles.digest(roles.read_regular(source/roles.POLICY))
 r=roles.audit_test_identifiers(source,source,frozen);assert r['state']=='PASS_SOURCE_ROLE_SCOPE'
 # A declared spelling in an unselected source artifact holds in both callers.
 (source/'tests/unreviewed.py').write_text('sample = '+repr(fixture_token())+'\n')
 assert module._unreviewed_test_ids(source,allowed,source/roles.POLICY)
 assert roles.audit_test_identifiers(source,source,frozen)['state']=='HOLD'


def finalizer_module():
 spec=importlib.util.spec_from_file_location('role_bound_archive_finalizer',ROOT/'tools/finalize_public_archive.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m


def test_role_snapshot_agrees_with_finalizer_inventory_without_archive(tmp_path):
 root=stage(tmp_path);r=audited(root);m=finalizer_module()
 assert r['state']=='PASS_SOURCE_ROLE_SCOPE'
 assert roles.test_source_snapshot(m.inventory_stage(root),final_inventory=True)==r['test_source_sha256']
 (root/'tests/late.py').write_text('late change\n')
 assert roles.test_source_snapshot(m.inventory_stage(root),final_inventory=True)!=r['test_source_sha256']


@pytest.mark.parametrize('change',['changed','extra_file','empty_dir','cache'])
def test_finalizer_refuses_post_role_audit_drift_before_construction(tmp_path,monkeypatch,change):
 root=stage(tmp_path);expected=audited(root)['test_source_sha256'];m=finalizer_module()
 if change=='changed':(root/FIXFILE).write_text((root/FIXFILE).read_text()+'\n# changedgeneration\n')
 elif change=='extra_file':(root/'tests/late.py').write_text('new file\n')
 elif change=='empty_dir':(root/'tests/extra').mkdir()
 else:(root/'tests/__pycache__').mkdir();(root/'tests/__pycache__/late.pyc').write_bytes(b'OPAQUE_CACHE')
 monkeypatch.setattr(m,'capability_probe',lambda p:None)
 def writer(*a,**k):raise AssertionError('archive constructor must not run')
 monkeypatch.setattr(m,'_write_archive',writer);out=tmp_path/'out';out.mkdir()
 with pytest.raises(m.ArchiveTransactionError) as e:
  m.finalize_archive(root,out,'opaque.bin',expected_test_source_sha256=expected)
 assert e.value.reason in ['source_role_snapshot_drift','source_role_snapshot_unverified'] and not e.value.committed
 assert not (out/'opaque.bin').exists() and not list(out.glob('.archtxn-*'))


def test_absent_test_tree_has_bound_empty_snapshot_and_late_tree_is_detected(tmp_path):
 source_fixture(tmp_path)
 root=tmp_path/'stage';root.mkdir();r=audited(root);m=finalizer_module()
 assert r['state']=='PASS_SOURCE_ROLE_SCOPE' and r['test_source_sha256']==roles.test_source_snapshot([])
 (root/'tests').mkdir();(root/'tests/late.txt').write_text('newsource')
 assert roles.test_source_snapshot(m.inventory_stage(root),final_inventory=True)!=r['test_source_sha256']


def test_public_handoff_without_snapshot_cannot_launch_finalizer(tmp_path):
 harness=tmp_path/'harness';harness.mkdir();marker=tmp_path/'child-launched';(harness/'finalize_public_archive.py').write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("bad")\n')
 text=(ROOT/'tools/make_public_tier.sh').read_text();code='set -eu\n'+text[text.index('# BEGIN SOURCE ROLE FINALIZER HANDOFF'):]
 r=subprocess.run(['bash','-c',code,str(harness/'locator.sh')],env=dict(os.environ,PYTHON=sys.executable,TIER='code',SOURCE_TEST_ROLE_SHA256=''),capture_output=True,text=True,timeout=10)
 assert r.returncode==11 and not marker.exists() and 'no archive construction' in r.stderr


@pytest.mark.parametrize('variant',['strain_id','uppercase_keyword','public_prefix'])
def test_public_role_semantics_refuse_even_with_rebound_hash_and_complete_metadata(variant):
 import copy
 manifest=json.loads(roles.read_regular(POLICY));entry=copy.deepcopy(next(e for e in manifest['files'] if e['path']==PUBFILE));site=copy.deepcopy(entry['sites'][0]);token=json.loads(roles.read_regular(ROOT/'tools/test_public_reference_tokens.json'))['tokens'][0]['token']
 if variant=='strain_id':raw=('strain_id = '+repr(token)+'\n').encode()
 elif variant=='uppercase_keyword':raw=('f(STRAIN='+repr(token)+')\n').encode()
 else:raw=('product = '+repr(token+'_other')+'\n').encode()
 a=raw.index(token.encode());site.update(start=a,end=a+len(token),token_sha256=roles.digest(token.encode()),context_start=0,context_end=len(raw),context_sha256=roles.digest(raw),owner='<module>',lexical_kind='string');entry.update(source_sha256=roles.digest(raw),sites=[site]);_,public,keys=roles.reference_hashes(ROOT);_,allowed=roles.declarations(ROOT,keys)
 with pytest.raises(ValueError,match='public role context'):roles.bound_sites(raw,entry,public,allowed)


def test_finalizer_matching_snapshot_uses_only_opaque_mocks(tmp_path,monkeypatch,capsys):
 m=finalizer_module();spec=importlib.util.spec_from_file_location('snapshot_test_config',ROOT/'tests/test_finalizer_interrupted_receipts.py');helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
 root,out,final,calls=helpers.configure(m,tmp_path,monkeypatch,'normal',RuntimeError('unused'))
 # No test files in this deliberately opaque mock inventory; exact empty snapshot is bound.
 receipt=m.finalize_archive(root,out,final.name,expected_test_source_sha256=roles.test_source_snapshot([]))
 assert receipt.status=='COMMITTED' and final.read_bytes()==helpers.OPAQUE


def test_snapshot_rejects_normalized_namespace_collisions():
 rows=[{'name':'tests/é.txt','kind':'REGULAR_FILE','size':1,'sha256':'0'*64},
       {'name':'tests/e\u0301.txt','kind':'REGULAR_FILE','size':1,'sha256':'0'*64}]
 with pytest.raises(ValueError,match='snapshot shape'):roles.test_source_snapshot(rows)


def test_malformed_snapshot_refuses_before_any_capability_probe(tmp_path,monkeypatch):
 m=finalizer_module()
 def forbidden(*a,**k):raise AssertionError('no nativeprobe for invalidbinding')
 monkeypatch.setattr(m,'capability_probe',forbidden)
 with pytest.raises(m.ArchiveTransactionError) as e:m.finalize_archive(tmp_path,tmp_path,'opaque.bin',expected_test_source_sha256='invalid')
 assert e.value.reason=='source_role_snapshot_digest_invalid' and not e.value.committed


def test_policy_pins_all_three_source_semantic_dependencies():
 manifest=json.loads(roles.read_regular(POLICY))
 for rel,key in [('tools/test_synthetic_ids.txt','canonical_declarations_sha256'),
                 ('tools/test_public_reference_tokens.json','public_reference_catalog_sha256'),
                 ('tools/synthetic_id_registry_guard.py','identity_normalizer_sha256')]:
  assert roles.digest(roles.read_regular(ROOT/rel))==manifest[key]


@pytest.mark.parametrize('change',['extra','missing','false_permission','contradictory_issues','bool_count','unreviewed_count','wrong_policy','short_snapshot'])
def test_contradictory_or_incomplete_role_receipts_are_refused(tmp_path,change):
 import copy
 root=stage(tmp_path);record=copy.deepcopy(audited(root));expected=roles.digest(roles.read_regular(root.parent/'source'/roles.POLICY))
 if change=='extra':record['extra']=True
 elif change=='missing':record.pop('counts')
 elif change=='false_permission':record['artifact_export_permission']=True
 elif change=='contradictory_issues':record['issues']=['unverified']
 elif change=='bool_count':record['counts']['public_reference_sites']=True
 elif change=='unreviewed_count':record['counts']['declared_unreviewed_sites']=1
 elif change=='wrong_policy':record['policy_sha256']='0'*64
 else:record['test_source_sha256']='abc'
 with pytest.raises(ValueError):roles.validate_role_audit_receipt(record,expected)
