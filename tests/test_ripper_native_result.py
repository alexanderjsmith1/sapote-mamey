"""Retained-result CLI cases: content consistency cannot become annotation or coordinates."""
import copy,hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('result_adapter',ROOT/'tools/ripper_adapter.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a);m=a.owned_module('ripper_native_result')
class NativeResult(unittest.TestCase):
 def setUp(self):
  self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir())));self.term=self.work/'terminal.json';self.raw=self.work/'raw.json';self.out=self.work/'inspection';seq='M'+'A'*19
  self.candidates=[dict(enzyme_accession='SYN_TE',peptide_id='SYN_TE_'+str(i),sequence=seq,channel='main' if i==1 else 'distant',source_fields=dict(acc='SYN_TE',species='Fabricated only',ppser=i,fastaid='SYN_TE_'+str(i),aaseq=seq,ppstrand=1,testrand=1,pptedist=12,score=1.0),candidate_membership='UNVERIFIED',coordinate_status='ABSENT_PRODUCER_MAPPING',hmm_annotation='NOT_RUN') for i in (1,9001)]
  self.rawdata=dict(schema_version='ripper-raw-discovery/1',status='SUCCESS_UNBOUND',upstream_execution=m.EXECUTED,evidence_kind='local_adapter_observed_native',candidate_count=2,retained_raw_candidate_count=2,candidates=self.candidates,hmm_annotation='NOT_RUN_SEPARATE_STAGE',candidate_membership='UNVERIFIED',coordinate_provenance='ABSENT_PRODUCER_MAPPING',biological_absence_inferred=False,subject_context_mismatch=False,incomplete=[],source_declaration=dict(status='MATCHED_UNATTESTED_SOURCE_DECLARATION',state='TE_MATCH_WITH_ROWS_UNATTESTED',candidate_rows_declared=2))
  self.terminal=dict(schema_version='ripper-lifecycle/1',mode='adapted_local05',status='SUCCESS_UNBOUND',upstream_execution=m.EXECUTED,returncode=0,reason=None,supervision_cleanup_uncertain=False,output_admission='SCOPED_BOUND_BYTES_ONLY',outcome_scope='RAW_NATIVE_DISCOVERY_ONLY_HMM_ANNOTATION_NOT_RUN',candidate_bgc_membership='UNVERIFIED',biological_absence_inferred=False,native_contract=dict(source_interface='n3',requires_discovery_declaration=True,hmm_annotation='NOT_RUN_SEPARATE_STAGE'))
  self.terminal['terminal_publication']=dict(protocol='EXCLUSIVE_CANONICAL_LINK_AFTER_SERIALIZATION',canonical_name=self.term.name,staging_names_are_not_completion=True)
  self.save()
 def save(self):
  self.raw.write_text(json.dumps(self.rawdata));self.terminal['raw_discovery']=dict(status=self.rawdata['status'],candidate_count=self.rawdata['candidate_count'],retained_raw_candidate_count=self.rawdata['retained_raw_candidate_count'],sha256=hashlib.sha256(self.raw.read_bytes()).hexdigest());self.term.write_text(json.dumps(self.terminal))
 def inspect(self,raw=True):return m.native_result(a.binding_api(),self.term,self.raw if raw else None,self.out)
 def refuse(self,code):
  with self.assertRaisesRegex(ValueError,code):self.inspect()
  self.assertFalse(self.out.exists())
 def test_distinct_ids_sharing_sequence_remain_two_raw_rows_without_hmm(self):
  d=self.inspect();self.assertEqual(d['terminal_status'],'SUCCESS_UNBOUND');self.assertEqual(d['raw_candidate_count'],2);self.assertEqual(d['lexical_channel_counts'],{'main':1,'distant':1});self.assertEqual(d['hmm_annotation'],'NOT_RUN_SEPARATE_STAGE');self.assertEqual(d['coordinate_status'],'ABSENT_PRODUCER_MAPPING');self.assertEqual(d['canonical_import'],'NOT_ADMITTED');self.assertFalse(d['biological_absence_inferred'])
 def test_raw_digest_change_refused_even_when_candidate_count_matches(self):
  self.rawdata['candidates'][0]['sequence']='M'+'G'*19;self.raw.write_text(json.dumps(self.rawdata));self.refuse('RAW_DIGEST_MISMATCH')
 def test_failed_terminal_cannot_admit_stale_raw_rows_even_with_valid_hash(self):
  self.terminal.update(status='FAILED',returncode=7,reason='EXIT_NONZERO',output_admission='NOT_ADMITTED');self.save();self.refuse('NONADMITTED_RAW_REFUSED')
 def test_interrupted_terminal_without_raw_preserves_null_count(self):
  self.terminal.update(status='INTERRUPTED',reason='WALL_LIMIT',output_admission='NOT_ADMITTED');self.save();d=self.inspect(False);self.assertEqual(d['terminal_status'],'INTERRUPTED');self.assertIsNone(d['raw_candidate_count']);self.assertEqual(d['raw_result_status'],'NOT_ADMITTED')
 def test_declared_zero_and_nonzero_counts_are_not_interchangeable(self):
  self.rawdata['candidate_count']=0;self.rawdata['retained_raw_candidate_count']=0;self.save();self.refuse('CANDIDATE_DENOMINATOR_INVALID')
 def test_boolean_count_is_not_zero_or_one(self):
  self.rawdata['candidate_count']=True;self.save();self.refuse('CANDIDATE_DENOMINATOR_INVALID')
 def test_native_returncode_and_cleanup_uncertainty_gate_counts(self):
  original=copy.deepcopy(self.terminal)
  for change in [dict(returncode=True),dict(returncode=7),dict(supervision_cleanup_uncertain=True),dict(cleanup_errors=['EPERM'])]:
   self.terminal=dict(original,**change);self.save()
   with self.subTest(change=change):self.refuse('TERMINAL_NOT_ADMITTED')
 def test_rebound_raw_cannot_promote_annotation_coordinates_or_membership(self):
  original=copy.deepcopy(self.rawdata)
  for change in [dict(hmm_annotation='VALIDATED'),dict(candidate_membership='VERIFIED'),dict(coordinate_provenance='PRODUCER_VERIFIED'),dict(biological_absence_inferred=True)]:
   self.rawdata=dict(original,**change);self.save()
   with self.subTest(change=change):self.refuse('RAW_QUALIFICATION_INVALID')
 def test_candidate_promotion_and_identity_reassignment_refused(self):
  self.rawdata['candidates'][0]['candidate_membership']='VERIFIED';self.save();self.refuse('CANDIDATE_QUALIFICATION_INVALID')
  self.rawdata['candidates'][0]['candidate_membership']='UNVERIFIED';self.rawdata['candidates'][0]['source_fields']['aaseq']='M'+'G'*19;self.save();self.refuse('CANDIDATE_IDENTITY_INVALID')
 def test_complete_nine_column_raw_contract_required(self):
  original=copy.deepcopy(self.rawdata)
  for index,(key,value) in enumerate([('species',None),('ppstrand',True),('ppstrand',0),('testrand',1.0),('pptedist',-1),('pptedist',False),('score',float('nan')),('score',float('inf')),('score',True),('score','1.0')]):
   self.out=self.work/('inspection-'+str(index));self.rawdata=copy.deepcopy(original);self.rawdata['candidates'][0]['source_fields'][key]=value;self.save()
   with self.subTest(key=key,value=value):self.refuse('RAW_FIELDS_INVALID')
 def test_missing_or_extra_raw_columns_refused(self):
  original=copy.deepcopy(self.rawdata)
  for mutation in ('missing','extra'):
   self.out=self.work/('inspection-'+mutation);self.rawdata=copy.deepcopy(original);fields=self.rawdata['candidates'][0]['source_fields']
   if mutation=='missing':fields.pop('species')
   else:fields['HMM_NAME']='invented'
   self.save()
   with self.subTest(mutation=mutation):self.refuse('RAW_FIELDS_INVALID')
 def test_zero_retained_after_te_match_is_not_no_te_hit(self):
  self.terminal['status']=self.rawdata['status']='NO_RETAINED_CANDIDATES';self.rawdata.update(candidate_count=0,retained_raw_candidate_count=0,candidates=[]);self.rawdata['source_declaration'].update(state='TE_MATCH_NO_CANDIDATE_ROWS_UNATTESTED',candidate_rows_declared=0);self.save();d=self.inspect();self.assertEqual(d['raw_result_status'],'NO_RETAINED_CANDIDATES');self.assertEqual(d['raw_candidate_count'],0);self.assertFalse(d['biological_absence_inferred'])
 def test_no_te_hit_and_zero_retained_declarations_cannot_be_relabelled(self):
  self.terminal['status']=self.rawdata['status']='NO_HIT';self.rawdata.update(candidate_count=0,retained_raw_candidate_count=0,candidates=[]);self.rawdata['source_declaration'].update(state='TE_MATCH_NO_CANDIDATE_ROWS_UNATTESTED',candidate_rows_declared=0);self.save();self.refuse('SOURCE_DECLARATION_CONTRADICTION')
 def test_receipt_embedded_paths_are_not_followed(self):
  self.terminal['sources']=[{'path':'/Network/UNREQUESTED_TEST_INPUT','sha256':'0'*64}];self.rawdata['sources']=[{'path':'/Network/UNREQUESTED_TEST_INPUT','sha256':'0'*64}];self.save();original=a.load_bytes
  def load(path):
   if str(path).startswith('/Network'):raise AssertionError('Unrequested path followed')
   return original(path)
  with patch.object(a,'load_bytes',load):d=self.inspect()
  self.assertEqual(d['raw_candidate_count'],2);self.assertEqual(len(d['sources']),2)
 def test_malformed_execution_value_is_typed_refusal(self):
  self.terminal['upstream_execution']=[];self.save();self.refuse('TERMINAL_QUALIFICATION_INVALID')
 def test_cli_logs_raw_status_and_holds_without_launch(self):
  args=['native-result','--terminal',str(self.term),'--raw',str(self.raw),'--out',str(self.out)]
  with patch('subprocess.Popen',side_effect=AssertionError('No subprocess permitted')),self.assertLogs(a.LOG,level='INFO') as logs:code=a.main(args)
  self.assertEqual(code,0);text=' '.join(logs.output);self.assertIn('SUCCESS_UNBOUND',text);self.assertIn('HMM=NOT_RUN_SEPARATE_STAGE',text);self.assertIn('canonical_import=NOT_ADMITTED',text)
 def test_cli_failed_inspection_records_state_with_nonzero_exit(self):
  self.terminal.update(status='FAILED',returncode=7,reason='EXIT_NONZERO',output_admission='NOT_ADMITTED');self.save();code=a.main(['native-result','--terminal',str(self.term),'--out',str(self.out)]);self.assertEqual(code,2);d=json.loads((self.out/'NATIVE_RESULT.json').read_text());self.assertIsNone(d['raw_candidate_count']);self.assertEqual(d['terminal_status'],'FAILED')
 def test_staging_success_shape_is_not_canonical_publication(self):
  self.terminal['terminal_publication']['canonical_name']='TERMINAL.json';self.save();self.refuse('UNCOMMITTED_TERMINAL_FILE')
 def test_legacy_success_requires_outer_invocation_control(self):
  self.terminal.pop('terminal_publication');self.save();self.refuse('LEGACY_PUBLICATION_CONTROL_REQUIRED')
 def test_legacy_control_failure_cannot_promote_complete_success_json(self):
  self.terminal.pop('terminal_publication');self.save();p=self.work/'control.json';p.write_text(json.dumps(dict(status='FAILED',returncode=7)))
  with self.assertRaisesRegex(ValueError,'CONTROL_NOT_ADMITTED'):m.native_result(a.binding_api(),self.term,self.raw,self.out,p)
  self.assertFalse(self.out.exists())
 def test_cli_reads_actual78row_fabricated_result_without_native_repeat(self):
  terminal=os.environ.get('RIPPER_ACTUAL_NATIVE_TERMINAL');raw=os.environ.get('RIPPER_ACTUAL_NATIVE_RAW');control=os.environ.get('RIPPER_ACTUAL_NATIVE_CONTROL')
  if not terminal or not raw or not control:self.skipTest('explicit actual retained native files not selected')
  before={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [terminal,raw]}
  with patch('subprocess.Popen',side_effect=AssertionError('Native scope consumed')):code=a.main(['native-result','--terminal',terminal,'--raw',raw,'--control-result',control,'--out',str(self.out)])
  self.assertEqual(code,0);d=json.loads((self.out/'NATIVE_RESULT.json').read_text());self.assertEqual(d['raw_candidate_count'],78);self.assertEqual(d['lexical_channel_counts'],{'main':3,'distant':75});self.assertEqual(d['candidate_membership'],'UNVERIFIED');self.assertEqual(d['coordinate_status'],'ABSENT_PRODUCER_MAPPING')
  self.assertEqual(before,{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before})
if __name__=='__main__':unittest.main()
