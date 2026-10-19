import importlib.util,json,os,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('operator_adapter',ROOT/'tools/ripper_adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class OperatorTests(unittest.TestCase):
 def test_missing_dependency_action_never_says_ready(self):
  action=a.operator_actions(dict(schema_version='ripper-local-plan/1',semantic_validation={'status':'HOLD_DEPENDENCY_UNAVAILABLE'}))[0]
  self.assertIn('already admitted',action);self.assertIn('not a pass',action)
 def test_ambiguous_mapping_action_does_not_pick_location(self):
  action=a.operator_actions(dict(schema_version='ripper-coordinate-binding/1',assessments=[{'status':'AMBIGUOUS_DECLARED_MAPPINGS'}]))[0]
  self.assertIn('do not choose',action)
 def test_interrupted_action_does_not_become_negative(self):
  action=a.operator_actions(dict(schema_version='ripper-evidence/2',declared_upstream_state='INTERRUPTED'))[0]
  self.assertIn('INTERRUPTED',action);self.assertIn('biological absence',action)
 def test_profile_export_does_not_contaminate_column_map(self):
  root=Path(os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir()));root.mkdir(parents=True,exist_ok=True);out=Path(tempfile.mkdtemp(prefix='operator-profile-',dir=root))/'out'
  d=a.write_profile('archived-e90b3e6-mergeRidePfam',out)
  self.assertIn('operator_next_actions',d);self.assertEqual(set(json.loads((out/'columns.json').read_text())),{'enzyme_accession','peptide_id','sequence'})
 def test_source_mismatch_action_requires_profile_admission(self):
  self.assertIn('separate adapted-profile admission',a.refusal_action('RUN_BINDING_ARCHIVED_SOURCE_PIN_MISMATCH'))
if __name__=='__main__':unittest.main()
