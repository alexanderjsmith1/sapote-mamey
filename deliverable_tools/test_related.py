import importlib.util,json,tempfile,unittest,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('related',Path(__file__).with_name('build_related.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Gates(unittest.TestCase):
 def locus(self):return dict(strain='TEST-1',full_node='contig_1',region='region001',bgc_alias='cluster1',exact_identity='TEST-1 / contig_1 / region001 / cluster1')
 def test_identity(self):self.assertEqual(m.identity(self.locus()),self.locus()['exact_identity'])
 def test_missing_identity(self):
  x=self.locus();x.pop('region')
  with self.assertRaisesRegex(ValueError,'IDENTITY'):m.identity(x)
 def test_wrong_assembly(self):
  x=self.locus();x['full_node']='other_contig'
  with self.assertRaisesRegex(ValueError,'CONFLICT'):m.identity(x)
 def test_wrong_protein(self):
  with self.assertRaisesRegex(ValueError,'PROTEIN_ROSTER'):m.validate_detail(self.locus(),[dict(membership='EXACT_REGION',locus_tag='g1',protein_sha256='a',start=1,end=10)],[dict(locus_tag='g1',protein_sha256='b')])
 def test_boundary_not_absence(self):
  genes=[dict(membership='OVERLAPPING_BOUNDARY',locus_tag='g1',protein_sha256='a',start=1,end=10)]
  check=m.validate_detail(self.locus(),genes,[]);self.assertEqual(check['exact_genes'],0);self.assertEqual(check['boundary_context_genes'],1)
 def test_duplicate_gene(self):
  g=dict(membership='EXACT_REGION',locus_tag='g1',protein_sha256='a',start=1,end=10)
  with self.assertRaisesRegex(ValueError,'PROTEIN_ROSTER'):m.validate_detail(self.locus(),[g,g],[g])
 def test_run_hold(self):
  row=dict(state=m.ADMITTED,database_sha256='a',run_id=1)
  self.assertFalse(m.eligible(row,dict(database_sha256='a',run_id=1,end_time=None)))
 def test_cross_run(self):
  row=dict(state=m.ADMITTED,database_sha256='a',run_id=1)
  self.assertFalse(m.eligible(row,dict(database_sha256='a',run_id=2,end_time='recorded')))
 def test_unadmitted(self):
  row=dict(state='OBSERVED_UNADMITTED',database_sha256='a',run_id=1)
  self.assertFalse(m.eligible(row,dict(database_sha256='a',run_id=1,end_time='recorded')))
 def test_population(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'cfg.json';p.write_text(json.dumps(dict(population='current44base',sources={})))
   with self.assertRaisesRegex(ValueError,'POPULATION'):m.build(p,Path(t)/'out')
 def test_dependency_tamper(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'cfg.json';d=Path(t)/'dep';d.write_text('changed');p.write_text(json.dumps(dict(population='frozen45',sources={'reader':{'path':str(d),'sha256':'0'*64}})))
   with self.assertRaisesRegex(ValueError,'HASH'):m.build(p,Path(t)/'out')
if __name__=='__main__':unittest.main()
