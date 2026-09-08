"""CUT-10B: external registry and exclusions loader must resolve one governed source."""
from __future__ import annotations

import json
from pathlib import Path

from mamey import exclusions, external_data


def _write(root: Path, strains: int, regions: int) -> Path:
    official = root / "OFFICIAL_DATA"
    official.mkdir(parents=True)
    (official / "exclusions.json").write_text(
        json.dumps({
            "hard_excluded": [],
            "raw_assembly_void": [],
            "strain_of_record": {},
            "qc_hold_audit_only": [],
            "governed": {"strains": strains, "regions": regions},
        }),
        encoding="utf-8",
    )
    return official


def test_shared_data_root_is_one_source_for_registry_and_denominator(monkeypatch, tmp_path: Path):
    official = _write(tmp_path, 7, 91)
    monkeypatch.delenv("MAMEY_OFFICIAL_DATA", raising=False)
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(tmp_path))

    assert external_data.resolve("official_data") == official
    assert exclusions.load_exclusions()["governed"] == {"strains": 7, "regions": 91}


def test_explicit_official_data_precedes_shared_root(monkeypatch, tmp_path: Path):
    _write(tmp_path / "shared", 7, 91)
    explicit = _write(tmp_path / "explicit", 8, 99)
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(tmp_path / "shared"))
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(explicit))

    assert external_data.resolve("official_data") == explicit
    assert exclusions.load_exclusions()["governed"] == {"strains": 8, "regions": 99}
