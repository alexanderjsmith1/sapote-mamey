"""tests/public/test_public_release_v9_7_381.py — hard invariants for the public GitHub release.

Selected with `pytest -m public`. Every test here is hermetic (no network, no cohort pack, no
personal paths) and asserts a property that must hold for a safe public artifact.
"""
from pathlib import Path
import re
import pytest

pytestmark = pytest.mark.public

_MAMEY = Path(__import__("mamey").__file__).parent
_ROOT = _MAMEY.parent


def test_no_cohort_roster_ships():
    assert not (_MAMEY / "data" / "strain_genus.csv").exists()


def test_shipped_exclusions_default_is_empty():
    from mamey import exclusions
    assert exclusions._DEFAULT["hard_excluded"] == []
    assert exclusions._DEFAULT["governed"] == {}


def test_unknown_strain_fails_safe_to_private():
    from mamey.dedup_and_guard import derive_release
    assert derive_release("unregistered-strain-xyz") == "PRIVATE"


def test_no_personal_paths_in_mamey_package():
    bad = re.compile(r"/Users/[^/]+/|/home/[^/]+/|Claude_Alex_\d+|Codex Alex \d+")
    # detector modules legitimately contain the pattern they hunt for (no name, just a regex)
    detectors = {"combined_report_builder.py"}
    hits = [p for p in _MAMEY.rglob("*.py") if p.name not in detectors and bad.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert not hits, f"personal paths in shipped package: {[str(p) for p in hits]}"


def test_front_door_files_exist():
    for f in ("SECURITY.md", "CONTRIBUTING.md", "docs/EXTERNAL_ASSETS_GUIDE.md"):
        assert (_ROOT / f).exists(), f"missing front-door file: {f}"


def test_missing_optional_pfam_degrades_not_crashes():
    # importing the engine must not require any external HMM/db (fail-safe optional-data)
    import importlib
    m = importlib.import_module("mamey")
    assert m is not None


def test_no_pfam_hmm_ships():
    # per the release policy the Pfam HMM is operator-acquired, not bundled
    assert not list(_ROOT.rglob("scanner_pfam*.hmm"))
    assert not list((_MAMEY / "data").rglob("Pfam-A.hmm"))
