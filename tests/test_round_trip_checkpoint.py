import csv,datetime as dt,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
TOOL=Path(__file__).resolve().parents[1]/'tools/round_trip_checkpoint.py'
spec=importlib.util.spec_from_file_location('rt',TOOL);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def table(p,rs):
    with p.open('w') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]),delimiter='\t');w.writeheader();w.writerows(rs)
class Check(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_missing_ledger_is_unknown(self):
        self.assertEqual(m.inbox(self.p,dt.datetime.now(m.ZONE))['open_count'],None)
    def test_aging_duplicates_and_orphans_preserved(self):
        inbox=self.p/'00 Inbox';inbox.mkdir();(inbox/'a').mkdir();(inbox/'unbooked').mkdir()
        table(inbox/'INBOX_LEDGER.tsv',[{'id':'a','status':'ACCEPTED','submitted':'2026-10-21 09:00','verified':'2026-10-22 09:00','submitter':'one','verifier':'two'}, {'id':'a','status':'SUBMITTED','submitted':'2026-10-23 09:00','verified':'','submitter':'one','verifier':''}])
        before=m.sha(inbox/'INBOX_LEDGER.tsv');r=m.inbox(self.p,dt.datetime(2026,10,24,10,tzinfo=m.ZONE))
        self.assertEqual(r['open_row_count'],2);self.assertEqual(r['open_unique_id_count'],1);self.assertEqual(r['duplicate_live_ids'],['a']);self.assertEqual(r['unledgered_directories'],['unbooked']);self.assertTrue(r['waiting'][0]['accepted_over_24h']);self.assertEqual(before,m.sha(inbox/'INBOX_LEDGER.tsv'))
    def test_withdrawn_history_is_not_live_duplicate(self):
        inbox=self.p/'00 Inbox';inbox.mkdir();(inbox/'a').mkdir()
        table(inbox/'INBOX_LEDGER.tsv',[{'id':'a','status':'WITHDRAWN','submitted':'','verified':''},{'id':'a','status':'SUBMITTED','submitted':'invalid','verified':''}])
        r=m.inbox(self.p,dt.datetime.now(m.ZONE));self.assertEqual(r['duplicate_live_ids'],[]);self.assertIsNone(r['waiting'][0]['age_hours'])
    def setup_return(self):
        root=self.p/'returns';root.mkdir();(root/'x.txt').write_text('returned bytes');digest=m.sha(root/'x.txt')
        sent=self.p/'sent.tsv';table(sent,[{'member':'x','sha256':'a'*64,'bytes':'1'},{'member':'y','sha256':'b'*64,'bytes':'1'}])
        row={'item_id':'x','sent_sha256':'a'*64,'returned_path':'x.txt','returned_sha256':digest,'decision':'PENDING'}
        return root,sent,row
    def result(self,root,sent,row):
        back=self.p/'return.tsv';table(back,[row]);return m.reconcile(sent,back,root)
    def test_good_bytes_still_pending(self):
        root,sent,row=self.setup_return();r=self.result(root,sent,row);self.assertEqual(r['status'],'BYTE_BINDINGS_CHECKED');self.assertEqual(r['not_returned_ids'],['y']);self.assertEqual(r['rows'][0]['acceptance'],'NOT_ESTABLISHED')
    def test_baseline_change(self):
        root,sent,row=self.setup_return();row['sent_sha256']='c'*64;self.assertIn('BASELINE_MISMATCH',self.result(root,sent,row)['rows'][0]['issues'])
    def test_changed_return(self):
        root,sent,row=self.setup_return();(root/'x.txt').write_text('mutated');self.assertIn('RETURN_BYTES_MISMATCH',self.result(root,sent,row)['rows'][0]['issues'])
    def test_escape(self):
        root,sent,row=self.setup_return();row['returned_path']='../sent.tsv';self.assertIn('RETURN_PATH_ESCAPES_ROOT',self.result(root,sent,row)['rows'][0]['issues'])
    def test_symlink_escape(self):
        root,sent,row=self.setup_return();(root/'link').symlink_to(sent);row['returned_path']='link';self.assertIn('RETURN_PATH_ESCAPES_ROOT',self.result(root,sent,row)['rows'][0]['issues'])
    def test_duplicate_return(self):
        root,sent,row=self.setup_return();back=self.p/'return.tsv';table(back,[row,row]);self.assertTrue(all('DUPLICATE_RETURN_ID' in r['issues'] for r in m.reconcile(sent,back,root)['rows']))
    def test_missing_return_not_nohit(self):
        root,sent,row=self.setup_return();row['returned_path']='missing';self.assertIn('RETURN_FILE_UNAVAILABLE',self.result(root,sent,row)['rows'][0]['issues'])
    def test_external_acceptance_assertion_refused(self):
        root,sent,row=self.setup_return();row['decision']='ACCEPTED';self.assertIn('UNSUPPORTED_DECISION',self.result(root,sent,row)['rows'][0]['issues'])
    def test_core_allocation_unknown(self):self.assertIsNone(m.resources(self.p)['allocated_core_budget'])
    def test_no_returns_not_complete(self):
        root,sent,row=self.setup_return();back=self.p/'return.tsv';back.write_text('item_id\tsent_sha256\treturned_path\treturned_sha256\tdecision\n');self.assertEqual(m.reconcile(sent,back,root)['status'],'NO_RETURNS_PENDING')
    def test_malformed_baseline_refused(self):
        root,sent,row=self.setup_return();table(sent,[{'member':'x','sha256':'not-a-hash'}]);back=self.p/'return.tsv';table(back,[row])
        with self.assertRaisesRegex(ValueError,'PIN_REQUIRED'):m.reconcile(sent,back,root)
if __name__=='__main__':unittest.main()
