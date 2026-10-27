import datetime as dt,hashlib,importlib.util,json,socket,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
TOOL=Path(__file__).resolve().parents[1]/'tools/checkpoint_status.py'
s=importlib.util.spec_from_file_location('checkpoint',TOOL);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Check(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.p=Path(self.temp.name);self.now=dt.datetime(2026,10,24,23,tzinfo=dt.timezone.utc);self.rows=[]
 def tearDown(self):self.temp.cleanup()
 def source(self,key,kind,data):
  p=self.p/(key+'.json');p.write_text(json.dumps(data));row={'id':key,'kind':kind,'path':str(p),'sha256':m.digest(p)};self.rows.append(row);return p
 def manifest(self):return {'schema':m.SCHEMA,'sources':self.rows}
 def runcheck(self):return m.build(self.manifest(),self.p,self.now,self.p)
 def goal(self):self.source('goal','goal',{'status':'ACTIVE_INDEFINITE','objective':'Keep improving'})
 def inbox(self,when=None):
  p=self.p/'ledger.tsv';p.write_text('source ledger bytes')
  self.source('inbox','inbox',{'observed_at':when or self.now.isoformat(),'source':{'path':str(p),'sha256':m.digest(p)},'open_unique_id_count':23,'unledgered_directories':['old-context'],'native_inbox_bookkeeping_check':{'status':'FAIL'}});return p
 def allocation(self,**kwargs):
  data={'schema':'sapote.scheduler-allocation.v1','host_id':socket.gethostname(),'observed_at':self.now.isoformat(),'allocated_cores':2,'queue':'review queue'};data.update(kwargs);self.source('allocation','allocation',data)
 def test_goal_stays_active_with_complete_milestone(self):
  self.goal();self.source('done','receipt',{'status':'COMPLETE'});r=self.runcheck();self.assertEqual(r['goal']['reported_status'],'ACTIVE_INDEFINITE');self.assertEqual(r['QC_receipts'][0]['scientific_acceptance'],'NOT_ESTABLISHED')
 def test_current_inbox_count_and_unledgered_hold(self):
  self.goal();self.inbox();r=self.runcheck();self.assertEqual(r['inbox']['current_open_count'],23);self.assertEqual(r['inbox']['native_check']['status'],'FAIL');self.assertTrue(any('unledgered' in x['action'] for x in r['next_actions']))
 def test_changed_live_ledger_requires_refresh(self):
  self.goal();p=self.inbox();p.write_text('updated');r=self.runcheck();self.assertIsNone(r['inbox']['current_open_count']);self.assertEqual(r['inbox']['ledger_binding'],'LIVE_LEDGER_CHANGED')
 def test_stale_inbox_not_current(self):
  self.goal();self.inbox((self.now-dt.timedelta(hours=2)).isoformat());r=self.runcheck();self.assertEqual(r['inbox']['reported_open_count'],23);self.assertIsNone(r['inbox']['current_open_count'])
 def test_future_inbox_time_holds(self):
  self.goal();self.inbox((self.now+dt.timedelta(hours=1)).isoformat());self.assertEqual(self.runcheck()['inbox']['age_state'],'FUTURE_TIME_HOLD')
 def test_unoffset_clock_not_guessed(self):
  self.goal();self.inbox('2026-10-24T23:00:00');self.assertEqual(self.runcheck()['inbox']['age_state'],'TIME_UNAVAILABLE')
 def test_missing_goal_unknown_never_complete(self):
  p=self.source('goal','goal',{'status':'ACTIVE'});p.unlink();r=self.runcheck();self.assertEqual(r['goal']['reported_status'],'UNAVAILABLE');self.assertEqual(r['sources'][0]['byte_state'],'MISSING')
 def test_changed_receipt_not_reused(self):
  self.goal();p=self.source('receipt','receipt',{'status':'PASS'});p.write_text('{"status":"PASS"} ');r=self.runcheck();self.assertEqual(r['QC_receipts'],[]);self.assertEqual(r['sources'][1]['byte_state'],'CHANGED')
 def test_logical_cpus_not_allocation(self):
  self.goal();r=self.runcheck();self.assertIsNone(r['resources']['allocated_cores']);self.assertEqual(r['resources']['queue'],'UNAVAILABLE')
 def test_bound_allocation_presented_as_reported(self):
  self.goal();self.allocation();self.assertEqual(self.runcheck()['resources']['allocated_cores'],2)
 def test_wrong_host_allocation_holds(self):
  self.goal();self.allocation(host_id='another-host');self.assertEqual(self.runcheck()['resources']['allocation_state'],'DIFFERENT_HOST')
 def test_stale_allocation_holds(self):
  self.goal();self.allocation(observed_at=(self.now-dt.timedelta(hours=1)).isoformat());self.assertIsNone(self.runcheck()['resources']['allocated_cores'])
 def test_boolean_not_core_allocation(self):
  self.goal();self.allocation(allocated_cores=True);self.assertEqual(self.runcheck()['resources']['allocation_state'],'INVALID_ALLOCATION')
 def test_nonfinite_not_core_allocation(self):
  self.goal();self.allocation(allocated_cores=float('nan'));self.assertEqual(self.runcheck()['resources']['allocation_state'],'INVALID_ALLOCATION')
 def test_duplicate_id_refused(self):
  self.goal();self.rows.append(self.rows[0].copy())
  with self.assertRaisesRegex(ValueError,'SOURCE_ID'):self.runcheck()
 def test_ambiguous_goal_refused(self):
  self.goal();self.source('other','goal',{'status':'COMPLETE'})
  with self.assertRaisesRegex(ValueError,'AMBIGUOUS'):self.runcheck()
 def test_pinned_deliverable_does_not_establish_ready(self):
  self.goal();self.source('report','deliverable',{'status':'READY'});r=self.runcheck();self.assertEqual(r['deliverables'][0]['byte_state'],'HASH_MATCH');self.assertNotIn('ready',r['deliverables'][0])
 def test_unpinned_source_holds(self):
  self.goal();self.rows[0]['sha256']='';self.assertEqual(self.runcheck()['sources'][0]['byte_state'],'BASELINE_UNPINNED')
 def test_byte_budget_no_partial_pass(self):
  self.goal();manifest=self.manifest();manifest['max_source_bytes']=1;r=m.build(manifest,self.p,self.now,self.p);self.assertEqual(r['sources'][0]['byte_state'],'UNVERIFIED_BYTE_BUDGET')
 def test_low_disk_flag_and_no_fake_queue(self):
  self.goal()
  with patch.object(m.shutil,'disk_usage',return_value=type('Usage',(),{'free':10})()):r=self.runcheck()
  self.assertEqual(r['resources']['disk_state'],'BELOW_FLOOR');self.assertTrue(any(x['source']=='disk' for x in r['next_actions']))
 def test_source_bytes_unchanged(self):
  self.goal();p=self.inbox();before=m.digest(p);self.runcheck();self.assertEqual(before,m.digest(p))
 def card(self,artifact):
  self.source('card','receipt',{'schema':'sapote.delivery_capability_card.result.v1','status':'EVIDENCE_CARD_WITH_HOLDS','artifact':artifact,'checks':[{'kind':'program_behavior','state':'BOUND_REPORTED_PASS'},{'kind':'browser_compatibility','state':'NOT_PERFORMED'}]})
 def test_card_target_rechecked_only_when_listed(self):
  self.goal();p=self.source('viewer','deliverable',{'payload':'view'});self.card({'path':str(p),'actual_sha256':m.digest(p)});r=self.runcheck();self.assertEqual(r['QC_receipts'][0]['target_state'],'TARGET_BYTES_RECHECKED');self.assertEqual(r['QC_receipts'][0]['reported_checks'][1]['state'],'NOT_PERFORMED')
 def test_card_target_omission_not_silently_rechecked(self):
  self.goal();self.card({'path':str(self.p/'unlisted'),'actual_sha256':'a'*64});self.assertEqual(self.runcheck()['QC_receipts'][0]['target_state'],'TARGET_NOT_LISTED')
 def test_changed_card_target_does_not_inherit_pass(self):
  self.goal();p=self.source('viewer','deliverable',{'payload':'view'});self.card({'path':str(p),'actual_sha256':m.digest(p)});p.write_text('changed');self.assertEqual(self.runcheck()['QC_receipts'][0]['target_state'],'TARGET_CHANGED_OR_UNVERIFIED')
 def test_human_summary_keeps_unknown_count_and_allocation(self):
  self.goal();self.inbox((self.now-dt.timedelta(hours=2)).isoformat());text=m.markdown(self.runcheck());self.assertIn('Current pending count: **unknown**',text);self.assertIn('Allocated cores: unknown',text);self.assertIn('Reported historical count: 23',text)
 def test_manifest_surface_is_declared_not_adopted(self):
  self.goal();self.source('patch','patch',{'code':'candidate'});self.rows[-1]['surface']='custom work';text=m.markdown(self.runcheck());self.assertIn('custom work',text);self.assertIn('does not establish readiness',text)
 def test_markdown_table_values_escaped(self):
  self.goal();self.source('patch','patch',{});self.rows[-1]['surface']='custom|work\nother';text=m.markdown(self.runcheck());self.assertIn('custom\\|work other',text)
if __name__=='__main__':unittest.main()
