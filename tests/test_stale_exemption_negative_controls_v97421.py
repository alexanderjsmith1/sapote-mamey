"""Regression controls for active and obsolete file exemptions."""
from pathlib import Path
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 spec=importlib.util.spec_from_file_location("guard_under_test",ROOT/"tests"/name)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
@pytest.mark.parametrize("rel",["tools/public_release_audit.py","tests/public/test_public_release_v9_7_381.py","tests/public/test_release_audit_fails_closed_v9_7_381.py","tests/test_hooks_workspace_portability.py","mamey/workspace_root.py","tests/test_workspace_root.py"])
def test_former_exemption_no_longer_hides_planted_path(tmp_path,rel):
 mod=load("test_workspace_path_portability.py");mod.ROOT=tmp_path
 p=tmp_path/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("value = "+repr(mod.HARDCODED+"/fixture")+"\n")
 with pytest.raises(AssertionError,match="bare hardcoded workspace path"):
  mod.test_no_bare_workspace_path_in_code()
def test_environment_lookup_remains_allowed(tmp_path):
 mod=load("test_workspace_path_portability.py");mod.ROOT=tmp_path
 p=tmp_path/"generic.py";p.write_text("value = os.getenv('SAPOTE_WORKSPACE_ROOT', "+repr(mod.HARDCODED+"/fixture")+")\n")
 mod.test_no_bare_workspace_path_in_code()

def test_plain_allowlist_missing_file_is_stale(tmp_path):
 mod=load("test_410_csv_writer_coverage.py");mod.BUNDLE_ROOT=tmp_path;mod.PLAIN_WRITER_ALLOWLIST={"mamey/missing.py"}
 with pytest.raises(AssertionError,match="stale"):
  mod.test_plain_writer_allowlist_is_not_stale()
def test_plain_allowlist_live_writer_remains_allowed(tmp_path):
 mod=load("test_410_csv_writer_coverage.py");mod.BUNDLE_ROOT=tmp_path;mod.PLAIN_WRITER_ALLOWLIST={"mamey/valid.py"}
 p=tmp_path/"mamey/valid.py";p.parent.mkdir();p.write_text("csv.writer(stream)\n")
 mod.test_plain_writer_allowlist_is_not_stale()
