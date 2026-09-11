"""Generic annotation-view QC; fixtures contain no biological source records."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('atlas',Path(__file__).with_name('build_atlas.py'));a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class QC(unittest.TestCase):
 def test_non_enzyme_negative(self):self.assertEqual(a.classify({'description':['DNA binding protein']}),[])
 def test_family_not_specificity(self):self.assertEqual(a.classify({'description':['O-methyltransferase domain']}),['Methyltransferases'])
 def test_glycosyl_hydrolase_not_transferase(self):self.assertNotIn('Glycosyltransferases',a.classify({'description':['glycosyl hydrolase']}))
 def test_primary_metabolism_remains_broad(self):self.assertEqual(a.classify({'description':['Respiratory-chain NADH dehydrogenase']}),['Oxidoreductases'])
 def test_multiple_families(self):self.assertEqual(len(a.classify({'description':['acyltransferase dehydratase']})),2)
 def test_missing_identity(self):
  with self.assertRaises(ValueError):a.identity({'strain':'TEST'})
 def test_wrong_assembly(self):
  with self.assertRaises(ValueError):a.identity(dict(strain='TEST',full_node='contig2',region='region001',bgc_alias='cluster1',exact_identity='TEST / contig1 / region001 / cluster1'))
 def test_wrong_protein(self):
  with self.assertRaises(ValueError):a.binding_check({'protein_sha256':'a'*64},{'protein_sha256':'b'*64})
 def test_source_tamper(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'x';p.write_text('a');cfg={'inputs':{'x':{'path':str(p),'sha256':a.sha(p)}}};p.write_text('b')
   with self.assertRaises(ValueError):a.verify_inputs(cfg)
 def test_additive_resume(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'view';a.write(p,'same',td);a.write(p,'same',td)
   with self.assertRaises(ValueError):a.write(p,'changed',td)
 def test_root_escape(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(ValueError):a.write(Path(td).parent/'escape','x',td)
 def test_no_sequence_export(self):self.assertNotIn('translation',a.clean({'translation':['SECRET'],'description':['raw']}))
 def test_markup_injection(self):self.assertNotIn('</script>',a.render({'raw':'</script>'},'__ATLAS_DATA__'))
if __name__=='__main__':unittest.main()
