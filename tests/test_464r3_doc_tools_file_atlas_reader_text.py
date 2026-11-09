"""The file atlas shows what a file does, without release tags or audit-game jargon."""
import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("file_atlas_464r3", ROOT / "tools" / "file_atlas.py")
atlas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atlas)


@pytest.mark.parametrize("raw, expected", [
    ("CSV/TSV formula-injection neutraliser (v9.7.409, DEEP_AUDIT2 export-injection; "
     "v9.7.410 CLAUDE_410_csv_writer_coverage: full writer coverage).", "CSV/TSV formula-injection neutraliser."),
    ("M5_452 P5: caption and METHODS for a page.", "caption and METHODS for a page."),
    ("v9.7.405: reads a table.", "reads a table."),
    ("Draw a heatmap (top 40 loci).", "Draw a heatmap (top 40 loci)."),
    ("Write GENOMES_USED beside the figure.", "Write GENOMES_USED beside the figure."),
])
def test_reader_summary(raw, expected):
    assert atlas._reader_summary(raw) == expected


def test_rendered_atlas_has_plain_heading():
    source = (ROOT / "tools" / "file_atlas.py").read_text(encoding="utf-8")
    assert "Files with no detected caller" in source
    assert "bunny-hop" not in source
