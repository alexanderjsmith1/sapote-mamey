"""Finite executable hashing; real installed BLAST inputs are optional/read-only."""
import hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('executable_adapter',ROOT/'tools/ripper_adapter.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a);m=a.run_binding_module()
class Streaming(unittest.TestCase):
 def setUp(self):
  self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir())));self.p=self.work/'synthetic_tool';self.p.write_bytes(b'S'*(3*1024**2));self.p.chmod(0o700)
 def test_reads_are_chunked_and_never_full_file(self):
  original=a.os.fdopen;sizes=[]
  class Reader:
   def __init__(self,handle):self.handle=handle
   def __enter__(self):return self
   def __exit__(self,*args):return self.handle.__exit__(*args)
   def fileno(self):return self.handle.fileno()
   def read(self,size):
    sizes.append(size)
    if not 0<size<=1024**2:raise AssertionError('unbounded executable read')
    return self.handle.read(size)
  with patch.object(a.os,'fdopen',side_effect=lambda *args:Reader(original(*args))):d=a.tool_binding(self.p,4*1024**2,10)
  self.assertEqual(d['hash_mode'],'streamed_executable');self.assertEqual(d['bytes'],3*1024**2);self.assertGreaterEqual(len(sizes),4);self.assertEqual(d['byte_budget'],4*1024**2)
 def test_invalid_budget_and_timeout_refuse_before_read(self):
  for budget,seconds in ((True,1),(0,1),(512*1024**2+1,1),(4*1024**2,True),(4*1024**2,0),(4*1024**2,float('nan')),(4*1024**2,301)):
   with self.subTest(budget=budget,seconds=seconds),self.assertRaisesRegex(ValueError,'EXECUTABLE_STREAM_BUDGET_INVALID'):a.tool_binding(self.p,budget,seconds)
 def test_byte_and_time_caps_refuse(self):
  with self.assertRaisesRegex(ValueError,'BYTE_BUDGET_EXCEEDED'):a.tool_binding(self.p,10,1)
  with patch.object(a.time,'monotonic',side_effect=[0,2]),self.assertRaisesRegex(ValueError,'TIME_BUDGET_EXCEEDED'):a.tool_binding(self.p,4*1024**2,1)
 def test_leaf_symlink_refused(self):
  link=self.work/'link';link.symlink_to(self.p)
  with self.assertRaisesRegex(ValueError,'INPUT_NOT_REGULAR'):a.tool_binding(link,4*1024**2,1)
 def test_path_replaced_during_read_refused(self):
  original=a.os.fdopen;changed=False;path=self.p
  class Reader:
   def __init__(self,h):self.h=h
   def __enter__(self):return self
   def __exit__(self,*args):return self.h.__exit__(*args)
   def fileno(self):return self.h.fileno()
   def read(self,size):
    nonlocal changed
    raw=self.h.read(size)
    if not changed:
     changed=True;path.rename(path.with_name('retained_old_generation'));path.write_bytes(b'CHANGED')
    return raw
  with patch.object(a.os,'fdopen',side_effect=lambda *args:Reader(original(*args))),self.assertRaisesRegex(ValueError,'FILE_CHANGED'):a.tool_binding(self.p,4*1024**2,10)
 def test_default_small_tool_binding_keeps_legacy_receipt_shape(self):
  d=a.tool_binding(self.p);self.assertEqual(d['hash_mode'],'bounded_tool_16MiB');self.assertEqual(set(d),{'path','bytes','sha256','hash_mode'})
 def test_publication_rehashes_selected_executable_budget(self):
  d=a.tool_binding(self.p,4*1024**2,10);self.p.write_bytes(b'CHANGED')
  with self.assertRaisesRegex(ValueError,'INPUT_CHANGED_DURING_IMPORT'):a.publish(self.work/'out',{'TEST.json':{}},[d])
  self.assertFalse((self.work/'out').exists())
 def test_binding_receipt_carries_and_rechecks_executable_policy(self):
  manifest={'schema_version':'ripper-run-binding-manifest/1','run_id':'SYNTHETIC_EXECUTABLE_BYTES_ONLY','evidence_kind':'synthetic_fixture','profile_id':'archived-e90b3e6-mergeRidePfam','source_revision':'e90b3e6e74ddee99685183ca421323737012a991','executable_byte_budget':4*1024**2,'executable_hash_timeout_seconds':10,'files':{'blastp':hashlib.sha256(self.p.read_bytes()).hexdigest()}}
  p=self.work/'manifest.json';p.write_text(json.dumps(manifest));args=['blastp='+str(self.p)];d=m.bind_run(a.binding_api(),p,args,self.work/'binding')
  self.assertEqual(d['executable_byte_budget'],4*1024**2);self.assertEqual(d['files']['blastp']['hash_mode'],'streamed_executable')
  fresh=m.verify_boundary(a.binding_api(),self.work/'binding/RUN_BINDING.json',args,[],{});self.assertEqual(fresh['upstream_execution'],'NOT_EXECUTED')
class InstalledBLAST(unittest.TestCase):
 def setUp(self):
  selected=os.environ.get('RIPPER_EXECUTABLE_TEST_INPUTS')
  if not selected:self.skipTest('explicit installed executable audit inputs not selected')
  self.inputs=json.loads(Path(selected).read_text());self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir())))
 def test_all_three_existing_blast_leaves_bind_with_explicit_finite_budget(self):
  for role,info in self.inputs.items():
   with self.subTest(role=role):
    with self.assertRaisesRegex(ValueError,'EXPLICIT_TOOL_TOO_LARGE'):a.tool_binding(info['path'])
    b=a.tool_binding(info['path'],32*1024**2,10);self.assertEqual(b['bytes'],info['bytes']);self.assertEqual(b['sha256'],info['sha256']);self.assertEqual(b['hash_mode'],'streamed_executable')
 def test_executable_budget_does_not_enlarge_config_or_model_default_cap(self):
  info=next(iter(self.inputs.values()))
  for role in ('config','pfam_model'):
   with self.subTest(role=role),self.assertRaisesRegex(ValueError,'INPUT_TOO_LARGE'):m.files(a.binding_api(),{role:info['sha256']},[role+'='+info['path']],[],None,30,32*1024**2,10)
 def test_missing_budget_does_not_silently_expand_or_borrow_model_budget(self):
  info=next(iter(self.inputs.values()))
  with self.assertRaisesRegex(ValueError,'EXPLICIT_TOOL_TOO_LARGE'):m.files(a.binding_api(),{'blastp':info['sha256']},['blastp='+info['path']],[],64*1024**2,10)
if __name__=='__main__':unittest.main()
