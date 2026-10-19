"""Synthetic admission declarations only; no native Perl/tools/source executed."""
import hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('native_adapter',ROOT/'tools/ripper_adapter.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a);m=a.owned_module('ripper_native_contract');PROFILE=json.loads((ROOT/'tools/ripper_source_profile.json').read_text())
class NativeContract(unittest.TestCase):
 def setUp(self):
  self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir())));self.inner=self.work/'not_created/upstream_run';self.roles={}
  for role in m.REQUIRED:
   p=self.work/role;p.write_text('SYNTHETIC_CONTRACT_ONLY_NOT_A_NATIVE_RESOURCE\n');self.roles[role]=p
   if role in m.TOOLS:p.chmod(0o700)
  if os.environ.get('RIPPER_DISPATCHER_TEST_INPUT'):self.roles['perl_dispatcher']=Path(os.environ['RIPPER_DISPATCHER_TEST_INPUT'])
  sem=ROOT/'tests/fixtures/ripper_semantic';self.roles.update(genbank=sem/'synthetic_single_record.gbk',query_fasta=sem/'synthetic_single_query.faa',queries=sem/'synthetic_query_context.json')
  self.roles['config'].write_text('prodigalshortbin '+str(self.roles['prodigal_short'])+'\nprepeptab ripper\n')
  self.roles['source_closure'].write_text(json.dumps({'schema':'lane05-ripper-adapted-source-profile-v1','source_revision':PROFILE['revision'],'files':[{'role':k,'sha256':self.sha(self.roles[v])} for k,v in {'archived_base':'archived_base','adapted_source':'upstream_source','cumulative_patch':'source_patch'}.items()]}))
  self.runtime={'schema_version':'ripper-native-runtime/1','state':'PROBED_NATIVE_RUNTIME_CONTENT_UNATTESTED','tool_sha256':{k:self.sha(self.roles[k]) for k in m.TOOLS},'tool_versions':{k:'SYNTHETIC_CONTRACT_ONLY_NO_EXECUTION' for k in m.TOOLS},'module_versions':{k:'SYNTHETIC_CONTRACT_ONLY_NO_EXECUTION' for k in m.MODULES},'perl5lib':[],'prodigal_short_validation':'SHORT_ORF_BEHAVIOR_REVIEWED','blast_database_format_validation':'REVIEWED_FOR_SELECTED_SOURCE','blast_pairwise_parser_validation':'REVIEWED_FOR_SELECTED_BIOPERL','prodigal_recipe_sha256':self.sha(self.roles['prodigal_recipe'])}
  lib=self.work/'synthetic_perl_lib'
  for name,role in m.MODULE_ROLES.items():
   p=lib/Path(*name.split('::')).with_suffix('.pm');p.parent.mkdir(parents=True,exist_ok=True);p.write_text('SYNTHETIC_NOT_NATIVE_MODULE\n');self.roles[role]=p
  self.runtime.update(probed_interpreter_sha256=self.sha(self.roles['perl_runtime']),tool_probe_exit_codes={k:0 for k in m.TOOLS},module_probe_exit_codes={k:0 for k in m.MODULES})
  self.runtime.update(perl5lib=[str(lib)],module_sha256={k:self.sha(self.roles[v]) for k,v in m.MODULE_ROLES.items()},module_paths={k:str(self.roles[v]) for k,v in m.MODULE_ROLES.items()})
  self.spec={'source_revision':PROFILE['revision']};self.adaptation={'artifact_sha256':'a'*64};self.review=None
 def sha(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
 def prepare(self):
  self.roles['runtime_receipt'].write_text(json.dumps(self.runtime));bound={k:a.tool_binding(p) if k in m.TOOLS else a.binding(p,p.read_bytes()) for k,p in self.roles.items()}
  api=a.binding_api();owned=api['owned_module']
  def modules(name):
   value=owned(name)
   if name=='ripper_source_admission':value.NATIVE_INTERFACES=dict(value.NATIVE_INTERFACES,**{bound['upstream_source']['sha256']:'q3'})
   return value
  api['owned_module']=modules
  with patch.object(m,'DISPATCHER_SHA256',bound['perl_dispatcher']['sha256']):return m.prepare(api,self.spec,'b'*64,bound,[],self.adaptation,self.inner,self.review)
 def approve_synthetic_declarations_for_pure_contract_test(self):
  d=self.prepare();q=dict(d['review_request'],decision='APPROVED_NATIVE_LOCAL_EXECUTION',local_use_decision='REVIEWED_LOCAL_EXECUTION_ONLY_NO_DISTRIBUTION_CLEARANCE');self.review=self.work/'synthetic_review.json';self.review.write_text(json.dumps(q));return q
 def test_missing_parent_review_holds_exact_prepared_native_request(self):
  d=self.prepare();self.assertIn('HOLD_LOCAL_SOURCE_EXECUTION_ADMISSION',d['holds']);self.assertEqual(d['hmm_annotation'],'NOT_RUN_SEPARATE_STAGE');self.assertNotIn('pfam_model',m.REQUIRED);self.assertNotIn('ripp_model',m.REQUIRED)
  self.assertEqual(d['input_basename'],self.roles['genbank'].name);self.assertEqual(d['argv'][-2:],['--',str(self.roles['genbank'])]);self.assertIn('--outfile',d['argv']);self.assertEqual(d['argv'][d['argv'].index('--temp-root')+1],str(self.inner/'temp'));self.assertFalse(self.inner.exists())
 def test_exact_parent_content_can_admit_request_not_permanent_hold(self):
  self.approve_synthetic_declarations_for_pure_contract_test();d=self.prepare();self.assertEqual(d['holds'],[]);self.assertEqual(d['review_content_authentication'],'UNATTESTED_EXPLICIT_PARENT_REVIEW_CONTENT')
 def test_mutated_argv_spec_files_or_decision_refused(self):
  q=self.approve_synthetic_declarations_for_pure_contract_test()
  for key,bad in (('argv_sha256','c'*64),('spec_sha256','d'*64),('decision','PENDING_PARENT_REVIEW'),('file_sha256',{}),('adapted_profile_sha256','0'*64),('environment_sha256','0'*64),('semantic_sha256','0'*64),('evidence_kind','synthetic_fixture')):
   changed=dict(q);changed[key]=bad;self.review.write_text(json.dumps(changed))
   with self.subTest(key=key),self.assertRaisesRegex(ValueError,'PARENT_REVIEW_BINDING_MISMATCH'):self.prepare()
 def test_missing_module_and_tool_behavior_stay_hold_even_without_review(self):
  self.runtime['module_versions'].pop('Bio::SeqIO');self.runtime['prodigal_short_validation']='UNVERIFIED';d=self.prepare();self.assertIn('HOLD_NATIVE_PERL_MODULES',d['holds']);self.assertIn('HOLD_NATIVE_TOOL_BEHAVIOR_REVIEW',d['holds'])
 def test_runtime_tool_digest_mismatch_holds(self):
  self.runtime['tool_sha256']['blastp']='0'*64;d=self.prepare();self.assertIn('HOLD_NATIVE_RUNTIME_TOOL_BYTES',d['holds'])
 def test_controlled_path_cannot_resolve_other_executable(self):
  replacement=self.work/'other';replacement.mkdir();p=replacement/'not_named_blastp';p.write_text('SYNTHETIC\n');p.chmod(0o700);self.roles['blastp']=p;self.runtime['tool_sha256']['blastp']=self.sha(p);d=self.prepare();self.assertIn('HOLD_NATIVE_CONTROLLED_PATH_BLASTP',d['holds'])
 def test_config_allowlist_namespace_ranges_and_exact_prodigal(self):
  for text in ('','pfamdir /unbound\n','prodigalshortbin /wrong\n','prodigalshortbin '+str(self.roles['prodigal_short'])+'\nflankLen nan\n','prodigalshortbin '+str(self.roles['prodigal_short'])+'\nsqlite3fn /outside\n',' prodigalshortbin '+str(self.roles['prodigal_short'])+'\n','prodigalshortbin '+str(self.roles['prodigal_short'])+'\nprepeptab ripper;drop\n'):
   self.roles['config'].write_text(text)
   with self.subTest(text=text),self.assertRaises(ValueError):self.prepare()
 def test_missing_semantic_dependency_holds(self):
  api=a.binding_api();api['validate_local_semantics']=lambda *args:{'status':'HOLD_DEPENDENCY_UNAVAILABLE'}
  self.roles['runtime_receipt'].write_text(json.dumps(self.runtime));bound={k:a.binding(p,p.read_bytes()) for k,p in self.roles.items()};d=m.prepare(api,self.spec,'b'*64,bound,[],self.adaptation,self.inner);self.assertIn('HOLD_NATIVE_INPUT_SEMANTIC_DEPENDENCY',d['holds'])
 def test_config_file_cannot_expand_to_arbitrary_run_path(self):
  self.roles['config'].write_text('prodigalshortbin '+str(self.roles['prodigal_short'])+'\nblastdbdir '+str(self.inner/'temp')+'\n')
  with self.assertRaisesRegex(ValueError,'OUTPUT_NAMESPACE_MISMATCH'):self.prepare()
 def test_missing_native_roles_is_precise_hold(self):
  d=m.prepare(a.binding_api(),self.spec,'b'*64,{},[],self.adaptation,self.inner);self.assertIn('HOLD_MISSING_NATIVE_ROLES',d['holds'])
 def test_native_flag_cannot_execute_synthetic_mode(self):
  p=self.work/'spec.json';p.write_text(json.dumps({'schema_version':'ripper-lifecycle-spec/1','mode':'synthetic_stub','limits':{'wall_seconds':1,'rss_bytes':1024,'disk_bytes':1024,'poll_seconds':0.01}}));l=a.owned_module('ripper_lifecycle')
  with patch.object(l.subprocess,'Popen',side_effect=AssertionError('no launch')),self.assertRaisesRegex(ValueError,'NATIVE_EXECUTION_MODE_REQUIRED'):l.lifecycle(a.binding_api(),p,[],self.work/'run',execute_native=True)

 def test_unavailable_version_or_failed_probe_remains_hold(self):
  self.runtime['tool_versions']['blastp']='UNAVAILABLE';self.runtime['module_probe_exit_codes']['Bio::SeqIO']=1;d=self.prepare();self.assertIn('HOLD_NATIVE_TOOL_VERSIONS',d['holds']);self.assertIn('HOLD_NATIVE_PROBE_COMPLETION',d['holds'])
 def test_whitespace_padded_unavailable_versions_retain_their_hold(self):
  for value in (' unavailable ','\tUNVERIFIED\n',' missing ',' unknown ',' NOT_PROBED '):
   self.runtime['tool_versions']['blastp']=value;self.runtime['module_versions']['Bio::SeqIO']=value;d=self.prepare()
   with self.subTest(value=value):self.assertIn('HOLD_NATIVE_TOOL_VERSIONS',d['holds']);self.assertIn('HOLD_NATIVE_PERL_MODULES',d['holds'])
 def test_changed_module_file_hash_holds(self):
  self.runtime['module_sha256']['Bio::SeqIO']='0'*64;d=self.prepare();self.assertIn('HOLD_NATIVE_PERL_MODULE_BYTES',d['holds'])
 def test_explicit_inc_dispatch_and_private_tmp_are_bound_not_inherited(self):
  d=self.prepare();self.assertEqual(d['argv'][1],str(self.roles['perl_dispatcher']));self.assertEqual(d['argv'][2],str(len(self.runtime['perl5lib'])));self.assertEqual(d['environment']['TMPDIR'],str(self.inner.parent/'runtime_tmp'));self.assertNotIn('PERL5LIB',d['environment']);self.assertFalse(self.inner.exists());self.assertFalse((self.inner.parent/'runtime_tmp').exists())
 def test_unreviewed_dispatcher_keeps_execution_hold(self):
  p=self.work/'unreviewed_dispatcher.pl';p.write_text('SYNTHETIC_UNKNOWN_DISPATCHER');self.roles['perl_dispatcher']=p;self.roles['runtime_receipt'].write_text(json.dumps(self.runtime));bound={k:a.binding(v,v.read_bytes()) for k,v in self.roles.items()}
  d=m.prepare(a.binding_api(),self.spec,'b'*64,bound,[],self.adaptation,self.inner);self.assertIn('HOLD_NATIVE_DISPATCHER_INTERFACE_UNREVIEWED',d['holds'])
 def test_network_library_locator_refused_without_stat(self):
  self.runtime['perl5lib']=['/Network/UNREQUESTED_TEST_LOCATOR'];original=Path.is_dir
  def guarded(path):
   if str(path).startswith('/Network'):raise AssertionError('network locator was accessed')
   return original(path)
  with patch.object(Path,'is_dir',guarded),self.assertRaisesRegex(ValueError,'PERL_LIBRARY_PATH_INVALID'):self.prepare()
 def test_explicit_observed_closure_is_bound_and_not_called_exhaustive(self):
  self.spec['bind_observed_runtime_closure']=True;p=self.roles['perl_module_bio_seqio'];self.runtime['transitive_loaded_bindings']=[a.binding(p,p.read_bytes())];d=self.prepare();self.assertEqual(d['observed_runtime_closure']['file_count'],1);self.assertEqual(d['observed_runtime_closure']['status'],'EXACT_OBSERVED_FILES_BOUND_NOT_EXHAUSTIVE_RUNTIME_PROOF')
 def test_changed_observed_closure_bytes_refused(self):
  self.spec['bind_observed_runtime_closure']=True;p=self.roles['perl_module_bio_seqio'];self.runtime['transitive_loaded_bindings']=[dict(a.binding(p,p.read_bytes()),sha256='0'*64)]
  with self.assertRaisesRegex(ValueError,'RUNTIME_CLOSURE_BYTES_MISMATCH'):self.prepare()
 def test_observed_closure_external_or_network_path_is_not_opened(self):
  self.spec['bind_observed_runtime_closure']=True;self.runtime['transitive_loaded_bindings']=[{'path':'/Network/UNREQUESTED_TEST_CLOSURE','bytes':1,'sha256':'0'*64}]
  with self.assertRaisesRegex(ValueError,'CLOSURE_PATH_OR_BUDGET'):self.prepare()
 def test_unselected_observed_closure_paths_are_not_followed(self):
  self.runtime['transitive_loaded_bindings']=[{'path':'/Network/UNREQUESTED_TEST_CLOSURE','bytes':1,'sha256':'0'*64}];d=self.prepare();self.assertEqual(d['observed_runtime_closure']['status'],'NOT_SELECTED_NO_TRANSITIVE_CLOSURE_CLAIM')
 def test_duplicate_observed_closure_refused(self):
  self.spec['bind_observed_runtime_closure']=True;p=self.roles['perl_module_bio_seqio'];entry=a.binding(p,p.read_bytes());self.runtime['transitive_loaded_bindings']=[entry,entry]
  with self.assertRaisesRegex(ValueError,'CLOSURE_PATH_OR_BUDGET'):self.prepare()
 def test_parent_native_rss_budget_is_bounded_and_stub_ceiling_unchanged(self):
  lifecycle=a.owned_module('ripper_lifecycle');limits={'wall_seconds':300,'rss_bytes':2*1024**3,'disk_bytes':256*1024**2,'poll_seconds':0.05};self.assertEqual(lifecycle.policy({'mode':'adapted_local05','limits':limits}),limits)
  with self.assertRaisesRegex(ValueError,'LIMIT_INVALID'):lifecycle.policy({'mode':'synthetic_stub','limits':limits})
  with self.assertRaisesRegex(ValueError,'LIMIT_INVALID'):lifecycle.policy({'mode':'adapted_local05','limits':dict(limits,rss_bytes=2*1024**3+1)})
class SelectedNativeDispatch(unittest.TestCase):
 sha=NativeContract.sha
 def setUp(self):
  selected=os.environ.get('RIPPER_NATIVE_TEST_INPUTS')
  if not selected:self.skipTest('explicit current source closure inputs not selected')
  NativeContract.setUp(self);inputs=json.loads(Path(selected).read_text());self.adapted=inputs.pop('adapted_profile');self.roles.update({k:Path(v) for k,v in inputs.items()});self.runtime['prodigal_recipe_sha256']=self.sha(self.roles['prodigal_recipe'])
 def make_spec(self):
  self.roles['runtime_receipt'].write_text(json.dumps(self.runtime))
  # Original runtime role digests remain the synthetic fixture's unchanged files.
  d={'schema_version':'ripper-lifecycle-spec/1','mode':'adapted_local05','profile_id':PROFILE['id'],'source_revision':PROFILE['revision'],'files':{k:self.sha(p) for k,p in self.roles.items()},'limits':{'wall_seconds':1,'rss_bytes':128*1024**2,'disk_bytes':2*1024**2,'poll_seconds':0.01}}
  self.specfile=self.work/'dispatch_spec.json';self.specfile.write_text(json.dumps(d));return [k+'='+str(p) for k,p in self.roles.items()]
 def test_reviewed_native_dispatch_has_real_argv_but_test_prevents_launch(self):
  args=self.make_spec();l=a.owned_module('ripper_lifecycle');run=self.work/'native_dispatch';first=l.lifecycle(a.binding_api(),self.specfile,args,run,self.adapted)
  self.assertEqual(first['status'],'HOLD');self.assertFalse((run/'runtime_tmp').exists());q=dict(first['native_contract']['review_request'],decision='APPROVED_NATIVE_LOCAL_EXECUTION',local_use_decision='REVIEWED_LOCAL_EXECUTION_ONLY_NO_DISTRIBUTION_CLEARANCE');review=self.work/'synthetic_contract_review.json';review.write_text(json.dumps(q))
  with patch.object(l.subprocess,'Popen',side_effect=OSError('SYNTHETIC_TEST_PREVENTED_NATIVE_LAUNCH')) as popen:
   result=l.lifecycle(a.binding_api(),self.specfile,args,run,self.adapted,execute_native=True,native_admission_path=review,resume_preflight=True)
  self.assertEqual(popen.call_count,1);self.assertEqual(popen.call_args.args[0],first['prepared_argv']);self.assertTrue(popen.call_args.kwargs['start_new_session'])
  self.assertEqual(result['status'],'FAILED');self.assertTrue((run/'runtime_tmp').is_dir());self.assertFalse((run/'upstream_run').exists());self.assertEqual(result['upstream_execution'],'NOT_EXECUTED');self.assertIn('SYNTHETIC_TEST_PREVENTED_NATIVE_LAUNCH',result['error'])
  self.assertEqual(json.loads((run/'TERMINAL.json').read_text())['status'],'HOLD');self.assertTrue((run/'EXECUTION_TERMINAL.json').is_file())
  with self.assertRaisesRegex(ValueError,'PREFLIGHT_ROOT_NOT_PRISTINE'):l.lifecycle(a.binding_api(),self.specfile,args,run,self.adapted,execute_native=True,native_admission_path=review,resume_preflight=True)
 def test_execute_native_without_parent_review_never_launches(self):
  args=self.make_spec();l=a.owned_module('ripper_lifecycle')
  with patch.object(l.subprocess,'Popen',side_effect=AssertionError('must not launch')):result=l.lifecycle(a.binding_api(),self.specfile,args,self.work/'unreviewed',self.adapted,execute_native=True)
  self.assertEqual(result['status'],'HOLD');self.assertEqual(result['upstream_execution'],'NOT_EXECUTED')
 def test_tampered_reserved_preflight_does_not_resume(self):
  args=self.make_spec();l=a.owned_module('ripper_lifecycle');run=self.work/'tampered';first=l.lifecycle(a.binding_api(),self.specfile,args,run,self.adapted);q=dict(first['native_contract']['review_request'],decision='APPROVED_NATIVE_LOCAL_EXECUTION',local_use_decision='REVIEWED_LOCAL_EXECUTION_ONLY_NO_DISTRIBUTION_CLEARANCE');review=self.work/'review.json';review.write_text(json.dumps(q));p=run/'PREFLIGHT.json';bad=json.loads(p.read_text());bad['sources']=[];p.write_text(json.dumps(bad))
  with patch.object(l.subprocess,'Popen',side_effect=AssertionError('no launch')),self.assertRaisesRegex(ValueError,'PREFLIGHT_BOUNDARY_CHANGED'):l.lifecycle(a.binding_api(),self.specfile,args,run,self.adapted,execute_native=True,native_admission_path=review,resume_preflight=True)

class NativeCLI(unittest.TestCase):
 def test_native_execution_hold_returns_two_and_forwards_exact_optin(self):
  from types import SimpleNamespace
  fake=SimpleNamespace(lifecycle=lambda *args:{'status':'HOLD','upstream_execution':'NOT_EXECUTED'})
  with patch.object(a,'owned_module',return_value=fake),patch.object(fake,'lifecycle',return_value={'status':'HOLD','upstream_execution':'NOT_EXECUTED'}) as run:
   code=a.main(['lifecycle','--spec','SYNTHETIC_SPEC','--file','config=SYNTHETIC_CONFIG','--run-root','/SYNTHETIC_NOT_USED','--execute-native','--native-admission','SYNTHETIC_REVIEW','--resume-preflight'])
  self.assertEqual(code,2);self.assertTrue(run.call_args.args[7]);self.assertTrue(run.call_args.args[9])
 def test_ambiguous_native_outcome_returns_two(self):
  from types import SimpleNamespace
  fake=SimpleNamespace(lifecycle=lambda *args:{'status':'AMBIGUOUS','upstream_execution':'NOT_EXECUTED'})
  with patch.object(a,'owned_module',return_value=fake):
   self.assertEqual(a.main(['lifecycle','--spec','SYNTHETIC_SPEC','--file','config=SYNTHETIC_CONFIG','--run-root','/SYNTHETIC_NOT_USED','--execute-native']),2)
if __name__=='__main__':unittest.main()
