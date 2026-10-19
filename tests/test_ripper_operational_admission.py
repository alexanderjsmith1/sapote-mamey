"""Synthetic byte/admission controls; no real upstream/model/tool execution."""
import hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('operational_adapter',ROOT/'tools/ripper_adapter.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
r=a.run_binding_module();s=a.owned_module('ripper_source_admission')
class OperationalAdmission(unittest.TestCase):
 def setUp(self):
  self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir())))
 def write(self,name,raw):
  p=self.work/name;p.write_bytes(raw if isinstance(raw,bytes) else raw.encode());return p
 def test_six_megabyte_model_is_streamed_only_with_explicit_budget(self):
  p=self.write('synthetic.model',b'S'*(6*1024**2));decl={'pfam_model':hashlib.sha256(p.read_bytes()).hexdigest()};args=['pfam_model='+str(p)]
  with self.assertRaisesRegex(ValueError,'INPUT_TOO_LARGE'):r.files(a.binding_api(),decl,args,[])
  sources=[];bound=r.files(a.binding_api(),decl,args,sources,8*1024**2,10)
  self.assertEqual(bound['pfam_model']['hash_mode'],'streamed_model');self.assertEqual(bound['pfam_model']['bytes'],6*1024**2)
  a.publish(self.work/'out',{'TEST.json':{'model_validation':'BYTES_ONLY'}},sources)
  self.assertEqual([p.name for p in (self.work/'out').iterdir()],['TEST.json'])
 def test_same_large_config_refused_even_with_model_budget(self):
  p=self.write('large.conf',b'X'*(6*1024**2))
  with self.assertRaisesRegex(ValueError,'INPUT_TOO_LARGE'):r.files(a.binding_api(),{'config':hashlib.sha256(p.read_bytes()).hexdigest()},['config='+str(p)],[],8*1024**2)
 def test_stream_caps_symlink_and_time_controls(self):
  p=self.write('model',b'ABC');link=self.work/'link';link.symlink_to(p)
  for budget,seconds in ((True,1),(0,1),(2,1),(10,False),(10,float('nan'))):
   with self.subTest(budget=budget,seconds=seconds),self.assertRaises(ValueError):a.stream_binding(p,budget,seconds)
  with self.assertRaisesRegex(ValueError,'INPUT_NOT_REGULAR'):a.stream_binding(link,10)
  with patch.object(a.time,'monotonic',side_effect=[0,2]),self.assertRaisesRegex(ValueError,'TIME_BUDGET'):a.stream_binding(p,10,1)
 def test_mutating_model_between_bind_and_publish_refused(self):
  p=self.write('model',b'ABC');b=a.stream_binding(p,100);p.write_bytes(b'ABD')
  with self.assertRaisesRegex(ValueError,'INPUT_CHANGED'):a.publish(self.work/'out',{'T.json':{}},[b])
  self.assertFalse((self.work/'out').exists())
 def test_patch_context_counts_postimage_and_multifile_controls(self):
  base='A\nB\n';diff='--- original\n+++ proposed\n@@ -1,2 +1,2 @@\n A\n-B\n+C\n'
  self.assertEqual(s.apply_patch_text(base,diff),'A\nC\n')
  for broken in (diff.replace('-B','-Q'),diff.replace('-1,2','-1,3'),diff+'--- second\n+++ second\n@@ -1 +1 @@\n-A\n+Z\n'):
   with self.subTest(broken=broken),self.assertRaises(ValueError):s.apply_patch_text(base,broken)
 def test_adapted_profile_wrong_shape_is_typed_refusal(self):
  for obj in ({},[],{'schema_version':'ripper-adapted-source-profile/1','profile_status':'EXPLICIT_LOCAL_ADAPTATION_REVIEW_ONLY'}):
   p=self.write('profile.json',json.dumps(obj))
   with self.subTest(obj=obj),self.assertRaises(ValueError):s.verify_adapted(a.binding_api(),p,{},[])
 def test_original_operator_pin_never_admits_arbitrary_adaptation(self):
  p=self.write('source',b'# adapted source not upstream\n');manifest={'schema_version':'ripper-run-binding-manifest/1','run_id':'SYNTHETIC','evidence_kind':'operator_supplied','profile_id':'archived-e90b3e6-mergeRidePfam','source_revision':'e90b3e6e74ddee99685183ca421323737012a991','files':{'upstream_source':hashlib.sha256(p.read_bytes()).hexdigest()}}
  m=self.write('m.json',json.dumps(manifest))
  with self.assertRaisesRegex(ValueError,'ARCHIVED_SOURCE_PIN_MISMATCH'):r.bind_run(a.binding_api(),m,['upstream_source='+str(p)],self.work/'out')
 def test_owner_receipt_nested_malformed_shape_refused(self):
  # Reject on original archived-base pin first; no fixture pretends to be original bytes.
  owner=self.write('receipt.json',json.dumps({'provenance':[]}));base=self.write('base',b'not archived');diff=self.write('patch',b'not patch');post=self.write('post',b'not adapted')
  with self.assertRaisesRegex(ValueError,'ARCHIVED_BASE_MISMATCH'):s.admit_adapted_profile(a.binding_api(),owner,base,diff,post,self.work/'out')

class SelectedAdaptation(unittest.TestCase):
 def setUp(self):
  selected=os.environ.get('RIPPER_ADAPTED_TEST_INPUTS')
  if not selected:self.skipTest('explicit archived/adapted inputs not selected')
  self.inputs=json.loads(Path(selected).read_text());self.work=Path(tempfile.mkdtemp(prefix='selected-adaptation-',dir=os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir())))
 def admit(self,owner=None):
  x=self.inputs;d=s.admit_adapted_profile(a.binding_api(),owner or x['adaptation_receipt'],x['archived_base'],x['source_patch'],x['upstream_source'],self.work/'profile')
  return d,self.work/'profile/ADAPTED_SOURCE_PROFILE.json'
 def args(self):return [k+'='+v for k,v in self.inputs.items()]
 def test_actual05_patch_relation_and_separate_operator_profile(self):
  d,p=self.admit();self.assertEqual(d['profile_status'],'EXPLICIT_LOCAL_ADAPTATION_REVIEW_ONLY');self.assertEqual(d['upstream_execution'],'NOT_EXECUTED')
  manifest={'schema_version':'ripper-run-binding-manifest/1','run_id':'SYNTHETIC_BYTE_REVIEW_ONLY','evidence_kind':'operator_supplied','profile_id':d['base_profile_id'],'source_revision':d['base_revision'],'files':{k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in self.inputs.items()}}
  q=self.work/'manifest.json';q.write_text(json.dumps(manifest))
  with self.assertRaisesRegex(ValueError,'ARCHIVED_SOURCE_PIN_MISMATCH'):r.bind_run(a.binding_api(),q,self.args(),self.work/'unselected')
  b=r.bind_run(a.binding_api(),q,self.args(),self.work/'bound',p);self.assertEqual(b['source_binding_status'],'EXPLICIT_LOCAL_ADAPTATION_REVIEW_ONLY');self.assertEqual(b['binding_status'],'HOLD_REQUIRED_FILE_ROLES')
  fresh=r.verify_boundary(a.binding_api(),self.work/'bound/RUN_BINDING.json',self.args(),[],{},adapted_profile_path=p);self.assertEqual(fresh['adaptation']['adapted_source_sha256'],d['adapted_source_sha256'])
  with self.assertRaisesRegex(ValueError,'EXPLICIT_ADAPTED_PROFILE_REQUIRED'):r.verify_boundary(a.binding_api(),self.work/'bound/RUN_BINDING.json',self.args(),[],{})
 def test_actual_base_with_malformed_owner_provenance_typed_refusal(self):
  p=self.work/'bad.json';p.write_text(json.dumps({'provenance':[]}))
  with self.assertRaisesRegex(ValueError,'OWNER_RECEIPT_INVALID'):self.admit(p)
 def test_actual_profile_cannot_drop_explicit_role_or_rebind_patch(self):
  d,p=self.admit();sources=[];bound=r.files(a.binding_api(),{k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in self.inputs.items()},self.args(),sources)
  for role in ('archived_base','source_patch','upstream_source','adaptation_receipt'):
   missing=dict(bound);missing.pop(role)
   with self.subTest(role=role),self.assertRaisesRegex(ValueError,'EXPLICIT_FILE_BINDING_MISMATCH'):s.verify_adapted(a.binding_api(),p,missing,[])
 def test_adapted_native_preflight_remains_unavailable_without_native_roles(self):
  d,p=self.admit();spec={'schema_version':'ripper-lifecycle-spec/1','mode':'adapted_local05','profile_id':d['base_profile_id'],'source_revision':d['base_revision'],'files':{k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in self.inputs.items()},'limits':{'wall_seconds':1,'rss_bytes':1024**2,'disk_bytes':1024**2,'poll_seconds':0.01}}
  q=self.work/'spec.json';q.write_text(json.dumps(spec));l=a.owned_module('ripper_lifecycle')
  with patch.object(l.subprocess,'Popen',side_effect=AssertionError('no native launch')):out=l.lifecycle(a.binding_api(),q,self.args(),self.work/'native_preflight',p)
  self.assertEqual(out['status'],'HOLD');self.assertEqual(out['upstream_execution'],'NOT_EXECUTED');self.assertIn('HOLD_LOCAL_SOURCE_EXECUTION_ADMISSION',out['holds'])
  with self.assertRaisesRegex(ValueError,'STUB_EXECUTION_MODE_REQUIRED'):l.lifecycle(a.binding_api(),q,self.args(),self.work/'refused',p,True)

if __name__=='__main__':unittest.main()
