import importlib.util,json,os,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
adapter=load('malformed_adapter',ROOT/'tools/ripper_adapter.py')
class TypedRefusalTests(unittest.TestCase):
 def setUp(self):
  root=Path(os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir()));root.mkdir(parents=True,exist_ok=True);self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=root));self.fix=ROOT/'tests/fixtures/ripper'
 def cases(self,field):
  for i,value in enumerate(([],{},False,1,None)):
   with self.subTest(field=field,value=value):
    data=json.loads((self.fix/'complete.json').read_text());data[field]=value;p=self.work/(str(i)+'.json');p.write_text(json.dumps(data)+'\n');out=self.work/('out'+str(i))
    with self.assertLogs(adapter.LOG,level='ERROR') as logs:code=adapter.main(['import','--queries',str(self.fix/'queries.json'),'--receipt',str(p),'--out',str(out)])
    self.assertEqual(code,2);self.assertFalse(out.exists());self.assertIn('RIPPER_ADAPTER_REFUSED',' '.join(logs.output))
 def test_state_nonstring_is_typed_refusal(self):self.cases('state')
 def test_provenance_nonstring_is_typed_refusal(self):self.cases('evidence_kind')
 def test_coordinate_raw_fields_wrong_type_is_typed_refusal(self):
  fixture=load('malformed_coord_fixture',ROOT/'tests/test_ripper_coordinate_binding.py')
  if not fixture.HAVE_BIO:self.skipTest('optional Biopython unavailable')
  case=fixture.CoordinateTests('test_direct_match_is_unattested_not_membership');case.setUp();d=json.loads(case.evidence_path.read_text());d['candidates'][0]['raw_fields']=[];case.evidence_path.write_text(json.dumps(d)+'\n');case.mapping['evidence_sha256']=case.sha(case.evidence_path);mapping=case.write('mapping.json',case.mapping)
  with self.assertLogs(adapter.LOG,level='ERROR') as logs:code=adapter.main(['bind-coordinates','--evidence',str(case.evidence_path),'--local-plan',str(case.plan_path),'--genbank',str(case.gbk),'--query-fasta',str(case.faa),'--mapping',str(mapping),'--out',str(case.out)])
  self.assertEqual(code,2);self.assertFalse(case.out.exists());self.assertIn('COORDINATE_RAW_FIELDS_OBJECT_REQUIRED',' '.join(logs.output))
if __name__=='__main__':unittest.main()
