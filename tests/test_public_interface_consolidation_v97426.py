"""Public navigation stays small even while specialist commands remain available."""
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_widget_builder():
    path = ROOT / "tools" / "build_deliverable_menu_widget.py"
    spec = importlib.util.spec_from_file_location("build_deliverable_menu_widget", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_compatibility_start_page_redirects_to_three_distinct_audiences():
    text = (ROOT / "docs" / "START_HERE.md").read_text(encoding="utf-8")
    assert "[README](../README.md)" in text
    assert "[AGENTS contract](../AGENTS.md)" in text
    assert "python mamey_run.py start" in text
    assert "python -m mamey run" not in text
    assert "previously" not in text.lower()


def test_widget_defaults_to_a_small_recommended_command_path():
    mod = _load_widget_builder()
    payload = mod.build_payload(ROOT)
    primary = payload["primary_commands"]
    assert primary[0] == "start"
    assert {"inspect", "run", "validate", "discover", "render-all-figures", "mode-b"} <= set(primary)
    assert len(primary) < payload["subcommand_count"] / 4
    by_name = {row["name"]: row for row in payload["subcommands"]}
    assert all(by_name[name]["recommended"] for name in primary)
    assert not by_name["chatgpt-init"]["recommended"]
    html = mod.render_html(payload)
    assert 'id="primaryonly" checked' in html
    assert "Command reference" in html


def test_current_how_to_use_has_no_assistant_specific_handoff_path():
    text = (ROOT / "docs" / "HOW_TO_USE.md").read_text(encoding="utf-8")
    assert "send PMIDs to Claude" not in text
    assert "Sapote / Claude / ChatGPT handoff" not in text
    assert "render-all-figures" in text
    assert "phylo-autopilot" in text


def test_release_manifest_has_no_stale_internal_cut_narrative():
    text = (ROOT / "RELEASE_MANIFEST.md").read_text(encoding="utf-8")
    assert "v9.7.417 staging candidate" not in text
    assert "Release tier builds and full artifact suite | PENDING" not in text
    assert "Local release seal | NOT ISSUED" not in text
    assert "exact print-call count 1323" not in text
    assert "## Patches in" not in text
    assert "## Current validation" in text
