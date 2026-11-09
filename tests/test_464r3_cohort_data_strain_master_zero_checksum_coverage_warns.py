"""A checksum check that compared no record table is a warning, not a PASS."""
from __future__ import annotations

import json
from pathlib import Path

from mamey import strain_master as sm


def _checksum(result):
    return next(c for c in result["checks"] if c["name"].startswith("files match their README checksums"))


def test_patterns_selecting_nothing_warn(tmp_path):
    root = tmp_path / "m"
    sm.init_master(str(root), "Synthetic master")
    cfg_path = root / "strain_master.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["checksum_readmes"] = ["no_such_area/**/README.md"]
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    result = sm.check(str(root))
    check = _checksum(result)
    assert check["status"] == "WARN"
    assert "0 record tables" in check["name"]
    assert "no record table was checked" in check["lines"][0]
    assert result["result"] != "PASS"


def test_fresh_master_with_tables_still_passes(tmp_path):
    root = tmp_path / "m"
    sm.init_master(str(root), "Synthetic master")
    assert _checksum(sm.check(str(root)))["status"] == "PASS"
