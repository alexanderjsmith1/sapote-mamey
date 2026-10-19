"""Self-authored tiny Python stubs only. No RiPPER, BLAST, HMM or Perl execution."""
import hashlib,importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('lifecycle_adapter',ROOT/'tools/ripper_adapter.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a);m=a.owned_module('ripper_lifecycle');PROFILE=json.loads((ROOT/'tools/ripper_source_profile.json').read_text())
class Lifecycle(unittest.TestCase):
 def setUp(self):
  self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir())));self.root=self.work/'fresh_run'
  self.script=self.work/'self_authored_stub.py';self.config=self.work/'synthetic.conf';self.config.write_text('SYNTHETIC_NOT_UPSTREAM\n')
  self.script.write_text('from pathlib import Path\nimport sys\nPath(sys.argv[1]).write_text('+repr('\t'.join(PROFILE['headers'])+'\n')+')\n')
  self.roles={'python_runtime':Path(sys.executable).resolve(),'stub_script':self.script,'config':self.config}
  # Explicit finite streaming budget: Python executables vary across CI distributions.
  self.executable_budget=max(16*1024**2,self.roles['python_runtime'].stat().st_size)
  self.spec={'schema_version':'ripper-lifecycle-spec/1','mode':'synthetic_stub','profile_id':PROFILE['id'],'source_revision':PROFILE['revision'],'limits':{'wall_seconds':2,'rss_bytes':128*1024**2,'disk_bytes':2*1024**2,'poll_seconds':0.01}}
  self.spec['executable_byte_budget']=self.executable_budget
 def run_stub(self,execute=True,cancel=None):
  self.spec['files']={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in self.roles.items()};p=self.work/'spec.json';p.write_text(json.dumps(self.spec))
  return m.lifecycle(a.binding_api(),p,[k+'='+str(p) for k,p in self.roles.items()],self.root,execute_stub=execute,cancel_path=cancel)
 def test_default_preflight_launches_nothing(self):
  with patch.object(m.subprocess,'Popen',side_effect=AssertionError('must not launch')):d=self.run_stub(False)
  self.assertEqual(d['status'],'NOT_EXECUTED');self.assertFalse((self.root/'STARTED.json').exists());self.assertEqual(d['upstream_execution'],'NOT_EXECUTED')
 def test_header_only_is_stub_scoped_no_hit(self):
  d=self.run_stub();self.assertEqual(d['status'],'NO_HIT');self.assertFalse(d['biological_absence_inferred']);self.assertEqual(d['upstream_execution'],'NOT_EXECUTED');self.assertEqual(d['candidate_bgc_membership'],'UNVERIFIED')
  self.assertEqual(set(d['retained_outputs']),{'stdout.log','stderr.log','result.tsv'});self.assertTrue((self.root/'TERMINAL.json').is_file())
 def test_retained_stub_row_is_unbound(self):
  self.script.write_text('from pathlib import Path\nimport sys\nPath(sys.argv[1]).write_text('+repr('\t'.join(PROFILE['headers'])+'\n'+'\t'.join(['SYNTHETIC']*11)+'\n')+')\n')
  d=self.run_stub();self.assertEqual(d['status'],'SUCCESS_UNBOUND');self.assertEqual(d['retained_row_count'],1)
 def test_nonzero_and_missing_and_empty_output_are_failed(self):
  for code in ('raise SystemExit(7)\n','pass\n','from pathlib import Path\nimport sys\nPath(sys.argv[1]).write_text(\'\')\n'):
   with self.subTest(code=code):
    self.root=self.work/('run'+str(len(list(self.work.iterdir()))));self.script.write_text(code);d=self.run_stub();self.assertEqual(d['status'],'FAILED')
 def test_cancel_before_launch_is_interrupted(self):
  cancel=self.work/'cancel';cancel.touch()
  with patch.object(m.subprocess,'Popen',side_effect=AssertionError('must not launch')):d=self.run_stub(cancel=str(cancel))
  self.assertEqual(d['status'],'INTERRUPTED');self.assertEqual(d['stub_execution'],'NOT_EXECUTED')
 def test_cancel_running_child_and_no_surviving_pid(self):
  cancel=self.work/'cancel';self.script.write_text('from pathlib import Path\nimport time\nPath('+repr(str(cancel))+').touch()\ntime.sleep(4)\n')
  d=self.run_stub(cancel=str(cancel));self.assertEqual(d['reason'],'CANCEL_REQUESTED')
  import psutil
  self.assertFalse(psutil.pid_exists(d['pid']))
 def test_wall_limit_kills_child(self):
  self.script.write_text('import time\ntime.sleep(4)\n');self.spec['limits']['wall_seconds']=0.08;d=self.run_stub();self.assertEqual(d['status'],'INTERRUPTED');self.assertEqual(d['reason'],'WALL_LIMIT')
 def test_rss_limit_tiny_stub_is_interrupted(self):
  self.script.write_text('import time\nx=bytearray(4*1024*1024)\ntime.sleep(1)\n');self.spec['limits']['rss_bytes']=1;d=self.run_stub();self.assertEqual(d['reason'],'RSS_LIMIT')
 def test_disk_limit_tiny_stub_is_interrupted(self):
  self.script.write_text('from pathlib import Path\nimport time\nPath(\'oversize\').write_bytes(b\'X\'*65536)\ntime.sleep(1)\n');self.spec['limits']['disk_bytes']=32768;d=self.run_stub();self.assertEqual(d['reason'],'DISK_LIMIT')
 def test_existing_root_never_overwritten(self):
  self.root.mkdir();sentinel=self.root/'keep';sentinel.write_text('keep')
  with self.assertRaisesRegex(ValueError,'FRESH_ABSOLUTE_ROOT'):self.run_stub()
  self.assertEqual(sentinel.read_text(),'keep')
 def test_missing_explicit_role_unavailable_and_no_child(self):
  del self.roles['stub_script']
  with patch.object(m.subprocess,'Popen',side_effect=AssertionError('must not launch')):d=self.run_stub()
  self.assertEqual(d['status'],'UNAVAILABLE')
 def test_nan_bool_and_unbounded_limits_refused(self):
  for bad in (float('nan'),True,0,3601):
   self.spec['limits']['wall_seconds']=bad
   with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'LIMIT_INVALID'):self.run_stub()
 def test_stale_hash_refused_before_artifact_creation(self):
  api=a.binding_api();original=api['binding']
  def changed(path,raw):
   b=original(path,raw)
   if Path(path)==self.config:b['sha256']='0'*64
   return b
  with patch.object(a,'binding',side_effect=changed),self.assertRaisesRegex(ValueError,'DIGEST_MISMATCH'):self.run_stub()
  self.assertFalse(self.root.exists())
 def test_child_input_mutation_fails_post_run_receipt(self):
  self.script.write_text('from pathlib import Path\nPath('+repr(str(self.config))+').write_text(\'changed\')\n')
  d=self.run_stub();self.assertEqual(d['status'],'FAILED')
 def test_keyboard_interrupt_stops_child_and_writes_terminal(self):
  self.script.write_text('import time\ntime.sleep(4)\n')
  original=m.disk_size
  with patch.object(m,'disk_size',side_effect=[KeyboardInterrupt(),0]):d=self.run_stub()
  self.assertEqual(d['status'],'INTERRUPTED');self.assertEqual(d['reason'],'KEYBOARD_INTERRUPT');self.assertTrue((self.root/'TERMINAL.json').exists())

class LifecycleAdditional(unittest.TestCase):
 setUp=Lifecycle.setUp
 run_stub=Lifecycle.run_stub
 def test_group_cleanup_stops_descendant(self):
  cancel=self.work/'cancel';pidfile=self.root/'descendant.pid'
  self.script.write_text('from pathlib import Path\nimport subprocess,sys,time\np=subprocess.Popen([sys.executable,\'-I\',\'-S\',\'-B\',\'-c\',\'import time; time.sleep(4)\'])\nPath('+repr(str(pidfile))+').write_text(str(p.pid))\ntime.sleep(0.03)\nPath('+repr(str(cancel))+').touch()\ntime.sleep(4)\n')
  d=self.run_stub(cancel=str(cancel));self.assertEqual(d['status'],'INTERRUPTED')
  import psutil
  pid=int(pidfile.read_text())
  try:live=psutil.Process(pid).status()!=psutil.STATUS_ZOMBIE
  except psutil.NoSuchProcess:live=False
  self.assertFalse(live)
 def test_missing_optional_psutil_is_unavailable_before_launch(self):
  import builtins
  original=builtins.__import__
  def missing(name,*args,**kwargs):
   if name=='psutil':raise ImportError('synthetic unavailable')
   return original(name,*args,**kwargs)
  with patch('builtins.__import__',side_effect=missing),patch.object(m.subprocess,'Popen',side_effect=AssertionError('must not launch')):d=self.run_stub()
  self.assertEqual(d['status'],'UNAVAILABLE');self.assertIn('optional_psutil',d['missing'])
 def test_cli_default_preflight_records_no_execution(self):
  self.run_stub(False);self.root=self.work/'cli'
  args=['lifecycle','--spec',str(self.work/'spec.json'),'--run-root',str(self.root)]
  for k,p in self.roles.items():args.extend(['--file',k+'='+str(p)])
  self.assertEqual(a.main(args),0);self.assertEqual(json.loads((self.root/'TERMINAL.json').read_text())['stub_execution'],'NOT_EXECUTED')
 def test_child_mutation_with_valid_output_fails_exact_input_check(self):
  header='\t'.join(PROFILE['headers'])+'\n'
  self.script.write_text('from pathlib import Path\nimport sys\nPath(sys.argv[1]).write_text('+repr(header)+')\nPath('+repr(str(self.config))+').write_text(\'changed\')\n')
  d=self.run_stub();self.assertEqual(d['status'],'FAILED');self.assertIn('INPUT_CHANGED_DURING_STUB',d['error'])

 def test_cli_nonzero_stub_exits_two_with_failed_receipt(self):
  self.script.write_text('raise SystemExit(7)\n');self.run_stub(False);self.root=self.work/'failed_cli'
  args=['lifecycle','--spec',str(self.work/'spec.json'),'--run-root',str(self.root),'--execute-stub']
  for k,p in self.roles.items():args.extend(['--file',k+'='+str(p)])
  self.assertEqual(a.main(args),2);self.assertEqual(json.loads((self.root/'TERMINAL.json').read_text())['status'],'FAILED')


 def test_explicit_runtime_budget_is_streamed_and_recorded(self):
  d=self.run_stub(False);bound=d['files']['python_runtime']
  self.assertEqual(bound['hash_mode'],'streamed_executable')
  self.assertEqual(bound['bytes'],self.roles['python_runtime'].stat().st_size)
  self.assertEqual(bound['byte_budget'],self.executable_budget)
  self.assertEqual(bound['hash_timeout_seconds'],30)
  self.assertEqual(d['status'],'NOT_EXECUTED')
 def test_insufficient_runtime_budget_refuses_before_artifact_creation(self):
  self.spec['executable_byte_budget']=self.roles['python_runtime'].stat().st_size-1
  with patch.object(m.subprocess,'Popen',side_effect=AssertionError('must not launch')):
   with self.assertRaisesRegex(ValueError,'EXECUTABLE_STREAM_BYTE_BUDGET_EXCEEDED'):self.run_stub(False)
  self.assertFalse(self.root.exists())
 def test_nonexecutable_runtime_is_unavailable_before_launch(self):
  runtime=self.work/'not_executable';runtime.write_text('self-authored non-executable fixture\n');runtime.chmod(0o600)
  self.roles['python_runtime']=runtime
  with patch.object(m.subprocess,'Popen',side_effect=AssertionError('must not launch')):d=self.run_stub(False)
  self.assertEqual(d['status'],'UNAVAILABLE');self.assertIn('executable:python_runtime',d['missing'])

if __name__=='__main__':unittest.main()
