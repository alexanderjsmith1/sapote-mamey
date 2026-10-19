"""Corrupt cloned coordinate declarations; original native artifacts remain immutable."""
import copy,hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('native_coord_adapter',ROOT/'tools/ripper_adapter.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a);m=a.owned_module('ripper_native_coordinates')
class NativeCoordinates(unittest.TestCase):
 def setUp(self):
  selected=os.environ.get('RIPPER_NATIVE_COORD_PACKET');inputs=os.environ.get('RIPPER_NATIVE_COORD_INPUTS');control=os.environ.get('RIPPER_ACTUAL_NATIVE_CONTROL')
  if not selected or not inputs or not control:self.skipTest('explicit retained native coordinate packet and input roster not selected')
  self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir())));self.packet=self.work/'packet.json';self.out=self.work/'binding';self.data=json.loads(Path(selected).read_text());self.roles=json.loads(Path(inputs).read_text());self.control=control;self.save()
 def save(self):self.packet.write_text(json.dumps(self.data))
 def args(self):return [k+'='+v for k,v in self.roles.items()]
 def run_binding(self):return m.native_coordinates(a.binding_api(),self.packet,self.args(),self.out,self.control)
 def refuse(self,code):
  self.save()
  with self.assertRaisesRegex(ValueError,code):self.run_binding()
  self.assertFalse(self.out.exists())
 def test_actual78rows_keep_native_origin_and_unattested_producer(self):
  before={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in self.roles.values()}
  with patch('subprocess.Popen',side_effect=AssertionError('One native run already consumed')):d=self.run_binding()
  self.assertEqual(d['evaluated_candidate_count'],78);self.assertEqual(len({x['peptide_id'] for x in d['assessments']}),78);self.assertEqual(d['evidence_kind'],'local_adapter_observed_native');self.assertEqual(d['upstream_execution'],'EXECUTED_NATIVE_LOCAL_ADAPTER_OBSERVED');self.assertEqual(d['coordinate_evidence_origin'],'derived_from_retained_native_artifacts');self.assertFalse(d['instrumented_producer_sidecar']);self.assertEqual(d['source_raw_coordinate_provenance'],'ABSENT_PRODUCER_MAPPING');self.assertEqual(d['hmm_annotation'],'NOT_RUN_SEPARATE_STAGE');self.assertEqual(d['candidate_membership'],'UNVERIFIED');self.assertEqual(d['canonical_import'],'NOT_ADMITTED')
  self.assertEqual(before,{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before})
 def test_one_base_offset_refused_even_with_same_peptide_identity(self):
  self.data['rows'][0]['original_interval']['start_0based']+=1;self.refuse('INTERVAL_CONVERSION_OR_STRAND_MISMATCH')
 def test_reverse_interval_wrong_strand_refused(self):
  row=next(x for x in self.data['rows'] if x['original_interval']['strand']==-1);row['original_interval']['strand']=1;self.refuse('INTERVAL_CONVERSION_OR_STRAND_MISMATCH')
 def test_boolean_strand_is_not_integer_one(self):
  self.data['rows'][0]['original_interval']['strand']=True;self.refuse('INTEGER_GEOMETRY_REQUIRED')
 def test_duplicate_candidate_does_not_replace_a_missing_row(self):
  self.data['rows'][1]=copy.deepcopy(self.data['rows'][0]);self.refuse('CANONICAL_ROW_IDENTITY_DUPLICATE_OR_UNKNOWN')
 def test_row_count_cannot_be_promoted_or_boolean(self):
  original=self.data['candidate_count']
  for value in [77,True]:
   self.data['candidate_count']=value
   with self.subTest(value=value):self.refuse('EXACT_CANDIDATE_DENOMINATOR_REQUIRED')
  self.data['candidate_count']=original
 def test_fasta_header_binding_is_not_replaced_by_sequence_match(self):
  self.data['rows'][0]['fasta_header_binding']['header_line_sha256']='0'*64;self.refuse('FASTA_HEADER_SEQUENCE_BINDING_MISMATCH')
 def test_selected_score_line_content_hash_is_required(self):
  self.data['rows'][0]['score_row']['line_sha256']='0'*64;self.refuse('SCORE_ROW_CONTENT_BINDING_MISMATCH')
 def test_geometry_sha1_is_not_a_score_row_content_hash(self):
  self.data['rows'][0]['geometry_sha1']=self.data['rows'][0]['score_row']['line_sha256'][:40];self.refuse('START_OR_GEOMETRY_METADATA_MISMATCH')
 def test_source_version_alias_is_not_silently_stripped(self):
  self.data['source_record']['header_fields']['VERSION']='SYN_DISCOVERY';self.refuse('ORIGINAL_RECORD_IDENTITY_MISMATCH')
 def test_table11_scoring_model_does_not_replace_table1_peptide_translation(self):
  self.data['rows'][0]['translation_table']=11;self.refuse('SOURCE_TRANSLATION_POLICY_MISMATCH')
 def test_nucleotide_trimming_or_instrumented_producer_promotion_refused(self):
  original=copy.deepcopy(self.data)
  for change in [dict(instrumented_producer_sidecar=True),dict(candidate_membership='VERIFIED'),dict(hmm_annotation='VALIDATED'),dict(native_evidence_kind='operator_supplied')]:
   self.data=dict(original,**change)
   with self.subTest(change=change):self.refuse('PACKET_QUALIFICATION_PROMOTION')
  self.data=original;self.data['rows'][0]['nucleotide_interval_adjustment']='TRIM_TO_TRIPLET';self.refuse('ROW_QUALIFICATION_PROMOTION')
 def test_embedded_foreign_paths_are_never_followed(self):
  self.data['bindings']['genbank']['path']='/Network/UNREQUESTED_COORDINATE_INPUT';self.save();original=a.load_bytes
  def read(path):
   if str(path).startswith('/Network'):raise AssertionError('Unrequested packet path followed')
   return original(path)
  with patch.object(a,'load_bytes',read),self.assertRaisesRegex(ValueError,'EXPLICIT_FILE_BINDING_MISMATCH'):self.run_binding()
  self.assertFalse(self.out.exists())
 def test_score_row_ambiguity_is_not_resolved_by_first_match(self):
  faa=m.fasta_records(Path(self.roles['faa']).read_text());row=self.data['rows'][0];note=m.note_fields(faa[row['FastaID']]['description']);scores,table=m.score_rows(Path(self.roles['score']).read_text());matched=m.matching_scores(note,scores,row['same_strand_reward'],1);self.assertEqual(len(matched),1);self.assertEqual(len(m.matching_scores(note,scores+matched,row['same_strand_reward'],1)),2)
 def test_missing_rich_parser_is_typed_refusal_no_feature_fallback(self):
  api=a.binding_api();original=api['owned_module']
  def modules(name):
   value=original(name)
   if name=='ripper_coordinate_binding':value.rich_coordinate_reader=lambda:(_ for _ in ()).throw(RuntimeError('Biopython absent'))
   return value
  api['owned_module']=modules
  with self.assertRaisesRegex(ValueError,'RICH_PARSER_DEPENDENCY_REQUIRED'):m.native_coordinates(api,self.packet,self.args(),self.out,self.control)
  self.assertFalse(self.out.exists())
 def test_cli_logs_evaluated_coordinates_without_import_or_native_launch(self):
  argv=['native-coordinates','--packet',str(self.packet),'--control-result',self.control,'--out',str(self.out),*[x for pair in self.args() for x in ['--file',pair]]]
  with patch('subprocess.Popen',side_effect=AssertionError('Native scope consumed')),self.assertLogs(a.LOG,level='INFO') as logs:code=a.main(argv)
  self.assertEqual(code,0);self.assertIn('evaluated=78',' '.join(logs.output));self.assertIn('BGC_membership=UNVERIFIED',' '.join(logs.output))
class PureCoordinateRefusals(unittest.TestCase):
 def seq_class(self):
  try:from Bio.Seq import Seq
  except ImportError:self.skipTest('optional Biopython unavailable; strict coordinate translation is not exercised')
  return Seq
 def test_malformed_sqlite_is_typed_refusal(self):
  with self.assertRaisesRegex(ValueError,'SQLITE_READ_REFUSED'):m.sqlite_rows(b'not SQLite','ripper',[('acc','TEXT')])
 def test_nontriplet_interval_is_refused_instead_of_trimmed(self):
  Seq=self.seq_class()
  with self.assertRaisesRegex(ValueError,'NONTRIPLET_INTERVAL_REFUSED'):m.translated_interval(Seq('ATGAAAT'),1,'ATG')
 def test_initial_valine_adjustment_changes_amino_acid_only(self):
  Seq=self.seq_class()
  text,unadjusted,translated,changes=m.translated_interval(Seq('GTGGCTTAA'),1,'GTG');self.assertEqual(text,'GTGGCTTAA');self.assertEqual(unadjusted,'VA*');self.assertEqual(translated,'MA');self.assertIn('initial_V_or_L_to_M_without_coordinate_shift',changes)
 def test_reverse_translation_preserves_interval_without_codon_shift(self):
  Seq=self.seq_class()
  text,unadjusted,translated,changes=m.translated_interval(Seq('TTAAGCCAC'),-1,'GTG');self.assertEqual(text,'GTGGCTTAA');self.assertEqual(translated,'MA')
 def test_duplicate_score_header_is_refused(self):
  header='\t'.join(m.HEADER)
  with self.assertRaisesRegex(ValueError,'SCORE_HEADER_DUPLICATE'):m.score_rows(header+'\n'+header+'\n')
if __name__=='__main__':unittest.main()
