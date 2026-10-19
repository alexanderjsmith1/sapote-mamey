"""Coherently rebound raw/normalized contradictions; synthetic mappings only."""
import copy,hashlib,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('cross_field_fixture',ROOT/'tests/test_ripper_coordinate_binding.py');f=importlib.util.module_from_spec(sp);sp.loader.exec_module(f)
@unittest.skipUnless(f.HAVE_BIO,'strict coordinate validation needs optional Biopython')
class CrossFields(unittest.TestCase):
 def setUp(self):
  self.case=f.CoordinateTests('test_direct_match_is_unattested_not_membership');self.case.setUp();self.evidence=json.loads(self.case.evidence_path.read_text());self.candidate=self.evidence['candidates'][0];self.candidate['raw_fields'].update(Accession=self.candidate['enzyme_accession'],FastaID=self.candidate['peptide_id'],Sequence=self.candidate['sequence'])
 def evaluate(self):
  self.case.evidence_path.write_text(json.dumps(self.evidence)+'\n');self.case.mapping['evidence_sha256']=self.case.sha(self.case.evidence_path);return self.case.run_binding()
 def refuse(self,code):
  with self.assertRaisesRegex(ValueError,code):self.evaluate()
  self.assertFalse(self.case.out.exists())
 def test_three_mirror_fields_cannot_contradict_normalized_with_rebound_hash(self):
  for field,value in (('Accession','DIFFERENT_TE'),('FastaID','DIFFERENT_TE_1'),('Sequence','M')):
   old=self.candidate['raw_fields'][field];self.candidate['raw_fields'][field]=value
   with self.subTest(field=field):self.refuse('RAW_IDENTITY_SEQUENCE_MISMATCH')
   self.candidate['raw_fields'][field]=old
 def test_simultaneous_peer_contradiction_refused(self):
  self.candidate['raw_fields'].update(Accession='DIFFERENT_TE',FastaID='DIFFERENT_TE_1',Sequence='M');self.refuse('RAW_IDENTITY_SEQUENCE_MISMATCH')
 def test_partial_mirror_removal_refused(self):
  self.candidate['raw_fields'].pop('Sequence');self.refuse('RAW_IDENTITY_SEQUENCE_INCOMPLETE')
 def test_archived_profile_cannot_drop_all_mirror_fields(self):
  self.evidence['source_profile']={'id':'archived-e90b3e6-mergeRidePfam'}
  self.candidate['raw_fields']={'PPSerial':'1'};self.refuse('RAW_IDENTITY_SEQUENCE_INCOMPLETE')
 def test_wrong_typed_raw_sequence_refused(self):
  self.candidate['raw_fields']['Sequence']=[];self.refuse('RAW_IDENTITY_SEQUENCE_MISMATCH')
 def test_matching_fields_keep_unattested_coordinate_scope(self):
  d=self.evaluate();self.assertEqual(d['assessments'][0]['status'],'DIRECT_SEQUENCE_MATCH_UNATTESTED');self.assertEqual(d['assessments'][0]['raw_identity_consistency'],'MATCHED_DECLARED_RAW_IDENTITY_SEQUENCE');self.assertEqual(d['candidate_membership'],'UNVERIFIED')
 def test_legacy_minimal_declaration_is_explicitly_unverified_not_upgraded(self):
  self.candidate['raw_fields']={'PPSerial':'1'};d=self.evaluate();self.assertEqual(d['assessments'][0]['raw_identity_consistency'],'NOT_DECLARED_LEGACY_MINIMAL_INPUT');self.assertEqual(d['upstream_execution'],'NOT_EXECUTED_SYNTHETIC')
 def test_identical_sequence_distinct_serial_ids_are_preserved(self):
  second=copy.deepcopy(self.candidate);second['peptide_id']='SYNTHETIC_TE_2';second['raw_fields'].update(PPSerial='2',FastaID='SYNTHETIC_TE_2');self.evidence['candidates'].append(second);self.evidence['candidate_count']=2
  row=dict(self.case.mapping['mappings'][0],FastaID='SYNTHETIC_TE_2',PPSerial='2',local_start_1based=301,local_end_inclusive=363);self.case.mapping['mappings'].append(row)
  d=self.evaluate();self.assertEqual(d['candidate_count'],2);self.assertEqual([x['peptide_id'] for x in d['assessments']],['SYNTHETIC_TE_1','SYNTHETIC_TE_2']);self.assertTrue(all(x['status']=='DIRECT_SEQUENCE_MATCH_UNATTESTED' for x in d['assessments']))
if __name__=='__main__':unittest.main()
