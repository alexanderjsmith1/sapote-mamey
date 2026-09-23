"""`--strict` must fail on a mirror that is missing or partial, not only on one that drifted.

The original exit rule was `status == "DRIFT"`. An operator who points `--strict` at a wrong
path gets exit 0 forever: the gate passes because there is nothing there to compare. A mirror
missing `AGENTS.md` entirely behaves the same way. Both are worse than drift, because drift at
least proves the check reached a file.

`NOT_CONFIGURED` stays exit 0 by design — the docstring promises a standalone bundle with no
development workspace passes, and that is the documented default, not an oversight.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("cim", ROOT / "tools" / "check_instruction_mirror.py")
cim = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cim)


def _mirror(tmp_path, surfaces):
    d = tmp_path / "workspace"
    d.mkdir()
    for name, text in surfaces.items():
        (d / name).write_text(text)
    return d


def _bundle_text(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_strict_fail_states_are_exactly_the_three_actionable_ones():
    assert cim.STRICT_FAIL_STATES == frozenset({"DRIFT", "MIRROR_MISSING", "INCOMPLETE"})
    assert "NOT_CONFIGURED" not in cim.STRICT_FAIL_STATES
    assert "IN_SYNC" not in cim.STRICT_FAIL_STATES


def test_missing_mirror_now_fails_strict(tmp_path):
    report = cim.diagnose(tmp_path / "does_not_exist")
    assert report["status"] == "MIRROR_MISSING"
    assert report["status"] in cim.STRICT_FAIL_STATES


def test_incomplete_mirror_now_fails_strict(tmp_path):
    d = _mirror(tmp_path, {"CLAUDE.md": _bundle_text("CLAUDE.md")})
    report = cim.diagnose(d)
    assert report["status"] == "INCOMPLETE"
    assert report["status"] in cim.STRICT_FAIL_STATES


def test_drift_still_fails_strict(tmp_path):
    d = _mirror(tmp_path, {"AGENTS.md": "stale\n", "CLAUDE.md": "stale\n"})
    report = cim.diagnose(d)
    assert report["status"] == "DRIFT"
    assert report["status"] in cim.STRICT_FAIL_STATES


def test_in_sync_passes_strict(tmp_path):
    d = _mirror(tmp_path, {n: _bundle_text(n) for n in cim.MIRRORED})
    report = cim.diagnose(d)
    assert report["status"] == "IN_SYNC"
    assert report["status"] not in cim.STRICT_FAIL_STATES


def test_not_configured_still_passes_strict():
    report = cim.diagnose(None)
    assert report["status"] == "NOT_CONFIGURED"
    assert report["status"] not in cim.STRICT_FAIL_STATES


def test_exit_code_is_zero_without_strict(tmp_path, monkeypatch, capsys):
    """Advisory default is unchanged: drift reports, and still exits 0."""
    d = _mirror(tmp_path, {"AGENTS.md": "stale\n", "CLAUDE.md": "stale\n"})
    assert cim.main(["--mirror", str(d)]) == 0
    assert cim.main(["--mirror", str(d), "--strict"]) == 1


def test_missing_mirror_exit_codes_end_to_end(tmp_path):
    missing = str(tmp_path / "nope")
    assert cim.main(["--mirror", missing]) == 0
    assert cim.main(["--mirror", missing, "--strict"]) == 1


def test_incomplete_mirror_exit_codes_end_to_end(tmp_path):
    """The INCOMPLETE state pinned through main(), not through the constant.

    Every other INCOMPLETE assertion in this file reads `cim.STRICT_FAIL_STATES`. That is a
    statement about a name, not about what the tool does: a call site rewritten to an inline
    set literal keeps the constant correct and silently stops honouring it. Measured -- with
    the exit rule changed to `{"DRIFT", "MIRROR_MISSING"}` and the constant left untouched,
    all eight other tests in this file still passed while a partial mirror exited 0 again.
    """
    d = _mirror(tmp_path, {"CLAUDE.md": _bundle_text("CLAUDE.md")})
    assert cim.main(["--mirror", str(d)]) == 0
    assert cim.main(["--mirror", str(d), "--strict"]) == 1
