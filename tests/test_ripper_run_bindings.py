"""Self-authored file bytes bind declarations, not model/runtime readiness."""
import hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('run_adapter',ROOT/'tools/ripper_adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);m=a.run_binding_module()
FIX=ROOT/'tests/fixtures/ripper';SEM=ROOT/'tests/fixtures/ripper_semantic'
class RunBindingTests(unittest.TestCase):
 def setUp(self):
  root=Path(os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir()));root.mkdir(parents=True,exist_ok=True);self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=root));self.out=self.work/'import'
  self.roles={'config':SEM/'fresh_run.conf.template','genbank':SEM/'synthetic_single_record.gbk','query_fasta':SEM/'synthetic_single_query.faa','queries':SEM/'synthetic_query_context.json','columns':FIX/'columns.json','raw_output':FIX/'synthetic.tsv','completion_log':FIX/'synthetic_completion.log'}
  for role in ('upstream_source','pfam_model','ripp_model'):
   p=self.work/(role+'.txt');p.write_text('SYNTHETIC '+role+' NOT A LIVE SOURCE OR MODEL\n');self.roles[role]=p
  self.manifest=dict(schema_version='ripper-run-binding-manifest/1',run_id='SYNTHETIC_RUN_001',evidence_kind='synthetic_fixture',profile_id='archived-e90b3e6-mergeRidePfam',source_revision='e90b3e6e74ddee99685183ca421323737012a991',files={k:self.sha(v) for k,v in self.roles.items()})
  self.receipt=json.loads((FIX/'complete.json').read_text());self.receipt.update(completed_accessions=['SYNTHETIC_TE_001'],queries_sha256=self.sha(self.roles['queries']),config_sha256=self.sha(self.roles['config']))
 def sha(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
 def args(self):return [k+'='+str(v) for k,v in self.roles.items()]
 def bind(self):
  p=self.work/'manifest.json';p.write_text(json.dumps(self.manifest)+'\n');data=m.bind_run(a.binding_api(),p,self.args(),self.work/'run');self.bound=self.work/'run/RUN_BINDING.json';self.receipt.update(run_id=data['run_id'],run_bindings_sha256=self.sha(self.bound));return data
 def import_result(self):
  p=self.work/'receipt.json';p.write_text(json.dumps(self.receipt)+'\n')
  return a.import_results(self.roles['queries'],p,self.out,self.roles['raw_output'],self.roles['columns'],self.roles['config'],self.roles['completion_log'],run_binding_path=self.bound,bound_files=self.args())
 def test_bound_bytes_are_not_model_or_execution_success(self):
  d=self.bind();self.assertEqual(d['binding_status'],'BOUND_DECLARED_FILES_ONLY');self.assertEqual(d['upstream_execution'],'NOT_EXECUTED');self.assertEqual(d['model_validation'],'BYTE_DIGEST_ONLY_NOT_MODEL_READY')
  data=self.import_result();self.assertEqual(data['run_binding']['run_id'],'SYNTHETIC_RUN_001');self.assertEqual(data['upstream_execution'],'NOT_EXECUTED_SYNTHETIC')
 def test_model_changed_after_binding_refused(self):
  self.bind();self.roles['ripp_model'].write_text('CHANGED')
  with self.assertRaisesRegex(ValueError,'FILE_DIGEST_MISMATCH'):self.import_result()
  self.assertFalse(self.out.exists())
 def test_new_run_claim_cannot_use_old_binding_receipt(self):
  self.bind();self.receipt['run_id']='SYNTHETIC_RUN_002'
  with self.assertRaisesRegex(ValueError,'RECEIPT_IDENTITY_MISMATCH'):self.import_result()
 def test_run_artifact_hash_required(self):
  self.bind();self.receipt['run_bindings_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'RECEIPT_IDENTITY_MISMATCH'):self.import_result()
 def test_missing_roles_produce_hold_and_block_complete_import(self):
  self.roles.pop('pfam_model');self.manifest['files'].pop('pfam_model');d=self.bind();self.assertEqual(d['binding_status'],'HOLD_REQUIRED_FILE_ROLES')
  with self.assertRaisesRegex(ValueError,'COMPLETE_ROLES_REQUIRED'):self.import_result()
 def test_no_implicit_discovery_from_artifact_paths(self):
  self.bind()
  with self.assertRaisesRegex(ValueError,'EXPLICIT_FILE_ROSTER_MISMATCH'):m.verify_boundary(a.binding_api(),self.bound,[],[],{},True,self.receipt)
 def test_operator_cannot_claim_synthetic_source_is_archive(self):
  self.manifest['evidence_kind']='operator_supplied'
  with self.assertRaisesRegex(ValueError,'ARCHIVED_SOURCE_PIN_MISMATCH'):self.bind()
 def test_local_plan_rechecks_exact_files(self):
  self.bind();d=a.local_plan(self.roles['queries'],self.roles['genbank'],self.roles['query_fasta'],self.roles['config'],self.work/'plan','archived-e90b3e6-mergeRidePfam',True,self.bound,self.args())
  self.assertEqual(d['run_binding']['run_id'],'SYNTHETIC_RUN_001');self.assertEqual(d['plan_status'],'HOLD')
 def test_digest_declaration_mismatch_refused_before_publication(self):
  self.manifest['files']['config']='0'*64
  with self.assertRaisesRegex(ValueError,'FILE_DIGEST_MISMATCH'):self.bind()
  self.assertFalse((self.work/'run').exists())
if __name__=='__main__':unittest.main()
