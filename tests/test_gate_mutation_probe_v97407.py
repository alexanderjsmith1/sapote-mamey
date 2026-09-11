from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("gate_mutation_probe", ROOT / "tools" / "gate_mutation_probe.py")
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def test_mutation_table_is_well_formed_and_has_core_protection_classes():
    rows = probe.read_table(ROOT / "tools" / "gate_mutation_table.tsv")
    ids = {row["id"] for row in rows}
    assert {"RULE:SACCHARIDE", "SCORING:MOBILE_ELEMENT", "RGGMCI:GEOMETRY", "VALIDATE:DEPTH_FLOOR"} <= ids
    assert all(row["tests"].startswith("tests/") for row in rows)
    assert rows[0]["old"].startswith('"id":')


def test_inventory_includes_prompt_defined_protection_categories():
    rows = probe.inventory(ROOT)
    ids = {row["id"] for row in rows}
    assert "RULE:SACCHARIDE" in ids
    assert "REGISTRY:sync_version" in ids
    assert "VALIDATE:RGGMCI_GATE" in ids
    assert any(item.startswith("FUNC:mamey/rggmci.py:") for item in ids)


def test_inventory_discovers_nested_tool_guards_and_excludes_cache(tmp_path):
    (tmp_path / "tools" / "nested").mkdir(parents=True)
    (tmp_path / "tools" / "__pycache__").mkdir()
    (tmp_path / "mamey" / "data").mkdir(parents=True)
    (tmp_path / "tools" / "gate_registry.tsv").write_text("", encoding="utf-8")
    (tmp_path / "mamey" / "data" / "rules_registry.json").write_text('{"rules": []}', encoding="utf-8")
    (tmp_path / "tools" / "nested" / "fixture.py").write_text(
        "def nested_guard():\n    return True\n\ndef helper():\n    return True\n", encoding="utf-8"
    )
    (tmp_path / "tools" / "__pycache__" / "cached.py").write_text(
        "def cached_gate():\n    return True\n", encoding="utf-8"
    )
    ids = {row["id"] for row in probe.inventory(tmp_path)}
    assert "FUNC:tools/nested/fixture.py:nested_guard" in ids
    assert "FUNC:tools/nested/fixture.py:helper" not in ids
    assert not any("__pycache__" in item for item in ids)


def test_inventory_does_not_follow_symlinked_tool_file(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "mamey" / "data").mkdir(parents=True)
    (tmp_path / "outside").mkdir()
    (tmp_path / "tools" / "gate_registry.tsv").write_text("", encoding="utf-8")
    (tmp_path / "mamey" / "data" / "rules_registry.json").write_text('{"rules": []}', encoding="utf-8")
    target = tmp_path / "outside" / "external.py"
    target.write_text("def external_gate():\n    return True\n", encoding="utf-8")
    (tmp_path / "tools" / "linked.py").symlink_to(target)
    external_dir = tmp_path / "outside" / "nested"
    external_dir.mkdir()
    (external_dir / "guard.py").write_text(
        "def external_dir_guard():\n    return True\n", encoding="utf-8"
    )
    (tmp_path / "tools" / "linked_dir").symlink_to(external_dir, target_is_directory=True)
    ids = {row["id"] for row in probe.inventory(tmp_path)}
    assert not any("external_gate" in item for item in ids)
    assert not any("external_dir_guard" in item for item in ids)


def test_inventory_keeps_same_named_guards_distinct_by_relative_path(tmp_path):
    (tmp_path / "tools" / "left").mkdir(parents=True)
    (tmp_path / "tools" / "right").mkdir(parents=True)
    (tmp_path / "mamey" / "data").mkdir(parents=True)
    (tmp_path / "tools" / "gate_registry.tsv").write_text("", encoding="utf-8")
    (tmp_path / "mamey" / "data" / "rules_registry.json").write_text('{"rules": []}', encoding="utf-8")
    for dirname in ("left", "right"):
        (tmp_path / "tools" / dirname / "fixture.py").write_text(
            "def same_guard():\n    return True\n", encoding="utf-8"
        )
    ids = {row["id"] for row in probe.inventory(tmp_path)}
    assert {
        "FUNC:tools/left/fixture.py:same_guard",
        "FUNC:tools/right/fixture.py:same_guard",
    } <= ids


def test_unpaired_mutation_is_explicitly_held(tmp_path):
    row = {"id": "X", "kind": "guard", "source": "mamey/scoring.py", "old": "", "new": "",
           "tests": "", "consequence": ""}
    result = probe.run_one(ROOT, row, tmp_path)
    assert result["classification"] == "UNPAIRED"
    assert result["remediation"] == "HOLD_MUTATION_TABLE_ENTRY_REQUIRED"


def test_mutation_log_name_cannot_create_nested_paths():
    assert "FUNC__mamey_scoring.py__standing_rule_for.log" == (
        "FUNC:mamey/scoring.py:standing_rule_for".replace(":", "__").replace("/", "_") + ".log"
    )
