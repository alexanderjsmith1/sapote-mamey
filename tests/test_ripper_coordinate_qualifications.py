"""Exact provenance controls on tiny synthetic declarations; no live RiPPER."""
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('qual_coordinate_fixture',ROOT/'tests/test_ripper_coordinate_binding.py');fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
@unittest.skipUnless(fixture.HAVE_BIO,'optional Biopython unavailable')
class QualificationTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CoordinateTests('test_direct_match_is_unattested_not_membership');self.case.setUp();self.evidence=json.loads(self.case.evidence_path.read_text())
 def evaluate(self):
  self.case.evidence_path.write_text(json.dumps(self.evidence)+'\n');self.case.mapping['evidence_sha256']=self.case.sha(self.case.evidence_path);return self.case.run_binding()
 def refuse(self,code):
  with self.assertRaisesRegex(ValueError,code):self.evaluate()
  self.assertFalse(self.case.out.exists())
 def test_valid_synthetic_pair_and_legacy_candidate_remain_unexecuted(self):
  d=self.evaluate();self.assertEqual(d['upstream_execution'],'NOT_EXECUTED_SYNTHETIC');self.assertEqual(d['assessments'][0]['evidence_kind'],'synthetic_fixture');self.assertEqual(d['candidate_membership'],'UNVERIFIED')
 def test_artificial_operator_pair_remains_unattested(self):
  self.evidence.update(evidence_kind='operator_supplied',upstream_execution='OPERATOR_DECLARED_UNATTESTED');d=self.evaluate();self.assertEqual(d['assessments'][0]['upstream_execution'],'OPERATOR_DECLARED_UNATTESTED');self.assertEqual(d['mapping_authentication'],'UNATTESTED_DECLARATIONS')
 def test_synthetic_crossed_with_operator_execution_refused(self):
  self.evidence['upstream_execution']='OPERATOR_DECLARED_UNATTESTED';self.refuse('EVIDENCE_QUALIFICATION_PAIR_MISMATCH')
 def test_operator_crossed_with_synthetic_execution_refused(self):
  self.evidence['evidence_kind']='operator_supplied';self.refuse('EVIDENCE_QUALIFICATION_PAIR_MISMATCH')
 def test_candidate_crossed_pair_refused(self):
  self.evidence['candidates'][0].update(evidence_kind='synthetic_fixture',upstream_execution='OPERATOR_DECLARED_UNATTESTED');self.refuse('CANDIDATE_QUALIFICATION_PAIR_MISMATCH')
 def test_valid_candidate_pair_different_from_parent_refused(self):
  self.evidence['candidates'][0].update(evidence_kind='operator_supplied',upstream_execution='OPERATOR_DECLARED_UNATTESTED');self.refuse('CANDIDATE_QUALIFICATION_PAIR_MISMATCH')
 def test_incomplete_candidate_qualification_refused(self):
  self.evidence['candidates'][0]['evidence_kind']='synthetic_fixture';self.refuse('CANDIDATE_QUALIFICATION_INCOMPLETE')
 def test_matching_candidate_pair_accepted_with_holds(self):
  self.evidence['candidates'][0].update(evidence_kind='synthetic_fixture',upstream_execution='NOT_EXECUTED_SYNTHETIC');d=self.evaluate();self.assertEqual(d['assessments'][0]['status'],'DIRECT_SEQUENCE_MATCH_UNATTESTED');self.assertIn('HOLD_BGC_MEMBERSHIP_NOT_ESTABLISHED',d['holds'])
 def test_nonstring_top_kind_is_typed_refusal(self):
  self.evidence['evidence_kind']=[];self.refuse('EVIDENCE_QUALIFICATION_PAIR_MISMATCH')
if __name__=='__main__':unittest.main()
