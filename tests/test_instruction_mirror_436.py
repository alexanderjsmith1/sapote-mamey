"""tools/check_instruction_mirror.py: diagnose a configured contract mirror without touching it.

The prior proposal for this problem was declined because its check failed on a clean standalone
candidate (no AGENTS.md in the parent) and because its cut step wrote outside the bundle. Both
failure modes are pinned here so a later revision cannot reintroduce them.
"""
import hashlib
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
_TOOL = ROOT / "tools" / "check_instruction_mirror.py"
_spec = importlib.util.spec_from_file_location("check_instruction_mirror", _TOOL)
mod = importlib.util.module_from_spec(_spec)
sys.modules["check_instruction_mirror"] = mod
_spec.loader.exec_module(mod)


def _mirror(tmp_path, agents=None, claude=None):
    d = tmp_path / "workspace"
    d.mkdir()
    (d / "AGENTS.md").write_text(agents if agents is not None else (ROOT / "AGENTS.md").read_text())
    (d / "CLAUDE.md").write_text(claude if claude is not None else (ROOT / "CLAUDE.md").read_text())
    return d


def test_unconfigured_is_not_an_error():
    """A standalone bundle with no mirror configured must pass. This is the failure that
    disqualified the previous proposal."""
    r = mod.diagnose(None)
    assert r["status"] == "NOT_CONFIGURED"
    assert mod.main([]) == 0


def test_missing_mirror_directory_is_advisory(tmp_path):
    r = mod.diagnose(tmp_path / "does_not_exist")
    assert r["status"] == "MIRROR_MISSING"
    assert mod.main(["--mirror", str(tmp_path / "does_not_exist")]) == 0


def test_identical_mirror_is_in_sync(tmp_path):
    r = mod.diagnose(_mirror(tmp_path))
    assert r["status"] == "IN_SYNC"
    assert {s["state"] for s in r["surfaces"]} == {"IN_SYNC"}


def test_stale_mirror_is_reported_as_drift(tmp_path):
    d = _mirror(tmp_path, agents="# stale copy from an older cut\n")
    r = mod.diagnose(d)
    assert r["status"] == "DRIFT"
    agents = next(s for s in r["surfaces"] if s["surface"] == "AGENTS.md")
    assert agents["state"] == "DRIFT"
    assert agents["bundle_sha256"] != agents["mirror_sha256"]


def test_drift_is_advisory_by_default_and_hard_only_on_opt_in(tmp_path):
    d = _mirror(tmp_path, agents="# stale\n")
    assert mod.main(["--mirror", str(d)]) == 0, "drift must not fail a release by default"
    assert mod.main(["--mirror", str(d), "--strict"]) == 1, "--strict is the operator's opt-in"


def test_absent_surface_in_mirror_is_incomplete_not_drift(tmp_path):
    d = _mirror(tmp_path)
    (d / "CLAUDE.md").unlink()
    r = mod.diagnose(d)
    assert r["status"] == "INCOMPLETE"


def test_the_tool_never_writes_anything(tmp_path):
    """Read-only is the whole premise: repairing a workspace is an explicit owner action."""
    d = _mirror(tmp_path, agents="# stale\n")
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in d.rglob("*") if p.is_file()}
    bundle_before = hashlib.sha256((ROOT / "AGENTS.md").read_bytes()).hexdigest()
    mod.main(["--mirror", str(d)])
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in d.rglob("*") if p.is_file()}
    assert before == after, "the tool modified the mirror"
    assert hashlib.sha256((ROOT / "AGENTS.md").read_bytes()).hexdigest() == bundle_before
    assert not (d / "AGENTS.md.bak").exists()
