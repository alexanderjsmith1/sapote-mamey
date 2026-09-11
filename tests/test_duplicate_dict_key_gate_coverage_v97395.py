"""v9.7.395: two silent coverage gaps in check_duplicate_dict_keys.py.

(1) ZERO-SCAN PASS — the gate's default roots (mamey/tools/tests) are cwd-relative and
`collect()` rglob'd them without checking they exist. Run from any other working directory (or
with a typo'd --root), it scanned zero files and printed "duplicate-dict-key gate: PASS ... 0
new" with exit 0 — a coverage boundary silently read as a clean result. Reproduced live from an
empty directory on pristine .394. Now: missing roots and an empty scan are exit-2 errors, and
the PASS line reports the scanned file count.

(2) LITERAL-KEY BLINDNESS — `_const_key()` accepted only bare scalar ast.Constant keys, so a
duplicate constant TUPLE key ({("AS-1","BGC001"): x, ("AS-1","BGC001"): y} — ast.Tuple) and a
duplicate negative-number key ({-1: a, -1: b} — ast.UnaryOp) produced ZERO findings, though both
are real runtime data loss (last binding wins; verified by eval). Reproduced live on pristine
.394. Now: keys evaluate via ast.literal_eval with a hashability guard, so every literal form
follows Python's own collision semantics; computed keys are still skipped.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "check_duplicate_dict_keys.py"


def _load():
    spec = importlib.util.spec_from_file_location("cdk_coverage_ut", GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(*args, cwd=ROOT):
    return subprocess.run([sys.executable, str(GATE), *args],
                          capture_output=True, text=True, cwd=str(cwd))


# --- (2) literal-key blindness ---------------------------------------------------------------

def test_duplicate_tuple_keys_detected(tmp_path):
    m = _load()
    p = tmp_path / "t.py"
    p.write_text("PAIRS = {('AS-1','BGC001'): 'x', ('AS-1','BGC001'): 'y'}\n")
    recs = list(m.scan_file(p))
    assert len(recs) == 1 and recs[0]["entries_lost"] == 1, recs


def test_duplicate_negative_number_keys_detected(tmp_path):
    m = _load()
    p = tmp_path / "t.py"
    p.write_text("NEG = {-1: 'a', -1: 'b'}\n")
    recs = list(m.scan_file(p))
    assert len(recs) == 1 and recs[0]["entries_lost"] == 1, recs


def test_bool_int_cross_type_collision_still_detected(tmp_path):
    """The v9.7.374 behavior (1/True/1.0 are one runtime key) must survive the rewrite."""
    m = _load()
    p = tmp_path / "t.py"
    p.write_text("D = {1: 'a', True: 'b', 1.0: 'c'}\n")
    recs = list(m.scan_file(p))
    assert len(recs) == 1 and recs[0]["entries_lost"] == 2, recs


def test_computed_keys_still_skipped_no_false_positive(tmp_path):
    m = _load()
    p = tmp_path / "t.py"
    p.write_text("k = 'x'\nD = {k: 1, k: 2, some_call(): 3}\n")
    assert list(m.scan_file(p)) == []


# --- (1) zero-scan PASS ----------------------------------------------------------------------

def test_missing_default_roots_error_not_pass(tmp_path):
    """From a cwd with no mamey/tools/tests, the gate must ERROR (2), never PASS (0)."""
    r = _run(cwd=tmp_path)
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "PASS" not in r.stdout


def test_explicit_missing_root_errors(tmp_path):
    r = _run("--root", str(tmp_path / "no_such_dir"))
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)


def test_empty_root_refuses_to_pass(tmp_path):
    (tmp_path / "empty").mkdir()
    r = _run("--root", str(tmp_path / "empty"))
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "0 python files" in r.stderr


def test_shipped_tree_still_passes_and_reports_scan_count():
    r = _run()
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "duplicate-dict-key gate: PASS" in r.stdout
    assert "file(s) scanned" in r.stdout
