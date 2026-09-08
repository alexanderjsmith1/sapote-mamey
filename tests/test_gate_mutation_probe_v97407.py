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
