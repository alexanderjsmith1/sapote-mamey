"""Lab Quest is removed (v9.7.450): no add-on, no command, no install path; old project folders still read."""
from __future__ import annotations

import json
from pathlib import Path

import mamey
from mamey import cli
from mamey.portfolio_config import LEGACY_PROJECT_OUTPUT_DIR, PROJECT_OUTPUT_DIR, project_output_dir
from mamey.project_catalog import ProjectCatalog

ROOT = Path(mamey.__file__).resolve().parent.parent


def test_addon_source_docs_and_command_are_gone():
    assert not (ROOT / "sapote_addons" / "lab_quest").exists()
    assert not (ROOT / "docs" / "LAB_QUEST.md").exists()
    assert "lab-quest" not in cli.build_parser().format_help()
    assert "LAB_QUEST" not in (ROOT / "bundle_support" / "install_sapote_addons.sh").read_text()


def test_no_lab_quest_mention_in_shipped_code_or_current_docs():
    history = {"CHANGELOG.md", "ENGINE_LINEAGE.md", "SOURCE_CHECKSUMS_SHA256.txt", "TIER_MANIFEST.txt"}
    allowed = {"mamey/portfolio_config.py", "tools/gen_command_catalog.py", "tools/check_command_pointers.py",
               "docs/PROJECT_CATALOG.md"}  # the legacy folder name and the removal notes
    hits = []
    for d in ("mamey", "tools", "docs", "bundle_support", "sapote_addons"):
        for p in (ROOT / d).rglob("*"):
            if not p.is_file() or "__pycache__" in p.parts or p.name in history or p.suffix in (".pyc", ".png", ".pdf"):
                continue
            rel = p.relative_to(ROOT).as_posix()
            if rel in allowed:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore").lower()
            if "lab quest" in text or "lab_quest" in text or "lab-quest" in text:
                hits.append(rel)
    assert not hits, hits


def test_new_projects_write_project_outputs(tmp_path):
    ProjectCatalog(tmp_path)
    assert (tmp_path / PROJECT_OUTPUT_DIR).is_dir()
    assert not (tmp_path / LEGACY_PROJECT_OUTPUT_DIR).exists()


def test_existing_legacy_folder_is_still_used(tmp_path):
    legacy = tmp_path / LEGACY_PROJECT_OUTPUT_DIR
    legacy.mkdir()
    (legacy / "keep.json").write_text(json.dumps({}))
    assert project_output_dir(tmp_path) == legacy
    ProjectCatalog(tmp_path)
    assert not (tmp_path / PROJECT_OUTPUT_DIR).exists()
