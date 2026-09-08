"""roster_v2.resolve_inventory freshness regression (v9.7.397 bypass-audit finding).

The picker scored homes but was version-blind: with inventories from multiple package
generations on disk, a legacy home preference (mamey_packages +100) beat a strictly newer
seal living in a versionless per-strain home. Repaired: newest bundle version wins (sibling
Complete_Package.zip name, else path token), then home score, then mtime.

Strain IDs are synthetic and runtime-constructed; fixtures live in tmp_path only.
"""
from __future__ import annotations

import csv
import importlib.util
import os
import zipfile

# The picker lives in the deliverable_tools CLI module (NOT mamey.roster_v2, which is the
# engine-side widget model without resolve_inventory). Load it by file path.
_SPEC = importlib.util.spec_from_file_location(
    "deliverable_tools_roster_v2",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "deliverable_tools", "roster_v2.py"),
)
roster_v2 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(roster_v2)

STRAIN = "AS-" + str(9900 + 2)
HDR = ["BGC_ID", "Products", "KCB_top"]


def _write_inventory(dirpath, rows=1):
    os.makedirs(dirpath, exist_ok=True)
    p = os.path.join(dirpath, STRAIN + "_2_inventory.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HDR)
        for i in range(rows):
            w.writerow([f"BGC{i:03d}", "NRPS", ""])
    return p


def _sibling_package_zip(strain_dir, version):
    os.makedirs(strain_dir, exist_ok=True)
    p = os.path.join(strain_dir, "%s_SapoteMamey_v%s_engine1.9.129_Complete_Package.zip" % (STRAIN, version))
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("package/manifest.json", "{}")
    return p


def test_newer_seal_beats_legacy_home_preference(tmp_path, monkeypatch):
    """A v9.7.376 inventory in a versionless per-strain home must beat a v9.7.339
    inventory under the legacy mamey_packages home (which previously won on +100)."""
    root = str(tmp_path)
    old = _write_inventory(os.path.join(root, "mamey_packages", STRAIN + "_SapoteMamey_v9.7.339_x", "package"))
    new_dir = os.path.join(root, "Mamey Complete", STRAIN)
    _sibling_package_zip(new_dir, "9.7.376")
    new = _write_inventory(os.path.join(new_dir, "package"))
    monkeypatch.setattr(roster_v2, "ROOT", root)
    got = roster_v2.resolve_inventory(STRAIN)
    assert got == new, "picked %r over newer seal %r" % (got, new)
    assert got != old


def test_path_version_token_used_when_no_sibling_zip(tmp_path, monkeypatch):
    root = str(tmp_path)
    older = _write_inventory(os.path.join(root, "runs_v9.7.335", STRAIN, "package"))
    newer = _write_inventory(os.path.join(root, "runs_v9.7.339", STRAIN, "package"))
    monkeypatch.setattr(roster_v2, "ROOT", root)
    assert roster_v2.resolve_inventory(STRAIN) == newer, "path version token not honored"
    assert older != newer


def test_header_gate_still_enforced(tmp_path, monkeypatch):
    """A fresher but schema-invalid inventory must be skipped for the valid older one."""
    root = str(tmp_path)
    valid = _write_inventory(os.path.join(root, "runs_v9.7.335", STRAIN, "package"))
    bad_dir = os.path.join(root, "runs_v9.7.339", STRAIN, "package")
    os.makedirs(bad_dir, exist_ok=True)
    bad = os.path.join(bad_dir, STRAIN + "_2_inventory.csv")
    with open(bad, "w", newline="") as f:
        csv.writer(f).writerow(["wrong", "columns"])
    monkeypatch.setattr(roster_v2, "ROOT", root)
    assert roster_v2.resolve_inventory(STRAIN) == valid


def test_none_when_no_inventory(tmp_path, monkeypatch):
    monkeypatch.setattr(roster_v2, "ROOT", str(tmp_path))
    assert roster_v2.resolve_inventory(STRAIN) is None
