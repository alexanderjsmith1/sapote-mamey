"""Missing/interrupted/stale outcomes stay distinct; no upstream process executes."""
import hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('outcome_adapter',ROOT/'tools/ripper_adapter.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
FIX=ROOT/'tests/fixtures/ripper'
class OutcomeTests(unittest.TestCase):
 def setUp(self):
  root=Path(os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir()));root.mkdir(parents=True,exist_ok=True);self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=root));self.out=self.work/'out'
  self.q=FIX/'queries.json';self.columns=FIX/'columns.json';self.conf=FIX/'synthetic.conf';self.log=FIX/'synthetic_completion.log';self.raw=FIX/'synthetic.tsv';self.receipt=json.loads((FIX/'complete.json').read_text())
 def write_receipt(self):
  p=self.work/'receipt.json';p.write_text(json.dumps(self.receipt)+'\n');return p
 def run_import(self):return adapter.import_results(self.q,self.write_receipt(),self.out,self.raw,self.columns,self.conf,self.log)
 def test_missing_and_interrupted_receipts_are_null_not_negative(self):
  for state in ('MISSING','INTERRUPTED','FAILED','NOT_RUN','UNAVAILABLE'):
   self.receipt['state']=state;p=self.write_receipt();data=adapter.import_results(self.q,p,self.work/state)
   self.assertEqual(data['evidence_outcome'],state);self.assertIsNone(data['candidate_count']);self.assertFalse(data['biological_absence_inferred'])
   self.assertTrue(all(x['retained_candidate_count'] is None for x in data['assessments']))
 def test_stale_rows_cannot_accompany_interruption(self):
  self.receipt['state']='INTERRUPTED'
  with self.assertRaisesRegex(ValueError,'NONCOMPLETE_RESULTS_NOT_ADMITTED'):self.run_import()
  self.assertFalse(self.out.exists())
 def test_empty_raw_complete_is_refused(self):
  self.raw=self.work/'empty.tsv';self.raw.write_bytes(b'');self.receipt['raw_sha256']=hashlib.sha256(b'').hexdigest()
  with self.assertRaisesRegex(ValueError,'UPSTREAM_TSV_HEADER_MISMATCH'):self.run_import()
  self.assertFalse(self.out.exists())
 def test_header_only_is_scoped_no_retained_rows_not_absence(self):
  text='accession\tpid\taa\tuncalibrated_score\n';self.raw=self.work/'header.tsv';self.raw.write_text(text);self.receipt['raw_sha256']=hashlib.sha256(text.encode()).hexdigest();data=self.run_import()
  self.assertEqual(data['evidence_outcome'],'NO_RETAINED_ROWS_DECLARED_SCOPE');self.assertEqual(data['candidate_count'],0);self.assertFalse(data['biological_absence_inferred']);self.assertEqual(data['candidate_membership'],'UNVERIFIED')
 def test_changed_raw_with_old_receipt_is_refused(self):
  self.raw=self.work/'stale.tsv';self.raw.write_text((FIX/'synthetic.tsv').read_text()+'\n')
  with self.assertRaisesRegex(ValueError,'RUN_RAW_OR_CONFIG_BINDING_MISMATCH'):self.run_import()
  self.assertFalse(self.out.exists())
 def test_missing_receipt_cli_does_not_create_negative_artifact(self):
  with self.assertLogs(adapter.LOG,level='ERROR'):
   code=adapter.main(['import','--queries',str(self.q),'--receipt',str(self.work/'missing.json'),'--out',str(self.out)])
  self.assertEqual(code,2);self.assertFalse(self.out.exists())
 def test_successful_rows_remain_unbound(self):
  data=self.run_import();self.assertEqual(data['evidence_outcome'],'RETAINED_CANDIDATES_UNBOUND');self.assertEqual(data['candidate_membership'],'UNVERIFIED');self.assertEqual(data['upstream_execution'],'NOT_EXECUTED_SYNTHETIC');self.assertFalse(data['biological_absence_inferred'])
 def test_unknown_outcome_is_not_silently_assumed_complete(self):
  self.receipt['state']='KILLED_MAYBE_OK'
  with self.assertRaisesRegex(ValueError,'RUN_RECEIPT_SCHEMA_INVALID'):self.run_import()
  self.assertFalse(self.out.exists())
if __name__=='__main__':unittest.main()
