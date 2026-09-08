from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mamey.interactive_figures.component_gallery import (
    COMPONENT_STATUS,
    SCHEMA_VERSION,
    component_manifest,
    component_specs,
    render_component_gallery_svg,
)


def test_component_registry_is_unique_and_claim_bounded() -> None:
    specs = component_specs()
    assert len(specs) == 5
    assert len({spec.component_id for spec in specs}) == len(specs)
    assert all(spec.required_fields for spec in specs)
    assert all(spec.caption_pattern.endswith(".") for spec in specs)
    assert all(spec.claim_ceiling.endswith(".") for spec in specs)
    assert "nr_state" in specs[0].required_fields
    assert "clusterednr_state" in specs[0].required_fields
    assert "local_swissprot_state" in specs[0].required_fields


def test_svg_is_accessible_parseable_and_preserves_workflow_states() -> None:
    svg = render_component_gallery_svg("evidence-navy")
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert root.attrib["role"] == "img"
    assert svg.count("<title") >= 13
    for phrase in (
        "Three-Channel Evidence Matrix",
        "Gene-Role and Reaction Ledger",
        "Locus Architecture Strip",
        "Comparison Availability Board",
        "Evidence-Stage Ladder",
        "Observed",
        "Unreturned",
        "Unbound",
        "Pending",
        "Unavailable",
    ):
        assert phrase in svg
    assert "judgment" not in svg.lower()
    assert "BGC001" not in svg
    assert "AS-" not in svg


def test_manifest_is_complete_and_json_safe() -> None:
    manifest = component_manifest("scientific-cream")
    encoded = json.dumps(manifest)
    decoded = json.loads(encoded)
    assert decoded["schema_version"] == SCHEMA_VERSION
    assert decoded["status"] == COMPONENT_STATUS
    assert decoded["theme_id"] == "scientific-cream"
    assert decoded["component_count"] == 5
    assert len(decoded["components"]) == 5


def test_unknown_theme_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unknown theme_id"):
        render_component_gallery_svg("not-a-governed-theme")


def test_command_writes_svg_and_manifest(tmp_path: Path) -> None:
    tool = Path(__file__).resolve().parents[1] / "tools" / "preview_figure_components.py"
    output_dir = tmp_path / "component-output"
    result = subprocess.run(
        [sys.executable, str(tool), "--out", str(output_dir), "--theme", "quiet-slate"],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "PASS"
    assert receipt["component_count"] == 5
    assert receipt["output_root"] == "component-output"
    assert receipt["svg"] == "component-output/sapote_mamey_figure_component_gallery.svg"
    assert receipt["manifest"] == "component-output/sapote_mamey_figure_component_manifest.json"
    assert str(tmp_path) not in result.stdout
    svg_path = output_dir / "sapote_mamey_figure_component_gallery.svg"
    manifest_path = output_dir / "sapote_mamey_figure_component_manifest.json"
    ET.parse(svg_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["theme_id"] == "quiet-slate"
    assert manifest["component_count"] == 5


def test_command_refusal_is_typed_and_path_redacted(tmp_path: Path) -> None:
    tool = Path(__file__).resolve().parents[1] / "tools" / "preview_figure_components.py"
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    sentinel = occupied / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(tool), "--out", str(occupied)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    diagnostic = json.loads(result.stderr)
    assert diagnostic["status"] == "REFUSED"
    assert diagnostic["error_code"] == "OUTPUT_REFUSED"
    assert "Traceback" not in result.stderr
    assert str(tmp_path) not in result.stderr
    assert "/Users/" not in result.stderr
    assert sentinel.read_text(encoding="utf-8") == "keep"
