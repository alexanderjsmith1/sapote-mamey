"""v9.7.395: regression tests for tools/strict_source_disclosure_audit.py — the opt-in strict
pass over the two surfaces public_release_audit deliberately skips (python source content, and
the tests/ tree).

Charter (Codex privacy audit B-003): a default-gate PASS proves the gate did not look at these
surfaces — a real cohort exclusions payload sat in tests/fixtures/ through every prior PASS.
This module widens the scan using ONLY the existing policy owners' predicates
(redact_public_tier.private_id_matches, tools/test_synthetic_ids.txt, public_release_audit's
skip/identity lists). It must never override the default gate's own scope decisions — an id in
a doc file outside tests/ stays the default gate's jurisdiction and is asserted NOT re-reported
here.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "strict_source_disclosure_audit.py"


def _load():
    spec = importlib.util.spec_from_file_location("strict_source_disclosure_ut", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["strict_source_disclosure_ut"] = mod
    spec.loader.exec_module(mod)
    return mod


def _root(tmp_path: Path, synthetic="AS-901\nAS-123\n") -> Path:
    (tmp_path / "mamey").mkdir()
    (tmp_path / "mamey" / "__init__.py").write_text('__version__ = "1.0.0"\n')
    (tmp_path / "BUILD_STAMP.txt").write_text("build=test\n")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "test_synthetic_ids.txt").write_text(synthetic)
    (tmp_path / "tests").mkdir()
    return tmp_path


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, cwd=str(ROOT))


# --- the B-003 blindnesses, closed -----------------------------------------------------------

def test_real_id_in_tests_fixture_is_a_strict_finding(tmp_path):
    """The exact shape of the shipped blindness: an exclusions payload in tests/fixtures."""
    m = _load()
    root = _root(tmp_path)
    fx = root / "tests" / "fixtures"
    fx.mkdir()
    (fx / "exclusions.json").write_text('{"hard_excluded": ["AS-260", "AS-216"]}\n')
    hits = m.strict_findings(root, show_identifiers=True)
    assert any("tests/fixtures/exclusions.json" in h and "AS-216" in h and "AS-260" in h
               for h in hits), hits


def test_cohort_id_in_python_source_is_a_strict_finding(tmp_path):
    m = _load()
    root = _root(tmp_path)
    (root / "mamey" / "legacy.py").write_text('"""Calibrated on AS-705."""\nX = 1\n')
    hits = m.strict_findings(root, show_identifiers=True)
    assert any("python source" in h and "AS-705" in h for h in hits), hits


def test_banned_identity_in_tests_is_a_strict_finding(tmp_path):
    m = _load()
    root = _root(tmp_path)
    (root / "tests" / "test_thing.py").write_text('"""From the Cerulean session."""\n')
    hits = m.strict_findings(root, show_identifiers=True)
    assert any("banned identity" in h and "Cerulean" in h for h in hits), hits


# --- the sanctioned exemptions must keep working ---------------------------------------------

def test_synthetic_allowlisted_id_is_clean_in_tests(tmp_path):
    m = _load()
    root = _root(tmp_path, synthetic="AS-901\n")
    (root / "tests" / "test_fixture.py").write_text('STRAIN = "AS-901"\n')
    assert m.strict_findings(root) == []


def test_dashless_id_normalises_to_the_allowlist(tmp_path):
    """make_public_tier.sh normalisation parity: as901/AS901 match allowlisted AS-901."""
    m = _load()
    root = _root(tmp_path, synthetic="AS-901\n")
    (root / "tests" / "test_fixture.py").write_text('A = "AS901"\nB = "as901"\n')
    assert m.strict_findings(root) == []


def test_redacted_placeholder_is_clean(tmp_path):
    m = _load()
    root = _root(tmp_path, synthetic="")
    (root / "tests" / "test_fixture.py").write_text('S = "AS-XXX"; T = "PENDING-XXX"\n')
    assert m.strict_findings(root) == []


def test_known_public_np_carveout_is_clean(tmp_path):
    """enterocin AS-48 is public reference data (redactor SSOT carve-out), not a strain."""
    m = _load()
    root = _root(tmp_path, synthetic="")
    (root / "tests" / "test_np.py").write_text('NAME = "enterocin AS-48"\n')
    assert m.strict_findings(root) == []


def test_default_gate_jurisdiction_is_not_rescanned(tmp_path):
    """An id in a doc file outside tests/ belongs to the default gate, not this pass."""
    m = _load()
    root = _root(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "notes.md").write_text("Example from AS-705.\n")
    assert m.strict_findings(root) == []


def test_missing_allowlist_degrades_strict_not_permissive(tmp_path):
    m = _load()
    root = _root(tmp_path)
    (root / "tools" / "test_synthetic_ids.txt").unlink()
    (root / "tests" / "test_fixture.py").write_text('STRAIN = "AS-901"\n')
    hits = m.strict_findings(root, show_identifiers=True)
    assert any("AS-901" in h for h in hits), hits


# --- CLI mechanics ---------------------------------------------------------------------------

def test_invalid_root_exits_2(tmp_path):
    r = _run(str(tmp_path / "nonexistent"))
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)


def test_clean_root_exits_0(tmp_path):
    root = _root(tmp_path)
    (root / "tests" / "test_ok.py").write_text("X = 1\n")
    r = _run(str(root))
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "STRICT SOURCE DISCLOSURE: PASS" in r.stdout


def test_finding_root_exits_1(tmp_path):
    root = _root(tmp_path)
    (root / "tests" / "test_bad.py").write_text('S = "AS-705"\n')
    r = _run(str(root))
    assert r.returncode == 1, (r.stdout, r.stderr)
