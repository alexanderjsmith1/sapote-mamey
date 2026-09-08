from __future__ import annotations

import json
from pathlib import Path

import pytest

from mamey.interactive_figures.component_gallery import write_component_gallery
from mamey.interactive_figures.optional_output import OutputRefusal
from mamey.interactive_figures.theme_gallery import write_theme_gallery


def test_explicit_tools_publish_complete_new_output_directories(tmp_path) -> None:
    theme = write_theme_gallery(tmp_path / "theme")
    component = write_component_gallery(tmp_path / "component")
    assert (tmp_path / "theme" / "sapote_mamey_figure_theme_gallery.html").is_file()
    assert (tmp_path / "component" / "sapote_mamey_figure_component_manifest.json").is_file()
    assert theme["theme_count"] == 6
    assert component["component_count"] == 5
    assert theme["html"].startswith("theme/")
    assert component["manifest"].startswith("component/")
    assert str(tmp_path) not in json.dumps({"theme": theme, "component": component})


def test_output_collision_refuses_without_replacement(tmp_path) -> None:
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    sentinel = occupied / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(OutputRefusal, match="already exists"):
        write_theme_gallery(occupied)
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert sorted(path.name for path in occupied.iterdir()) == ["sentinel.txt"]


def test_empty_existing_output_refuses_without_inode_replacement(tmp_path) -> None:
    occupied = tmp_path / "empty"
    occupied.mkdir()
    before = occupied.stat().st_ino
    with pytest.raises(OutputRefusal, match="already exists"):
        write_theme_gallery(occupied)
    assert occupied.is_dir()
    assert occupied.stat().st_ino == before
    assert list(occupied.iterdir()) == []


def test_owner_rejected_ladder_remains_absent_and_receipt_is_machine_readable(tmp_path) -> None:
    component = write_component_gallery(tmp_path / "component")
    manifest = json.loads((tmp_path / "component" / "sapote_mamey_figure_component_manifest.json").read_text(encoding="utf-8"))
    ids = [row["component_id"] for row in manifest["components"]]
    assert "claim-ceiling-ladder" not in ids
    assert "evidence-stage-ladder" in ids
    assert component["component_count"] == len(ids)
