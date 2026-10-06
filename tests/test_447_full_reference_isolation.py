"""Integration controls for private test clocks and import-only tool admission."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_discovery_fixture_never_replaces_shared_time():
    spec = importlib.util.spec_from_file_location('isolated_discovery_tests', ROOT / 'tests/test_447_discovery_failure_states.py')
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    original = time.sleep
    with pytest.MonkeyPatch.context() as patch:
        module = tests.load(patch)
        assert module.time is not time
        module.time.sleep(100)  # must be immediate and module-private
        assert time.sleep is original
        tests.test_exhausted_search_never_retrieves_results(patch)
        tests.test_partial_rows_survive_only_as_incomplete_evidence(patch)
        assert time.sleep is original
    assert time.sleep is original
    start = time.monotonic()
    time.sleep(.02)
    assert time.monotonic() - start >= .015


@pytest.mark.parametrize('bare', [False, True])
def test_bankio_import_preserves_path_and_resolves_shared_api(tmp_path, bare):
    # -I excludes the bundle/CWD so the bare-tools fallback is exercised honestly.
    source = '''import importlib.util, sys
from pathlib import Path
root = Path(sys.argv[1])
if sys.argv[2] == "normal": sys.path.insert(0, str(root))
before = list(sys.path)
spec = importlib.util.spec_from_file_location("synthetic_bankio", root / "tools/_bankio.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert sys.path == before
from mamey import bank_transaction as api
for name in ("hold_reader", "release_reader_locks", "reader", "lock", "prepare", "coherent", "BankError", "STORES"):
 assert getattr(m, name) is getattr(api, name), name
'''
    result = subprocess.run([sys.executable, '-I', '-c', source, str(ROOT), 'bare' if bare else 'normal'], cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert not list(tmp_path.iterdir())


def test_companion_optional_bio_absence_is_pytest_skip(tmp_path):
    source = '''import importlib.abc, runpy, sys, pytest
class AbsentBio(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname == "Bio" or fullname.startswith("Bio."): raise ModuleNotFoundError("synthetic absent Bio", name=fullname)
sys.meta_path.insert(0, AbsentBio())
try: runpy.run_path(sys.argv[1])
except pytest.skip.Exception as error:
 assert "Bio" in str(error)
else: raise AssertionError("Missing optional Bio was not skipped")
'''
    result = subprocess.run([sys.executable, '-I', '-c', source, str(ROOT / 'tests/test_447_companion_class_evidence.py')], cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
