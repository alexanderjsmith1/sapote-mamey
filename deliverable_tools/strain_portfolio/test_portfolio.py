import copy, importlib.util, json, tempfile, unittest, subprocess, sys, os
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('portfolio_builder',Path(__file__).with_name('build_portfolio.py'))
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)
def row():
 return dict(population='frozen45',strain='TEST-001',full_node='contig_alpha',region='region001',bgc_alias='cluster-a',exact_identity='TEST-001 / contig_alpha / region001 / cluster-a',run_id='a'*64,families=['NRPS','NRPS'],tailoring=['oxygenase'],ks=0,c=1,a=2,exact_genes=3,linked_genes=2,boundary_genes=1,touches_source_edge=None)
class PortfolioTests(unittest.TestCase):
 def test_overlap_and_denominators(self):
  g=m.summarize([row()])[0];self.assertEqual(g['families'],{'NRPS':1});self.assertEqual(g['exact_genes'],3);self.assertEqual(g['boundary_genes'],1);self.assertEqual(g['edge_known'],0)
 def test_cross_process_hash_seed(self):
  code="import importlib.util;from pathlib import Path;s=importlib.util.spec_from_file_location('p',"+repr(str(Path(__file__)))+");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);r=m.row();r['families']=['alpha','beta','gamma'];print(m.m.render({'portfolios':m.m.summarize([r])}))"
  values=[subprocess.check_output([sys.executable,'-B','-c',code],env={**os.environ,'PYTHONHASHSEED':seed})for seed in ['1','23']]
  self.assertEqual(*values)
 def test_duplicate_refused(self):
  with self.assertRaisesRegex(ValueError,'DUPLICATE'):m.summarize([row(),row()])
 def test_alternate_runs_separate(self):
  b=row();b['run_id']='b'*64;self.assertEqual(len(m.summarize([row(),b])),2)
 def test_wrong_contig_refused(self):
  b=row();b['full_node']='different_assembly'
  with self.assertRaisesRegex(ValueError,'IDENTITY_CONFLICT'):m.summarize([b])
 def test_missing_identity(self):
  b=row();b['region']=''
  with self.assertRaisesRegex(ValueError,'INCOMPLETE'):m.summarize([b])
 def test_mixed_population(self):
  b=row();b['population']='current46runs'
  with self.assertRaisesRegex(ValueError,'MIXED_POPULATION'):m.summarize([row(),b])
 def test_missing_not_zero(self):
  for field in ['ks','exact_genes','linked_genes']:
   b=row();b[field]=None
   with self.assertRaisesRegex(ValueError,'MISSING'):m.summarize([b])
 def test_invalid_denominator(self):
  b=row();b['linked_genes']=4
  with self.assertRaisesRegex(ValueError,'DENOMINATOR'):m.summarize([b])
 def test_tamper_and_changed_dependency(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'owner.py';p.write_text('original');entry={'path':str(p),'sha256':m.sha(p)};m.checked(entry);p.write_text('changed')
   with self.assertRaisesRegex(ValueError,'PIN_CHANGED'):m.checked(entry)
 def test_explicit_zero_vs_unknown_edge(self):
  b=row();b['touches_source_edge']=False;g=m.summarize([b])[0];self.assertEqual((g['edge_loci'],g['edge_known']),(0,1))
 def test_html_escape(self):
  h=m.render({'test':'</script><script>alert(1)</script>'});self.assertIn('\\u003c/script>',h)
 def test_resume_and_output_tamper(self):
  data={'portfolios':[],'loci':[],'denominator':{},'sources':{}}
  with tempfile.TemporaryDirectory()as td:
   m.write_outputs(data,td);m.write_outputs(data,td);(Path(td)/'portfolio.json').write_text('tampered')
   with self.assertRaisesRegex(ValueError,'OUTPUT_CONFLICT'):m.write_outputs(data,td)
if __name__=='__main__':unittest.main()
