"""A material file that enters no collection holds completeness instead of vanishing."""
from __future__ import annotations

import json
from pathlib import Path

from mamey.workspace_source_discovery import ScanLimits, build_source_catalog, sha256_file


def _registry(base: Path) -> Path:
    path = base / "collections.json"
    path.write_text(json.dumps({
        "schema_version": "sapote-source-collection-registry-v1",
        "unclassified_max_depth": 2,
        "rules": [{"collection_type": "MODE_B_COMPILATION", "directory_regex": r"modeb_compilation_",
                   "material_file_regex": r"ModeB_compilation\.md$"}],
    }), encoding="utf-8")
    return path


def _scan(base: Path, root: Path) -> dict:
    registry = _registry(base)
    return build_source_catalog(root=root, root_id="evidence", collection_registry_path=registry,
                                expected_collection_registry_sha256=sha256_file(registry), limits=ScanLimits())


def test_deep_unmatched_csv_holds_the_scan(tmp_path):
    root = tmp_path / "evidence"
    deep = root / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "orphan_results.csv").write_text("strain,value\nX,1\n", encoding="utf-8")
    catalog = _scan(tmp_path, root)
    assert catalog["status"] == "INCOMPLETE_UNCATALOGED_MATERIAL"
    assert catalog["scan_counts"]["uncataloged_material_file_count"] == 1
    assert catalog["uncataloged_material_directories"][0]["relative_path"] == "a/b/c"
    assert catalog["collections"] == []


def test_non_material_files_are_listed_but_do_not_hold(tmp_path):
    root = tmp_path / "evidence"
    deep = root / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "notes.txt").write_text("x", encoding="utf-8")
    catalog = _scan(tmp_path, root)
    assert catalog["status"] == "PASS_COMPLETE"
    assert catalog["scan_counts"]["uncataloged_other_file_count"] == 1
    assert catalog["uncataloged_other_directories"][0]["relative_path"] == "a/b/c"


def test_shallow_unmatched_csv_still_becomes_unclassified_collection(tmp_path):
    root = tmp_path / "evidence"
    (root / "a").mkdir(parents=True)
    (root / "a" / "table.csv").write_text("x\n", encoding="utf-8")
    catalog = _scan(tmp_path, root)
    assert catalog["status"] == "PASS_COMPLETE"
    assert [row["collection_type"] for row in catalog["collections"]] == ["UNCLASSIFIED_MATERIAL"]
    assert catalog["scan_counts"]["uncataloged_material_file_count"] == 0
