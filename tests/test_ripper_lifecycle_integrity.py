"""Peer-derived fault controls on current owner code; only fake process interfaces."""
import hashlib,importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('integrity_adapter',ROOT/'tools/ripper_adapter.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a);m=a.owned_module('ripper_lifecycle');PROFILE=json.loads((ROOT/'tools/ripper_source_profile.json').read_text())
class FakeError(Exception):pass
class FakeNoSuch(FakeError):pass
class FakeZombie(FakeError):pass
class FakeDenied(FakeError):pass
class Child:
 pid=918273
 def __init__(self,code=0):self.returncode=code;self.waits=0
 def poll(self):return self.returncode
 def kill(self):self.returncode=-9
 def wait(self,timeout=None):self.waits+=1;return self.returncode
class Integrity(unittest.TestCase):
 def setUp(self):
  self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir())));self.root=self.work/'run';self.roles={}
  for role in ('python_runtime','stub_script','config'):
   p=self.work/role;p.write_text('SYNTHETIC_FAKE_PROCESS_ONLY\n');self.roles[role]=p
  self.roles['python_runtime'].chmod(0o700);self.child=Child();self.inspect_error=None;self.group_error=ProcessLookupError
  spec={'schema_version':'ripper-lifecycle-spec/1','mode':'synthetic_stub','profile_id':PROFILE['id'],'source_revision':PROFILE['revision'],'files':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in self.roles.items()},'limits':{'wall_seconds':1,'rss_bytes':1024**2,'disk_bytes':2*1024**2,'poll_seconds':0.01}}
  self.spec=self.work/'spec.json';self.spec.write_text(json.dumps(spec));self.header='\t'.join(PROFILE['headers'])+'\n'
 def launch(self,*args,**kwargs):
  (self.root/'result.tsv').write_text(self.header);return self.child
 def proc(self,pid):
  if self.inspect_error:raise self.inspect_error('SYNTHETIC_INSPECTION_DENIED')
  return SimpleNamespace(children=lambda recursive:[],memory_info=lambda:SimpleNamespace(rss=1))
 def kill_group(self,*args):
  if self.group_error:raise self.group_error('SYNTHETIC_GROUP_OUTCOME')
 def run_fake(self):
  psutil=SimpleNamespace(__version__='SYNTHETIC_FAKE_PROCESS',Process=self.proc,Error=FakeError,NoSuchProcess=FakeNoSuch,ZombieProcess=FakeZombie,AccessDenied=FakeDenied)
  with patch.dict(sys.modules,{'psutil':psutil}),patch.object(m.subprocess,'Popen',self.launch),patch.object(m.os,'killpg',self.kill_group):
   return m.lifecycle(a.binding_api(),self.spec,[k+'='+str(p) for k,p in self.roles.items()],self.root,execute_stub=True)
 def terminal(self):return json.loads((self.root/'TERMINAL.json').read_text())
 def test_exited_leader_permission_denial_never_admits_no_hit(self):
  self.group_error=PermissionError;d=self.run_fake();self.assertEqual(d['status'],'UNAVAILABLE');self.assertEqual(d['reason'],'SUPERVISION_UNAVAILABLE');self.assertTrue(d['cleanup_errors']);self.assertNotIn('retained_row_count',d)
 def test_final_hash_keyboard_interrupt_records_terminal(self):
  try:
   with patch.object(m,'output_binding',side_effect=KeyboardInterrupt('SYNTHETIC_FINAL_HASH_INTERRUPT')):d=self.run_fake()
  except KeyboardInterrupt:d=None
  self.assertIsNotNone(d,'Catchable final hash interrupt escaped without terminal')
  self.assertEqual(d['status'],'INTERRUPTED');self.assertEqual(self.terminal()['status'],'INTERRUPTED');self.assertEqual(self.child.waits,1)
 def test_consumed_result_cannot_disagree_with_bound_generation(self):
  original=m.output_binding
  def swapping(path,cap):
   b=original(path,cap)
   if path.name=='result.tsv':path.write_text(self.header+'SYNTHETIC\t'*10+'SYNTHETIC\n')
   return b
  with patch.object(m,'output_binding',swapping):d=self.run_fake()
  self.assertEqual(d['status'],'FAILED');self.assertNotEqual(d.get('retained_row_count'),1);self.assertEqual(d['upstream_execution'],'NOT_EXECUTED')
 def test_inspection_permission_is_capability_unavailable_not_tool_failure(self):
  self.inspect_error=FakeDenied;d=self.run_fake();self.assertEqual(d['status'],'UNAVAILABLE');self.assertEqual(d['reason'],'SUPERVISION_UNAVAILABLE');self.assertIn('INSPECTION_DENIED',d['error'])
 def test_known_absent_group_and_exact_bytes_allow_stub_scoped_no_hit(self):
  d=self.run_fake();self.assertEqual(d['status'],'NO_HIT');self.assertEqual(d['retained_row_count'],0);self.assertFalse(d['biological_absence_inferred']);self.assertEqual(d['upstream_execution'],'NOT_EXECUTED')
 def test_nonzero_remains_failed_with_unadmitted_output(self):
  self.child.returncode=7;d=self.run_fake();self.assertEqual(d['status'],'FAILED');self.assertNotIn('retained_row_count',d)
 def test_final_interrupt_preserves_cleanup_uncertainty(self):
  self.group_error=PermissionError
  try:
   with patch.object(m,'output_binding',side_effect=KeyboardInterrupt('SYNTHETIC_INTERRUPT')):d=self.run_fake()
  except KeyboardInterrupt:d=None
  self.assertIsNotNone(d,'Final interrupt escaped with cleanup uncertainty')
  self.assertTrue(d['cleanup_errors']);self.assertNotEqual(d['status'],'NO_HIT');self.assertEqual(self.terminal()['upstream_execution'],'NOT_EXECUTED')
 def test_cleanup_interrupt_is_terminal_uncertainty_not_completion(self):
  calls=0
  def waiting(timeout=None):
   nonlocal calls
   calls+=1
   if calls==1:raise KeyboardInterrupt('SYNTHETIC_CLEANUP_INTERRUPT')
   self.child.waits+=1;return self.child.returncode
  self.child.wait=waiting;d=self.run_fake();self.assertEqual(d['status'],'UNAVAILABLE');self.assertTrue(d['supervision_cleanup_uncertain']);self.assertEqual(self.terminal()['output_admission'],'NOT_ADMITTED')
 def test_permission_error_during_inspection_uses_unavailable(self):
  self.inspect_error=PermissionError;d=self.run_fake();self.assertEqual(d['status'],'UNAVAILABLE');self.assertEqual(d['reason'],'SUPERVISION_UNAVAILABLE')
 def test_capability_failure_survives_secondary_hash_error(self):
  self.inspect_error=FakeDenied
  with patch.object(m,'output_binding',side_effect=OSError('SYNTHETIC_SECONDARY_HASH_ERROR')):d=self.run_fake()
  self.assertEqual(d['status'],'UNAVAILABLE');self.assertIn('INSPECTION_DENIED',d['primary_error']);self.assertIn('SECONDARY_HASH_ERROR',d['finalization_error'])
 def test_late_output_change_before_terminal_is_refused(self):
  original=a.load_bytes;count=0
  def reading(path):
   nonlocal count
   raw=original(path)
   if Path(path)==self.roles['config']:
    count+=1
    if count==3:(self.root/'result.tsv').write_text(self.header+'SYNTHETIC\\t'*10+'SYNTHETIC\\n')
   return raw
  with patch.object(a,'load_bytes',reading):d=self.run_fake()
  self.assertEqual(d['status'],'FAILED');self.assertEqual(d['output_admission'],'NOT_ADMITTED');self.assertIn('OUTPUT_CHANGED_BEFORE_TERMINAL',d['error'])
 def test_first_terminal_write_interrupt_is_caught_and_counts_withdrawn(self):
  original=m.write_new;calls=0
  def writing(path,data):
   nonlocal calls
   if path.name in ('TERMINAL.json.staging','TERMINAL.json.recovery.staging'):
    calls+=1
    if calls==1:raise KeyboardInterrupt('SYNTHETIC_FIRST_TERMINAL_WRITE')
   return original(path,data)
  with patch.object(m,'write_new',writing):d=self.run_fake()
  self.assertEqual(calls,2);self.assertEqual(d,self.terminal());self.assertEqual(d['status'],'INTERRUPTED');self.assertEqual(d['primary_status'],'NO_HIT');self.assertNotIn('retained_row_count',d);self.assertEqual(d['output_admission'],'NOT_ADMITTED');self.assertFalse(d['biological_absence_inferred'])
 def test_partial_terminal_bytes_retained_before_recovery(self):
  original=m.write_new;calls=0;partial=b'{"partial":'
  def writing(path,data):
   nonlocal calls
   if path.name in ('TERMINAL.json.staging','TERMINAL.json.recovery.staging'):
    calls+=1
    if calls==1:
     path.write_bytes(partial);raise KeyboardInterrupt('SYNTHETIC_PARTIAL_WRITE')
   return original(path,data)
  self.group_error=PermissionError
  with patch.object(m,'write_new',writing):d=self.run_fake()
  retained=self.root/'TERMINAL.json.staging'
  self.assertEqual(retained.read_bytes(),partial);self.assertEqual(d['interrupted_terminal_write']['sha256'],hashlib.sha256(partial).hexdigest());self.assertTrue(d['supervision_cleanup_uncertain']);self.assertEqual(d['primary_status'],'UNAVAILABLE');self.assertIsNone(d['primary_reason']);self.assertEqual(d['terminal_write_prior_reason'],'SUPERVISION_UNAVAILABLE');self.assertEqual(d['cleanup_reason'],'SUPERVISION_UNAVAILABLE');self.assertEqual(d['output_admission'],'NOT_ADMITTED')
 def test_second_terminal_write_interruption_is_not_completion(self):
  original=m.write_new
  def writing(path,data):
   if path.name in ('TERMINAL.json.staging','TERMINAL.json.recovery.staging'):raise KeyboardInterrupt('SYNTHETIC_REPEATED_INTERRUPT')
   return original(path,data)
  with patch.object(m,'write_new',writing),self.assertRaises(KeyboardInterrupt):self.run_fake()
  self.assertFalse((self.root/'TERMINAL.json').exists())
 def test_execution_terminal_first_interrupt_withdraws_raw_counts(self):
  path=self.work/'EXECUTION_TERMINAL.json';d={'status':'NO_HIT','reason':None,'raw_discovery':{'candidate_count':0},'output_admission':'SCOPED_BOUND_BYTES_ONLY'};original=m.write_new;calls=0
  def writing(p,data):
   nonlocal calls
   calls+=1
   if calls==1:raise KeyboardInterrupt('SYNTHETIC_EXECUTION_WRITE')
   return original(p,data)
  with patch.object(m,'write_new',writing):m.write_terminal(path,d)
  final=json.loads(path.read_text());self.assertEqual(final['status'],'INTERRUPTED');self.assertIsNone(final['raw_discovery']['candidate_count']);self.assertEqual(final['output_admission'],'NOT_ADMITTED')
 def test_recovery_refuses_to_overwrite_existing_partial_evidence(self):
  path=self.work/'TERMINAL.json';retained=self.work/'TERMINAL.json.staging';retained.write_bytes(b'prior evidence')
  with self.assertRaises(FileExistsError):m.write_terminal(path,{'status':'NO_HIT'})
  self.assertEqual(retained.read_bytes(),b'prior evidence');self.assertFalse(path.exists())
 def test_close_io_after_complete_success_payload_never_publishes_canonical(self):
  path=self.work/'TERMINAL.json';original=m.write_new
  def writing(p,data):original(p,data);raise OSError('SYNTHETIC_CLOSE_FAILURE_AFTER_COMPLETE_JSON')
  with patch.object(m,'write_new',writing),self.assertRaises(OSError):m.write_terminal(path,{'status':'SUCCESS_UNBOUND','output_admission':'SCOPED_BOUND_BYTES_ONLY'})
  self.assertFalse(path.exists());self.assertEqual(json.loads((self.work/'TERMINAL.json.staging').read_text())['status'],'SUCCESS_UNBOUND')
 def test_interrupted_serialization_and_preservation_failure_never_publish_success(self):
  path=self.work/'TERMINAL.json';original=m.write_new
  def writing(p,data):original(p,data);raise KeyboardInterrupt('SYNTHETIC_CLOSE_INTERRUPT')
  with patch.object(m,'write_new',writing),patch.object(m,'output_binding',side_effect=OSError('SYNTHETIC_PRESERVATION_FAILURE')),self.assertRaises(OSError):m.write_terminal(path,{'status':'SUCCESS_UNBOUND','output_admission':'SCOPED_BOUND_BYTES_ONLY'})
  self.assertFalse(path.exists());self.assertTrue((self.work/'TERMINAL.json.staging').is_file())
 def test_publication_link_failure_leaves_staging_without_canonical(self):
  path=self.work/'TERMINAL.json'
  with patch.object(m.os,'link',side_effect=OSError('SYNTHETIC_PUBLICATION_FAILURE')),self.assertRaises(OSError):m.write_terminal(path,{'status':'SUCCESS_UNBOUND'})
  self.assertFalse(path.exists());self.assertTrue((self.work/'TERMINAL.json.staging').is_file())
 def test_published_terminal_is_complete_exclusive_same_inode(self):
  path=self.work/'TERMINAL.json';d={'status':'NO_HIT'};m.write_terminal(path,d)
  self.assertTrue(os.path.samefile(path,self.work/'TERMINAL.json.staging'));self.assertEqual(json.loads(path.read_text())['terminal_publication']['canonical_name'],'TERMINAL.json')
 def test_group_absence_is_recorded_without_becoming_cleanup_uncertainty(self):
  d=self.run_fake();self.assertEqual(d['status'],'NO_HIT');self.assertEqual(d['cleanup_observations']['group_signal'],'GROUP_ABSENT_AT_SIGNAL_CHECK');self.assertEqual(d['cleanup_observations']['leader_reap'],'RETURNED');self.assertFalse(d['supervision_cleanup_uncertain']);self.assertEqual(d['upstream_execution'],'NOT_EXECUTED')
 def test_successful_group_signal_request_is_distinct_from_observed_absence(self):
  self.group_error=None;d=self.run_fake();self.assertEqual(d['cleanup_observations']['group_signal'],'SIGKILL_REQUEST_SENT');self.assertEqual(d['status'],'NO_HIT');self.assertFalse(d['supervision_cleanup_uncertain'])
 def test_signal_permission_denial_retains_unavailable_with_explicit_observation(self):
  self.group_error=PermissionError;d=self.run_fake();self.assertEqual(d['cleanup_observations']['group_signal'],'SIGNAL_UNAVAILABLE');self.assertEqual(d['status'],'UNAVAILABLE');self.assertTrue(d['supervision_cleanup_uncertain']);self.assertEqual(d['output_admission'],'NOT_ADMITTED')
 def test_vanished_member_contributes_zero_and_is_counted(self):
  def missing():raise FakeNoSuch('SYNTHETIC_MEMBER_VANISHED')
  self.proc=lambda pid:SimpleNamespace(children=lambda recursive:[SimpleNamespace(memory_info=missing)],memory_info=lambda:SimpleNamespace(rss=1))
  d=self.run_fake();self.assertEqual(d['peak_sampled_rss_bytes'],1);self.assertEqual(d['rss_sampling_observations']['vanished_member_samples'],1);self.assertEqual(d['rss_sampling_observations']['zombie_member_samples'],0);self.assertEqual(d['status'],'NO_HIT');self.assertFalse(d['biological_absence_inferred'])
 def test_zombie_member_contributes_zero_and_is_distinguished(self):
  def zombie():raise FakeZombie('SYNTHETIC_ZOMBIE_MEMBER')
  self.proc=lambda pid:SimpleNamespace(children=lambda recursive:[SimpleNamespace(memory_info=zombie)],memory_info=lambda:SimpleNamespace(rss=1))
  d=self.run_fake();self.assertEqual(d['peak_sampled_rss_bytes'],1);self.assertEqual(d['rss_sampling_observations']['zombie_member_samples'],1);self.assertEqual(d['rss_sampling_observations']['vanished_member_samples'],0);self.assertEqual(d['status'],'NO_HIT')
 def test_vanished_tree_is_counted_without_inventing_rss(self):
  self.inspect_error=FakeNoSuch;d=self.run_fake();self.assertEqual(d['peak_sampled_rss_bytes'],0);self.assertEqual(d['rss_sampling_observations']['absent_tree_samples'],1);self.assertEqual(d['status'],'NO_HIT')
 def test_member_inspection_denial_is_not_a_zero_contribution(self):
  def denied():raise FakeDenied('SYNTHETIC_MEMBER_INSPECTION_DENIED')
  self.proc=lambda pid:SimpleNamespace(children=lambda recursive:[SimpleNamespace(memory_info=denied)],memory_info=lambda:SimpleNamespace(rss=1))
  d=self.run_fake();self.assertEqual(d['status'],'UNAVAILABLE');self.assertEqual(d['reason'],'SUPERVISION_UNAVAILABLE');self.assertEqual(d['rss_sampling_observations']['vanished_member_samples'],0);self.assertEqual(d['rss_sampling_observations']['zombie_member_samples'],0);self.assertEqual(d['output_admission'],'NOT_ADMITTED');self.assertNotIn('retained_row_count',d)
if __name__=='__main__':unittest.main()
