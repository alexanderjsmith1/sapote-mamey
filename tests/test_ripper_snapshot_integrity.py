"""Synthetic SQLite generation fault; no native workflow, immutable snapshot required."""
import importlib.util,os,sqlite3,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('raw_snapshot_fixture',ROOT/'tests/test_ripper_raw_discovery.py');f=importlib.util.module_from_spec(sp);sp.loader.exec_module(f)
selected=os.environ.get('RIPPER_RAW_INTEGRITY_PREIMAGE')
if selected:
 sp=importlib.util.spec_from_file_location('raw_F4_preimage',selected);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
else:m=f.m
class SnapshotIntegrity(unittest.TestCase):
 def setUp(self):
  self.fixture=f.RawDiscovery('test_raw_candidate_is_unbound_without_hmm_or_coordinates');self.fixture.setUp();self.fixture.complete()
 def test_sqlite_rows_must_be_from_exact_hashed_bytes_not_later_generation(self):
  case=self.fixture;original=case.db.read_bytes();api=f.a.binding_api();loader=api['load_bytes'];first=True
  def read(path):
   nonlocal first
   raw=loader(path)
   if Path(path)==case.db and first:
    first=False;case.row()
   return raw
  inventory=m.stage_inventory
  def stages(*args):
   result=inventory(*args);case.db.write_bytes(original);return result
  api['load_bytes']=read
  with patch.object(m,'stage_inventory',stages),self.assertRaisesRegex(ValueError,'SQLITE_FASTA_MISMATCH'):
   m.parse_discovery(api,case.inner,case.bound,case.contract)
 def test_sqlite_snapshot_dependency_is_explicit(self):
  if selected:self.skipTest('new dependency contract belongs to F5')
  with patch.object(m.sqlite3,'Connection',object),self.assertRaisesRegex(ValueError,'SNAPSHOT_DEPENDENCY_UNAVAILABLE'):m.parse_discovery(f.a.binding_api(),self.fixture.inner,self.fixture.bound,self.fixture.contract)
if __name__=='__main__':unittest.main()
