"""N3 declaration consistency and exact source admission; no native source execution."""
import hashlib,importlib.util,json,os,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
raw_fixture=load('n3_raw_fixture',ROOT/'tests/test_ripper_raw_discovery.py');a=raw_fixture.a;raw=raw_fixture.m
native_fixture=load('n3_native_fixture',ROOT/'tests/test_ripper_native_contract.py')
class Declaration(unittest.TestCase):
 def setUp(self):
  self.case=raw_fixture.RawDiscovery('test_raw_candidate_is_unbound_without_hmm_or_coordinates');self.case.setUp();self.case.contract.update(source_interface='n3',requires_discovery_declaration=True)
  for key in ('upstream_source','config','genbank','query_fasta'):
   p=Path(self.case.bound[key]['path']) if key in self.case.bound else self.case.work/key;p.write_text('SYNTHETIC_EXPLICIT_N3_INPUT_ONLY\n');self.case.bound[key]=a.binding(p,p.read_bytes())
 def receipt(self,nohit=False,rows=0):
  self.case.complete(nohit)
  d={'schema':'ripper-local-discovery-review-v1','state':'NO_TE_HITS_DECLARED_UNATTESTED' if nohit else 'TE_MATCH_WITH_ROWS_UNATTESTED' if rows else 'TE_MATCH_NO_CANDIDATE_ROWS_UNATTESTED','candidate_rows_declared':rows,'te_matched_declared':not nohit,'stage_receipts':[str(p) for p in sorted((self.case.inner/'temp').glob('*.terminal.json'))],'inputs':{role:{k:self.case.bound[key][k] for k in ('path','bytes','sha256')} for role,key in {'source':'upstream_source','config':'config','query_fasta':'query_fasta','genbank':'genbank'}.items()},'validation_scope':'LOCAL_DECLARATION_NATIVE_EXECUTION_AND_FORMATS_UNATTESTED','evidence_channel':'RAW_DISCOVERY_NOT_HMM_MERGED_TABLE','biological_absence_inferred':False,'candidate_bgc_membership':'UNVERIFIED','completion':'NORMAL_SCRIPT_END_ONLY_NOT_INDEPENDENT_PROCESS_ATTESTATION'}
  self.path=self.case.inner/'DISCOVERY.json';self.path.write_text(json.dumps(d));return d
 def change(self,d):self.path.write_text(json.dumps(d))
 def test_matching_nohit_declaration_stays_scoped_and_unattested(self):
  self.receipt(True);d=self.case.parse();self.assertEqual(d['status'],'NO_HIT');self.assertEqual(d['source_declaration']['state'],'NO_TE_HITS_DECLARED_UNATTESTED');self.assertEqual(d['source_declaration']['status'],'MATCHED_UNATTESTED_SOURCE_DECLARATION');self.assertFalse(d['biological_absence_inferred'])
 def test_matching_raw_rows_are_not_hmm_annotation_or_membership(self):
  self.case.row();self.receipt(rows=1);d=self.case.parse();self.assertEqual(d['status'],'SUCCESS_UNBOUND');self.assertEqual(d['candidates'][0]['peptide_id'],'SYNTHETIC_TE_001_1');self.assertEqual(d['hmm_annotation'],'NOT_RUN_SEPARATE_STAGE');self.assertEqual(d['candidate_membership'],'UNVERIFIED')
 def test_te_match_with_zero_rows_is_not_no_te_hit(self):
  self.receipt();d=self.case.parse();self.assertEqual(d['status'],'NO_RETAINED_CANDIDATES');self.assertEqual(d['source_declaration']['state'],'TE_MATCH_NO_CANDIDATE_ROWS_UNATTESTED')
 def test_missing_n3_declaration_prevents_nohit_admission(self):
  self.case.complete(True);d=self.case.parse();self.assertEqual(d['status'],'AMBIGUOUS');self.assertIsNone(d['candidate_count']);self.assertIn('N3_DISCOVERY_DECLARATION_MISSING',d['incomplete'])
 def test_count_boolean_and_te_state_contradictions_refused(self):
  d=self.receipt(True)
  for key,value in (('candidate_rows_declared',1),('candidate_rows_declared',False),('te_matched_declared',True),('te_matched_declared',0),('state','TE_MATCH_WITH_ROWS_UNATTESTED')):
   changed=dict(d);changed[key]=value;self.change(changed)
   with self.subTest(key=key,value=value),self.assertRaisesRegex(ValueError,'OUTCOME_CONTRADICTION'):self.case.parse()
 def test_external_receipt_locator_never_read(self):
  d=self.receipt(True);d['inputs']['source']['path']='/UNADMITTED_EXTERNAL_INPUT_DO_NOT_READ';self.change(d);original=a.load_bytes;seen=[]
  def guard(path):
   seen.append(str(path))
   if str(path).startswith('/UNADMITTED'):raise AssertionError('receipt locator followed')
   return original(path)
  with patch.object(a,'load_bytes',guard),self.assertRaisesRegex(ValueError,'INPUT_BINDING_MISMATCH'):raw.parse_discovery(a.binding_api(),self.case.inner,self.case.bound,self.case.contract)
  self.assertFalse(any(x.startswith('/UNADMITTED') for x in seen))
 def test_duplicate_stage_roster_refused(self):
  d=self.receipt(True);d['stage_receipts'].append(d['stage_receipts'][0]);self.change(d)
  with self.assertRaisesRegex(ValueError,'STAGE_ROSTER_MISMATCH'):self.case.parse()
 def test_promoted_biological_or_process_qualification_refused(self):
  d=self.receipt(True)
  for key,value in (('biological_absence_inferred',True),('candidate_bgc_membership','CONFIRMED'),('validation_scope','NATIVE_VALIDATED'),('completion','AUTHENTICATED_SUCCESS')):
   changed=dict(d);changed[key]=value;self.change(changed)
   with self.subTest(key=key),self.assertRaisesRegex(ValueError,'QUALIFICATION_INVALID'):self.case.parse()
 def test_historical_q3_without_declaration_retains_its_separate_interface(self):
  self.case.contract.update(source_interface='q3',requires_discovery_declaration=False);self.case.complete(True);d=self.case.parse();self.assertEqual(d['status'],'NO_HIT');self.assertEqual(d['source_declaration']['status'],'NOT_REQUIRED_HISTORICAL_Q3_INTERFACE')
 def test_raw_nine_columns_cannot_enter_merged_eleven_column_import(self):
  f=load('n3_import_fixture',ROOT/'tests/test_ripper_source_profile.py');case=f.SourceProfileTests('test_source_profile_export_is_not_execution');case.setUp();case.raw.write_text('\t'.join(x for x,y in raw.COLUMNS)+'\n');case.rebind()
  with self.assertRaisesRegex(ValueError,'UPSTREAM_TSV_HEADER_MISMATCH'):case.run_import()
class ExactN3Profile(unittest.TestCase):
 def setUp(self):
  path=os.environ.get('RIPPER_N3_TEST_INPUTS')
  if not path:self.skipTest('explicit source-owner N3 inputs not selected')
  self.inputs=json.loads(Path(path).read_text());self.case=native_fixture.NativeContract('test_missing_parent_review_holds_exact_prepared_native_request');self.case.setUp();self.profile=self.inputs['adapted_profile']
  self.case.roles.update({k:Path(v) for k,v in self.inputs.items() if k!='adapted_profile'});self.case.runtime['prodigal_recipe_sha256']=self.case.sha(self.case.roles['prodigal_recipe']);self.case.roles['runtime_receipt'].write_text(json.dumps(self.case.runtime))
 def bound(self):return {k:a.tool_binding(p) if k in native_fixture.m.TOOLS else a.binding(p,p.read_bytes()) for k,p in self.case.roles.items()}
 def test_new_profile_verifies_and_old_q3_refuses_exact_n3_bytes(self):
  m=a.owned_module('ripper_source_admission');bound=self.bound();d=m.verify_adapted(a.binding_api(),self.profile,bound,[]);self.assertEqual(d['adapted_source_sha256'],'f37e1341c1f4ba1118fea6d30622bcc65a67d8ec3e9f605ee73d701f3e387ec9')
  if not os.environ.get('RIPPER_ADAPTED_TEST_INPUTS'):self.skipTest('explicit historical Q3 profile not selected')
  old=Path(os.environ['RIPPER_ADAPTED_TEST_INPUTS']).parent/'selected_adapted_profile/ADAPTED_SOURCE_PROFILE.json'
  with self.assertRaisesRegex(ValueError,'EXPLICIT_FILE_BINDING_MISMATCH'):m.verify_adapted(a.binding_api(),old,bound,[])
 def test_n3_native_preparation_uses_correct_phase_roster_and_argv(self):
  d=native_fixture.m.prepare(a.binding_api(),self.case.spec,'b'*64,self.bound(),[],{'artifact_sha256':self.case.sha(Path(self.profile))},self.case.inner)
  self.assertEqual(d['source_interface'],'n3');self.assertTrue(d['requires_discovery_declaration']);self.assertNotIn('--outfile',d['argv']);self.assertIn('blastn',native_fixture.m.REQUIRED);self.assertIn('perl_module_bio_species',native_fixture.m.REQUIRED);self.assertFalse({'hmmsearch','pfam_model','ripp_model'}&native_fixture.m.REQUIRED);self.assertIn('HOLD_LOCAL_SOURCE_EXECUTION_ADMISSION',d['holds'])
 def test_n3_additional_contract_is_required(self):
  bound=self.bound();bound.pop('source_discovery_contract');d=native_fixture.m.prepare(a.binding_api(),self.case.spec,'b'*64,bound,[],{'artifact_sha256':'a'*64},self.case.inner);self.assertIn('HOLD_MISSING_NATIVE_ROLES',d['holds']);self.assertEqual(d['additional_required_roles'],['source_discovery_contract'])
 def test_mismatched_source_closure_refused(self):
  p=self.case.work/'bad_closure.json';d=json.loads(self.case.roles['source_closure'].read_text());d['proposed_source']['sha256']='0'*64;p.write_text(json.dumps(d));self.case.roles['source_closure']=p
  with self.assertRaisesRegex(ValueError,'SOURCE_CLOSURE_BYTE_MISMATCH'):native_fixture.m.prepare(a.binding_api(),self.case.spec,'b'*64,self.bound(),[],{'artifact_sha256':'a'*64},self.case.inner)
 def test_unknown_source_interface_stays_held(self):
  case=native_fixture.NativeContract('test_missing_parent_review_holds_exact_prepared_native_request');case.setUp();case.roles['runtime_receipt'].write_text(json.dumps(case.runtime));bound={k:a.binding(p,p.read_bytes()) for k,p in case.roles.items()};d=native_fixture.m.prepare(a.binding_api(),case.spec,'b'*64,bound,[],case.adaptation,case.inner);self.assertIn('HOLD_NATIVE_SOURCE_INTERFACE_UNREVIEWED',d['holds'])
if __name__=='__main__':unittest.main()
