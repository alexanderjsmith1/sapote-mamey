"""Explicit optional rich-parser refusal; no thin-feature fallback or lint bypass."""
import builtins,importlib.util,os,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
a=load('rich_parser_adapter',ROOT/'tools/ripper_adapter.py');c=a.owned_module('ripper_coordinate_binding')
class DependencyContract(unittest.TestCase):
 def missing(self):
  original=builtins.__import__
  def importer(name,*args,**kwargs):
   if name=='Bio' or name.startswith('Bio.'):raise ImportError('SYNTHETIC_MISSING_OPTIONAL_BIOPYTHON')
   return original(name,*args,**kwargs)
  return patch('builtins.__import__',side_effect=importer)
 def test_rich_loader_explicitly_refuses_missing_biopython(self):
  with self.missing(),self.assertRaisesRegex(RuntimeError,'requires optional Biopython'):a.rich_biopython_dependencies()
 def test_semantic_boundary_returns_typed_hold_before_any_thin_parse(self):
  with self.missing():d=a.validate_local_semantics('NOT_PARSED','NOT_PARSED',{})
  self.assertEqual(d['status'],'HOLD_DEPENDENCY_UNAVAILABLE');self.assertEqual(d['upstream_execution'],'NOT_EXECUTED');self.assertEqual(d['dependency'],'Biopython')
 def test_coordinate_loader_explicitly_refuses_missing_biopython(self):
  with self.missing(),self.assertRaisesRegex(RuntimeError,'requires optional Biopython'):c.rich_coordinate_reader()
 def test_coordinate_boundary_does_not_claim_a_match_without_rich_parser(self):
  f=load('rich_coordinate_fixture',ROOT/'tests/test_ripper_coordinate_binding.py')
  if not f.HAVE_BIO:self.skipTest('fixture construction needs optional Biopython')
  case=f.CoordinateTests('test_direct_match_is_unattested_not_membership');case.setUp()
  with self.missing():d=case.run_binding()
  self.assertEqual(d['import_status'],'HOLD_DEPENDENCY_UNAVAILABLE');self.assertEqual(d['assessments'][0]['status'],'HOLD_DEPENDENCY_UNAVAILABLE');self.assertEqual(d['candidate_membership'],'UNVERIFIED')
 def test_existing_lint_recognizes_actual_guards_without_magic_comment(self):
  path=os.environ.get('RIPPER_GBK_CONTRACT_TEST')
  if not path:self.skipTest('exact current guard source not selected')
  guard=load('current_gbk_contract',Path(path))
  for name in ('ripper_adapter.py','ripper_coordinate_binding.py'):
   text=(ROOT/'tools'/name).read_text()
   with self.subTest(name=name):
    self.assertNotIn('_gbk_shim',text)
    self.assertTrue(guard._explicit_dependency_refusal(text))
if __name__=='__main__':unittest.main()
