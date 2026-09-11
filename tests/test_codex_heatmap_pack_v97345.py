"""v9.7.345 candidate: Codex Figure Factory heatmap publication pack."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

from mamey.interactive_figures.codex_heatmap_pack import (
    CLAIM_CEILING,
    build_codex_heatmap_pack,
    read_matrix_csv,
    select_top_rows,
)


def _matrix(path: Path, rows: int = 5, columns: int = 4) -> Path:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["gene_family"] + [f"AS-{i + 1}" for i in range(columns)])
        for i in range(rows):
            values = [i + j for j in range(columns)]
            writer.writerow([f"family_{i + 1}"] + values)
        writer.writerow(["missing_row", "", 0] + [""] * max(0, columns - 2))
    return path


def test_reader_preserves_missing_separately_from_zero(tmp_path):
    matrix = read_matrix_csv(_matrix(tmp_path / "matrix.csv"))
    missing = matrix.values[-1]
    assert missing[0] is None
    assert missing[1] == 0
    assert matrix.row_axis == "gene_family"


def test_stable_top_row_selection(tmp_path):
    matrix = read_matrix_csv(_matrix(tmp_path / "matrix.csv"))
    selected, omitted = select_top_rows(matrix, 2)
    assert selected.rows == ("family_5", "family_4")
    assert omitted == len(matrix.rows) - 2


def test_reader_rejects_populated_nonnumeric_cell(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text("family,AS-1\nfoo,not-a-number\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2.*AS-1.*non-numeric"):
        read_matrix_csv(source)


def test_reader_rejects_duplicate_axis_labels(tmp_path):
    duplicate_columns = tmp_path / "duplicate_columns.csv"
    duplicate_columns.write_text("family,AS-1,AS-1\nfoo,1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate matrix column labels"):
        read_matrix_csv(duplicate_columns)
    duplicate_rows = tmp_path / "duplicate_rows.csv"
    duplicate_rows.write_text("family,AS-1\nfoo,1\nfoo,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate matrix row labels"):
        read_matrix_csv(duplicate_rows)


def test_pack_emits_vector_html_caption_and_receipt(tmp_path):
    source = _matrix(tmp_path / "F04_data.csv", rows=7, columns=5)
    out = tmp_path / "pack"
    result = build_codex_heatmap_pack(
        [source], out, title="Per-strain BGC-class capacity",
        top_rows=0, rows_per_panel=4, columns_per_panel=3,
        citations=["antiSMASH citation reviewed by author"],
        claim_prefix="PRIVATE",
    )
    assert result["status"] == "PASS"
    item = result["results"][0]
    assert item["panels"] == 4
    figure_dir = Path(item["outdir"])
    svgs = sorted(figure_dir.glob("*.svg"))
    assert len(svgs) == 4
    svg_text = svgs[0].read_text(encoding="utf-8")
    assert "gray = missing" in svg_text
    assert "raw value:" in svg_text
    assert "family_" in svg_text
    explorer = next(figure_dir.glob("*_EXPLORER.html")).read_text(encoding="utf-8")
    assert "Accessible raw-value table" in explorer
    assert "Find row/column" in explorer
    ids = re.findall(r'\bid="([^"]+)"', explorer)
    assert len(ids) == len(set(ids)), "inline SVG panel IDs must be document-unique"
    caption = next(figure_dir.glob("*_CAPTION_METHODS.md")).read_text(encoding="utf-8")
    assert CLAIM_CEILING in caption
    assert "PRIVATE" in caption
    assert "antiSMASH citation reviewed by author" in caption
    receipt = json.loads(next(figure_dir.glob("*_RECEIPT.json")).read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS"
    assert receipt["matrix"]["missing_cells"] > 0
    assert receipt["matrix"]["observed_zero_cells"] > 0
    assert len(receipt["source"]["sha256"]) == 64
    assert receipt["source"]["portable_name"] == "F04_data.csv"
    assert receipt["independent_gates"]["publication_approval"] == "NOT_ASSESSED"


def test_cli_parser_exposes_explicit_codex_profile():
    from mamey.cli import build_parser

    args = build_parser().parse_args([
        "codex-heatmaps", "--input", "matrix.csv", "--outdir", "figures"
    ])
    assert args.command == "codex-heatmaps"
    assert args.normalization == "log1p"
    assert args.top_rows == 40
