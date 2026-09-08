from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from mamey.interactive_figures.theme_gallery import THEMES, PROTOTYPE_STATUS, render_theme_gallery_html, render_theme_overview_svg, write_theme_gallery


def test_theme_gallery_has_six_named_visual_directions():
    assert len(THEMES) == 6
    assert len({theme.theme_id for theme in THEMES}) == 6
    assert all(theme.name == theme.name.title() for theme in THEMES)
    assert all(theme.theme_id and theme.paper.startswith("#") and theme.ink.startswith("#") for theme in THEMES)


def test_html_is_self_contained_and_claim_safe():
    page = render_theme_gallery_html()
    assert "https://" not in page
    assert "<script id=\"theme-data\"" in page
    assert "Deterministic Extraction · Evidence-Aware Presentation" in page
    assert "No Biological Interpretation" not in page
    assert "no biological interpretation" in page.lower()
    assert "judgment" not in page.lower()
    assert PROTOTYPE_STATUS.replace("_", " ") in page
    payload = re.search(r'<script id="theme-data" type="application/json">(.*?)</script>', page, re.S)
    assert payload is not None
    assert set(json.loads(payload.group(1))) == {theme.theme_id for theme in THEMES}


def test_writer_emits_portable_html_and_svg(tmp_path: Path):
    output_dir = tmp_path / "theme-output"
    receipt = write_theme_gallery(output_dir)
    assert receipt["status"] == "PASS"
    assert receipt["theme_count"] == 6
    assert receipt["output_root"] == "theme-output"
    assert receipt["html"] == "theme-output/sapote_mamey_figure_theme_gallery.html"
    assert receipt["svg"] == "theme-output/sapote_mamey_figure_theme_overview.svg"
    assert str(tmp_path) not in json.dumps(receipt)
    html_path = output_dir / "sapote_mamey_figure_theme_gallery.html"
    svg_path = output_dir / "sapote_mamey_figure_theme_overview.svg"
    assert html_path.exists() and svg_path.exists()
    assert "<svg" in svg_path.read_text(encoding="utf-8")
    assert svg_path.read_text(encoding="utf-8").count("Generic Evidence Marks") == 6


def test_command_refusal_is_typed_and_path_redacted(tmp_path: Path) -> None:
    tool = Path(__file__).resolve().parents[1] / "tools" / "preview_figure_themes.py"
    occupied = tmp_path / "occupied"
    occupied.mkdir()
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
