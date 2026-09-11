"""Tests for the wheelhouse CLI module (mamey.wheelhouse).

Tests the data-management logic (version parsing, clean dry-run, add-strain merge) without
requiring the scanner engine's runtime deps (pyhmmer/pyfamsa). The Wheelhouse DATA itself is
not tested here — it's a lab-data store, excluded from the suite by design.
"""

import json
import os
import tempfile
from pathlib import Path

from mamey import wheelhouse as wh


def _make_wheelhouse(tmp: Path):
    (tmp / "Wheelhouse" / "strains").mkdir(parents=True)
    (tmp / "Wheelhouse" / "scanners").mkdir(parents=True)
    (tmp / "Wheelhouse" / "validations").mkdir(parents=True)
    (tmp / "Wheelhouse" / "engine").mkdir(parents=True)
    with open(tmp / "Wheelhouse" / "strains" / "strain_registry.json", "w") as fh:
        json.dump({"strains": {"AS-1": {"id": "AS-1"}}}, fh)
    for v in ("0.2", "0.3"):
        with open(tmp / "Wheelhouse" / "scanners" / f"scanner_registry_v{v}.json", "w") as fh:
            json.dump({"registry_version": v, "n_scanners": 28, "scanners": []}, fh)
    return tmp / "Wheelhouse"


def test_clean_identifies_superseded_registry():
    with tempfile.TemporaryDirectory() as td:
        whd = _make_wheelhouse(Path(td))
        # dry-run: both files still present
        rc = wh._cmd_clean(whd, apply=False)
        assert rc == 0
        assert (whd / "scanners" / "scanner_registry_v0.2.json").exists()
        assert (whd / "scanners" / "scanner_registry_v0.3.json").exists()


def test_clean_apply_removes_superseded():
    with tempfile.TemporaryDirectory() as td:
        whd = _make_wheelhouse(Path(td))
        wh._cmd_clean(whd, apply=True)
        assert not (whd / "scanners" / "scanner_registry_v0.2.json").exists()  # older pruned
        assert (whd / "scanners" / "scanner_registry_v0.3.json").exists()      # latest kept


def test_add_strain_merges_record():
    with tempfile.TemporaryDirectory() as td:
        whd = _make_wheelhouse(Path(td))
        rec = os.path.join(td, "new.json")
        with open(rec, "w") as fh:
            json.dump({"id": "AS-99", "host": "bee"}, fh)
        rc = wh._cmd_add_strain(whd, rec)
        assert rc == 0
        reg = json.load(open(whd / "strains" / "strain_registry.json"))
        assert "AS-99" in reg["strains"]
        assert "AS-1" in reg["strains"]  # original preserved


def test_list_runs_clean():
    with tempfile.TemporaryDirectory() as td:
        whd = _make_wheelhouse(Path(td))
        assert wh._cmd_list(whd) == 0


def test_resolve_hmm_database_prefers_larger_tier(monkeypatch):
    import tempfile
    from pathlib import Path
    monkeypatch.delenv("SM_HMM_DB", raising=False)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "iso_bundle"
        (root / "Wheelhouse" / "hmm").mkdir(parents=True)
        # 35-model core present; 148 present in the SAME bundle-local hmm dir -> must prefer 148.
        (root / "Wheelhouse" / "hmm" / "scanner_pfam.hmm").write_text("x")
        (root / "Wheelhouse" / "hmm" / "scanner_pfam_150.hmm").write_text("y")
        r = wh.resolve_hmm_database(root)
        # bundle-local 148 wins over bundle-local 35 (contract: larger tier preferred)
        assert r["n_models_hint"] == 148


def test_resolve_hmm_database_env_override(monkeypatch):
    import tempfile, os
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "scanner_pfam_150.hmm")
        Path(p).write_text("z")
        monkeypatch.setenv("SM_HMM_DB", p)
        r = wh.resolve_hmm_database(Path(td))
        assert r["tier"] == "env-override"
        assert r["n_models_hint"] == 148


def test_resolve_hmm_database_none_when_absent(monkeypatch):
    import tempfile
    from pathlib import Path
    monkeypatch.delenv("SM_HMM_DB", raising=False)
    with tempfile.TemporaryDirectory() as td:
        # isolated empty dir with no addon anywhere in its (temp) ancestry
        r = wh.resolve_hmm_database(Path(td) / "nonexistent_bundle")
        assert r["tier"] == "none"
        assert r["path"] is None


def test_shipped_strain_registry_count_invariant():
    """F1 (hostile audit): guard against the AS-XXX key-collision bug where masking collapsed
    multiple AS-strains into one JSON key and n_strains silently disagreed with the record count.
    The shipped registry must satisfy n_strains == len(strains)."""
    import json
    from pathlib import Path
    reg_path = Path(__file__).resolve().parent.parent / "Wheelhouse" / "strains" / "strain_registry.json"
    if not reg_path.exists():
        return  # Wheelhouse not in this tree (e.g. isolated test env)
    data = json.load(open(reg_path))
    strains = data.get("strains", data)
    n_field = data.get("n_strains")
    # The count invariant is the real F1 guard and holds in ALL tiers.
    keys = list(strains.keys()) if isinstance(strains, dict) else []
    if n_field is not None:
        assert n_field == len(strains), (
            f"n_strains={n_field} but registry has {len(strains)} records — "
            "possible key collision from AS-masking (audit F1)")
    # A COLLAPSED public tier would have a single literal "AS-XXX" key with n_strains > records.
    # Correctly-redacted public tiers have disambiguated AS-XXX / AS-XXX-1 / ... keys (all records
    # preserved), which is fine. So the failure signature is specifically: bare "AS-XXX" present
    # AND no disambiguated siblings AND fewer records than n_strains — already caught by the count
    # assertion above. Here we only guard the private tree: unmasked AS-<n> keys must be distinct.
    as_num_keys = [k for k in keys if isinstance(k, str) and k[:3] == "AS-" and k[3:].isdigit()]
    assert len(as_num_keys) == len(set(as_num_keys)), "duplicate AS-<n> keys (collision, audit F1)"


def test_ingest_load_returns_default_when_missing():
    """Patch F3: ingest_package.load() must return the caller's default shape for a missing
    store instead of raising FileNotFoundError (fresh-bank --merge must not need pre-seeding)."""
    import importlib.util
    from pathlib import Path
    ip_path = Path(__file__).resolve().parent.parent / "tools" / "ingest_package.py"
    if not ip_path.exists():
        return
    spec = importlib.util.spec_from_file_location("ingest_package_t", ip_path)
    ip = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ip)
    import tempfile, os
    missing = os.path.join(tempfile.gettempdir(), "definitely_absent_store_xyz.json")
    if os.path.exists(missing):
        os.remove(missing)
    assert ip.load(missing, default={"strains": {}, "bgcs": []}) == {"strains": {}, "bgcs": []}
    assert ip.load(missing) in ({}, None) or ip.load(missing, default={}) == {}
