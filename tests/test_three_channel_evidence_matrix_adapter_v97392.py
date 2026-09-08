from __future__ import annotations

import copy
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mamey.interactive_figures.component_gallery import component_specs
from mamey.interactive_figures.three_channel_evidence_matrix import (
    DISPLAY_STATES,
    FIGURE_ID,
    SCHEMA_VERSION,
    load_matrix_input,
    matrix_from_json_data,
    matrix_from_tsv_text,
    render_matrix_svg,
    write_matrix,
)
from mamey.figure_theme import CLAIM_SAFETY


ROOT = Path(__file__).resolve().parents[1]
JSON_FIXTURE = ROOT / "examples" / "figure_factory" / "three_channel_evidence_matrix.synthetic.json"
TSV_FIXTURE = ROOT / "examples" / "figure_factory" / "three_channel_evidence_matrix.synthetic.tsv"
THEMES = (
    "evidence-navy",
    "scientific-cream",
    "signal-dark",
    "high-contrast",
    "field-notebook",
    "quiet-slate",
)
BANNED_CANVAS_TERMS = (
    "claim ceiling",
    "claim-ceiling",
    "governance",
    "owner review",
    "privacy",
    "approval",
    "acceptance",
    "release",
    "publication",
)


def fixture_payload() -> dict[str, object]:
    return json.loads(JSON_FIXTURE.read_text(encoding="utf-8"))


def test_json_and_tsv_normalize_and_render_identically() -> None:
    json_model, json_format, _ = load_matrix_input(JSON_FIXTURE)
    tsv_model, tsv_format, _ = load_matrix_input(TSV_FIXTURE)
    assert json_format == "json"
    assert tsv_format == "tsv"
    assert json_model == tsv_model
    assert render_matrix_svg(json_model) == render_matrix_svg(tsv_model)
    assert [row.row_key for row in json_model.rows] == ["row-010", "row-020", "row-030", "row-040", "row-050"]


def test_shuffled_rows_and_channels_are_deterministic() -> None:
    original = fixture_payload()
    shuffled = copy.deepcopy(original)
    shuffled["rows"] = list(reversed(shuffled["rows"]))
    shuffled["channels"] = list(reversed(shuffled["channels"]))
    assert matrix_from_json_data(original) == matrix_from_json_data(shuffled)
    assert render_matrix_svg(matrix_from_json_data(original), "quiet-slate") == render_matrix_svg(matrix_from_json_data(shuffled), "quiet-slate")


def test_all_typed_states_and_denominators_are_visible() -> None:
    model = matrix_from_json_data(fixture_payload())
    svg = render_matrix_svg(model)
    for state in DISPLAY_STATES:
        assert state.replace("_", " ").title() in svg
    for count in ("3 / 5", "2 / 3", "5 / 8", "11 / 21", "Denom 13"):
        assert count in svg
    assert CLAIM_SAFETY in svg


def test_missing_or_malformed_channels_fail_closed() -> None:
    two_channels = fixture_payload()
    two_channels["channels"] = two_channels["channels"][:2]
    with pytest.raises(ValueError, match="exactly three"):
        matrix_from_json_data(two_channels)
    missing_cell = fixture_payload()
    del missing_cell["rows"][0]["cells"]["reference_a"]
    with pytest.raises(ValueError, match="exactly the three"):
        matrix_from_json_data(missing_cell)
    bad_header = TSV_FIXTURE.read_text(encoding="utf-8").replace("figure_title", "title", 1)
    with pytest.raises(ValueError, match="header"):
        matrix_from_tsv_text(bad_header)
    control_character = fixture_payload()
    control_character["figure_title"] = "Synthetic\nTitle"
    with pytest.raises(ValueError, match="control character"):
        matrix_from_json_data(control_character)


def test_duplicate_row_keys_fail_closed() -> None:
    data = fixture_payload()
    data["rows"][1]["row_key"] = data["rows"][0]["row_key"]
    with pytest.raises(ValueError, match="duplicate row_key"):
        matrix_from_json_data(data)


def test_cell_count_contract_fails_closed() -> None:
    bad_gap = fixture_payload()
    bad_gap["rows"][0]["cells"]["reference_a"]["observed_count"] = 1
    with pytest.raises(ValueError, match="must be null"):
        matrix_from_json_data(bad_gap)
    bad_observed = fixture_payload()
    bad_observed["rows"][1]["cells"]["reference_a"]["observed_count"] = 9
    with pytest.raises(ValueError, match="exceeds denominator"):
        matrix_from_json_data(bad_observed)


def test_long_labels_are_truncated_on_canvas_but_retained_accessibly() -> None:
    data = fixture_payload()
    long_label = "Synthetic row label " + "with deterministic overflow handling " * 8
    data["rows"][0]["row_label"] = long_label
    svg = render_matrix_svg(matrix_from_json_data(data))
    assert long_label in svg
    assert "…" in svg
    ET.fromstring(svg)


def test_empty_input_and_empty_matrix_contract(tmp_path: Path) -> None:
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_matrix_input(empty_file)
    data = fixture_payload()
    data["rows"] = []
    svg = render_matrix_svg(matrix_from_json_data(data), "high-contrast")
    assert "No Rows Supplied" in svg
    ET.fromstring(svg)


def test_all_themes_parse_and_canvas_has_no_banned_terms() -> None:
    model = matrix_from_json_data(fixture_payload())
    for theme in THEMES:
        svg = render_matrix_svg(model, theme)
        ET.fromstring(svg)
        lowered = svg.lower()
        assert not [term for term in BANNED_CANVAS_TERMS if term in lowered]
        assert "/Users/" not in svg
        assert "AS-" not in svg
        assert "AJS-" not in svg
        assert "PENDING-" not in svg


def test_rejected_component_remains_absent() -> None:
    ids = [spec.component_id for spec in component_specs()]
    assert "claim-ceiling-ladder" not in ids
    assert "evidence-stage-ladder" in ids


def test_cli_writes_portable_receipt_and_deterministic_svg(tmp_path: Path) -> None:
    tool = ROOT / "tools" / "render_three_channel_evidence_matrix.py"
    first = tmp_path / "first"
    second = tmp_path / "second"
    commands = (
        [sys.executable, str(tool), str(JSON_FIXTURE), "--out", str(first), "--theme", "field-notebook"],
        [sys.executable, str(tool), str(JSON_FIXTURE), "--out", str(second), "--theme", "field-notebook"],
    )
    receipts = []
    for command in commands:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        receipts.append(json.loads(result.stdout))
    svg_first = (first / "three_channel_evidence_matrix.svg").read_bytes()
    svg_second = (second / "three_channel_evidence_matrix.svg").read_bytes()
    assert svg_first == svg_second
    assert receipts[0] == receipts[1]
    receipt_text = (first / "three_channel_evidence_matrix.receipt.json").read_text(encoding="utf-8")
    receipt = json.loads(receipt_text)
    assert receipt["schema_version"].endswith("receipt.v1")
    assert receipt["channel_count"] == 3
    assert receipt["row_count"] == 5
    assert receipt["svg_locator"] == "three_channel_evidence_matrix.svg"
    assert receipt["figure_id"] == FIGURE_ID
    assert receipt["claim_safety_footer"].startswith(CLAIM_SAFETY)
    assert CLAIM_SAFETY in svg_first.decode("utf-8")
    assert f"figure_id={FIGURE_ID}" in svg_first.decode("utf-8")
    assert receipt["ordered_row_keys"] == ["row-010", "row-020", "row-030", "row-040", "row-050"]
    assert "/Users/" not in receipt_text


def test_cli_reports_a_malformed_input_as_a_clean_typed_refusal_not_a_traceback(tmp_path: Path) -> None:
    # BC2-407: every validator in this module raises ValueError, not RuntimeError -- main()'s
    # except clause must actually match, or every malformed-input run (the CLI's primary failure
    # mode, since this adapter's whole job is fail-closed validation) crashes with a raw Python
    # traceback and exit code 1 instead of the documented clean stderr message + exit code 2.
    tool = ROOT / "tools" / "render_three_channel_evidence_matrix.py"
    bad_input = tmp_path / "bad.json"
    bad_input.write_text("{}", encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, str(tool), str(bad_input), "--out", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 2, (
        f"expected the documented exit code 2 for a validation refusal, got {result.returncode}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "Traceback (most recent call last)" not in result.stderr, (
        "a validation refusal must be a clean typed message, not an uncaught traceback"
    )
    assert "keys mismatch" in result.stderr
    assert result.stdout == ""
    assert not out.exists() or not any(out.iterdir()), "a refused input must not leave partial output"


def test_optional_png_is_rendered_from_the_same_svg_and_hash_bound(tmp_path: Path, monkeypatch) -> None:
    class FakeCairoSVG:
        @staticmethod
        def svg2png(*, bytestring, output_width):
            assert CLAIM_SAFETY.encode("utf-8") in bytestring
            assert output_width == 2160
            return b"\x89PNG\r\n\x1a\nsynthetic-raster"

    monkeypatch.setitem(sys.modules, "cairosvg", FakeCairoSVG)
    receipt = write_matrix(JSON_FIXTURE, tmp_path / "render", emit_png=True)
    png = tmp_path / "render" / "three_channel_evidence_matrix.png"
    assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert receipt["outputs"][1]["format"] == "PNG"
    assert receipt["outputs"][1]["sha256"] == __import__("hashlib").sha256(png.read_bytes()).hexdigest()
    assert receipt["outputs"][1]["dpi"] == 300


def test_schema_version_and_fixture_are_generic() -> None:
    data = fixture_payload()
    assert data["schema_version"] == SCHEMA_VERSION
    fixture_text = JSON_FIXTURE.read_text(encoding="utf-8") + TSV_FIXTURE.read_text(encoding="utf-8")
    assert "/Users/" not in fixture_text
    assert "AS-" not in fixture_text
    assert "AJS-" not in fixture_text
    assert "PENDING-" not in fixture_text
