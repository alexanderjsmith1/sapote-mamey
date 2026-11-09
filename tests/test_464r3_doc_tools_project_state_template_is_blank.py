"""The shipped project-state template carries no person, project or example values."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "bundle_support" / "project_state_template.json"


def _state_fields(data):
    return {k: v for k, v in data.items() if not k.startswith("_")}


def test_identity_and_history_fields_are_blank():
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    for key in ("project_id", "project_name", "active_monolith", "affiliation", "pi", "analyst", "orcid",
                "master_workbook", "last_handoff_zip", "last_updated", "next_action", "session_notes"):
        assert data[key] == "", key


def test_strain_lists_hold_no_example_rows():
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    for key in ("completed_strains", "deferred_strains", "failed_strains"):
        assert data[key] == [], key


def test_no_state_value_is_a_menu_of_options():
    data = _state_fields(json.loads(TEMPLATE.read_text(encoding="utf-8")))
    allowed = set(json.loads(TEMPLATE.read_text(encoding="utf-8"))["_allowed_status_values"])
    assert set(data["project_bundle_status"].values()) <= allowed
    assert "|" not in json.dumps(data)


def test_sync_version_rule_still_finds_the_bundle_version():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert re.search(r'("bundle_version":\s*"sapote-mamey-v)[\w.\-]+(")', text)
