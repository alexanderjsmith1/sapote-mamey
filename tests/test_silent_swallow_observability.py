"""Regression tests for input-read failures that previously lost their cause."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

import tools.ingest_package as ingest


def _intake_module():
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("silent_swallow_intake_test", root / "tools" / "intake_harness.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_intake_warns_when_organism_record_cannot_be_read(tmp_path, monkeypatch):
    """Unreadable region input remains an explicit unknown-taxonomy condition."""
    intake = _intake_module()
    archive = tmp_path / "input.zip"
    import zipfile
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("region001.gbk", "LOCUS       test\n")

    real_open = open
    blocked = {"done": False}
    def blocked_open(path, *args, **kwargs):
        if (str(path).endswith("region001.gbk") and (not args or "r" in args[0])
                and not blocked["done"]):
            blocked["done"] = True
            raise OSError("fixture read denied")
        return real_open(path, *args, **kwargs)
    monkeypatch.setattr("builtins.open", blocked_open)

    with pytest.warns(RuntimeWarning, match="could not read ORGANISM"):
        kind, _, _, organism = intake.detect_and_stage(str(archive), str(tmp_path / "stage"), "fixture")
    assert kind == "ANTISMASH"
    assert organism is None


def test_ingest_warns_when_rggmci_alias_file_is_invalid(tmp_path):
    """An unreadable optional alias must be visible, not indistinguishable from no pairs."""
    alias = tmp_path / "alias.json"
    alias.write_text("{invalid json", encoding="utf-8")
    snapshot = {
        "strain_id": "SIDTEST", "taxonomy": "Streptomyces sp.",
        "assembly": {"contigs": 1, "n50": 1, "genome_bp": 1, "gc_pct": 70, "largest_contig": 1},
        "bgc_counts": {"raw": 0, "corrected": 0, "interior": 0, "full_contig": 0, "edge": 0},
        "bgcs": [],
        "source_scans": {"rggmci": {"alias_of": alias.name}},
    }
    with pytest.warns(RuntimeWarning, match="RG-GMCI alias"):
        entry = ingest.build_entry(snapshot, "", pkg_dir=tmp_path)
    assert entry["rggmci_full"]["status"] == "UNREADABLE_ALIAS"


def test_schema_gate_refuses_unreadable_manifest(tmp_path):
    """A present but malformed manifest cannot be overridden as an unknown schema."""
    package = tmp_path / "package"
    package.mkdir()
    (package / "manifest.json").write_text("{invalid json", encoding="utf-8")
    with pytest.raises(SystemExit, match="cannot read manifest"):
        ingest._schema_gate(str(package), str(tmp_path / "bank"), force=True)
