"""test_npatlas_env_unification_v97405.py -- NPA-01 (env-var unification) + NPA-02 (licence
correction), punch-card B7.

mamey/external_data.py documents MAMEY_NPATLAS_DIR as the NP Atlas dataset's env var (NPA-01
finding); mamey/npatlas_resolver.py and mamey/npatlas_structure.py must both honor it, with the
old SM_NPATLAS_DIR name still working as a warned legacy alias for one compatibility cycle.
mamey/external_data.py's licence string for NP Atlas must say CC BY-NC 4.0 (not CC BY 4.0).

Synthetic fixtures only: fake compound names/NPAIDs, tmp_path-only directories, no real strain
identifiers, no absolute local paths baked into assertions.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path


def _write_ref_file(d: Path, name: str, marker: str) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps({"compounds": [
        {"name": f"synthcompound-{marker}", "npaid": f"NPA{marker}", "inchikey": "",
         "smiles": "", "mol_formula": "", "npclassifier": {}},
    ]}), encoding="utf-8")


# ---------------------------------------------------------------------------
# NPA-01 -- mamey/npatlas_resolver.py
# ---------------------------------------------------------------------------

def test_resolver_reads_mamey_npatlas_dir(tmp_path, monkeypatch):
    d = tmp_path / "npatlas_primary"
    _write_ref_file(d, "all_actinobacteria_npatlas_ref.json", "primary")
    monkeypatch.setenv("MAMEY_NPATLAS_DIR", str(d))
    monkeypatch.delenv("SM_NPATLAS_DIR", raising=False)

    import mamey.npatlas_resolver as resolver
    resolver._load_index.cache_clear()
    idx = resolver._load_index()
    assert "synthcompound-primary" in idx


def test_resolver_sm_npatlas_dir_is_a_warned_legacy_alias(tmp_path, monkeypatch):
    d = tmp_path / "npatlas_legacy"
    _write_ref_file(d, "all_actinobacteria_npatlas_ref.json", "legacy")
    monkeypatch.delenv("MAMEY_NPATLAS_DIR", raising=False)
    monkeypatch.setenv("SM_NPATLAS_DIR", str(d))

    import mamey.npatlas_resolver as resolver
    resolver._load_index.cache_clear()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        idx = resolver._load_index()
    assert "synthcompound-legacy" in idx, "legacy SM_NPATLAS_DIR must still work for one compat cycle"
    assert any(issubclass(w.category, DeprecationWarning) and "SM_NPATLAS_DIR" in str(w.message)
               for w in caught), "legacy env var must emit a DeprecationWarning naming itself"


def test_resolver_mamey_npatlas_dir_wins_over_legacy(tmp_path, monkeypatch):
    primary = tmp_path / "primary"
    legacy = tmp_path / "legacy"
    _write_ref_file(primary, "all_actinobacteria_npatlas_ref.json", "primaryWins")
    _write_ref_file(legacy, "all_actinobacteria_npatlas_ref.json", "legacyLoses")
    monkeypatch.setenv("MAMEY_NPATLAS_DIR", str(primary))
    monkeypatch.setenv("SM_NPATLAS_DIR", str(legacy))

    import mamey.npatlas_resolver as resolver
    resolver._load_index.cache_clear()
    idx = resolver._load_index()
    assert "synthcompound-primarywins" in idx
    assert "synthcompound-legacyloses" not in idx


# ---------------------------------------------------------------------------
# NPA-01 -- mamey/npatlas_structure.py (standalone-fallback loader)
# ---------------------------------------------------------------------------

def test_structure_local_dirs_reads_mamey_npatlas_dir(tmp_path, monkeypatch):
    d = tmp_path / "npatlas_struct_primary"
    _write_ref_file(d, "all_actinobacteria_npatlas_ref.json", "structprimary")
    monkeypatch.setenv("MAMEY_NPATLAS_DIR", str(d))
    monkeypatch.delenv("SM_NPATLAS_DIR", raising=False)

    import mamey.npatlas_structure as struct
    dirs = struct._local_npatlas_dirs()
    assert Path(str(d)) in dirs


def test_structure_sm_npatlas_dir_is_a_warned_legacy_alias(tmp_path, monkeypatch):
    d = tmp_path / "npatlas_struct_legacy"
    d.mkdir()
    monkeypatch.delenv("MAMEY_NPATLAS_DIR", raising=False)
    monkeypatch.setenv("SM_NPATLAS_DIR", str(d))

    import mamey.npatlas_structure as struct
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        dirs = struct._local_npatlas_dirs()
    assert Path(str(d)) in dirs
    assert any(issubclass(w.category, DeprecationWarning) and "SM_NPATLAS_DIR" in str(w.message)
               for w in caught)


def test_structure_env_dir_none_when_neither_set(monkeypatch):
    monkeypatch.delenv("MAMEY_NPATLAS_DIR", raising=False)
    monkeypatch.delenv("SM_NPATLAS_DIR", raising=False)
    import mamey.npatlas_structure as struct
    assert struct._npatlas_env_dir() is None


def test_resolver_env_dir_none_when_neither_set(monkeypatch):
    monkeypatch.delenv("MAMEY_NPATLAS_DIR", raising=False)
    monkeypatch.delenv("SM_NPATLAS_DIR", raising=False)
    import mamey.npatlas_resolver as resolver
    assert resolver._npatlas_env_dir() is None


# ---------------------------------------------------------------------------
# NPA-02 -- mamey/external_data.py licence correction
# ---------------------------------------------------------------------------

def test_external_data_npatlas_licence_is_cc_by_nc():
    from mamey.external_data import DATASETS
    licence = DATASETS["npatlas"].licence
    assert "CC BY-NC 4.0" in licence, f"expected CC BY-NC 4.0 in licence text, got: {licence!r}"
    assert "CC BY 4.0" not in licence, "must not still claim the (incorrect) unrestricted CC BY 4.0"


def test_external_data_npatlas_env_var_is_mamey_npatlas_dir():
    from mamey.external_data import DATASETS
    assert DATASETS["npatlas"].env_var == "MAMEY_NPATLAS_DIR"


def test_external_data_status_reports_npatlas_licence():
    from mamey.external_data import status
    s = status()
    assert "npatlas" in s
    assert "CC BY-NC 4.0" in s["npatlas"]["licence"]
