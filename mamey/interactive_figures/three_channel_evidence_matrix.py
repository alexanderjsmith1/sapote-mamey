"""Portable static adapter for a three-channel evidence matrix.

The adapter consumes a small generic JSON or TSV contract, validates it
fail-closed, and renders one deterministic SVG.  It is intentionally independent
of package intake, scoring, biological interpretation, and the Mamey run
pipeline.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from ..console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from mamey.console import emit

import argparse
import csv
import hashlib
import html
import io
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from ..figure_save import NativeSvgFigure, save_figure
from ..figure_theme import CLAIM_SAFETY
from .theme_gallery import Theme, theme_profiles


SCHEMA_VERSION = "sapote_mamey.three_channel_evidence_matrix.v1"
RECEIPT_SCHEMA_VERSION = "sapote_mamey.three_channel_evidence_matrix_receipt.v1"
ADAPTER_STATUS = "STATIC_ADAPTER_NOT_RUNTIME_WIRED"
DEFAULT_THEME_ID = "evidence-navy"
FIGURE_ID = "THREE_CHANNEL_EVIDENCE_MATRIX"
DISPLAY_STATES: tuple[str, ...] = (
    "OBSERVED",
    "WORKFLOW_GAP",
    "BINDING_HOLD",
    "NOT_RUN",
    "NOT_APPLICABLE",
)
_STABLE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_MAX_COUNT = 1_000_000_000
_BANNED_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


@dataclass(frozen=True)
class Channel:
    channel_id: str
    channel_name: str
    display_order: int


@dataclass(frozen=True)
class Cell:
    state: str
    observed_count: int | None
    denominator_count: int
    detail: str


@dataclass(frozen=True)
class MatrixRow:
    row_key: str
    row_label: str
    sort_order: int
    cells: tuple[tuple[str, Cell], ...]

    def cell_map(self) -> dict[str, Cell]:
        return dict(self.cells)


@dataclass(frozen=True)
class MatrixModel:
    figure_title: str
    channels: tuple[Channel, ...]
    rows: tuple[MatrixRow, ...]


TSV_HEADERS: tuple[str, ...] = (
    "schema_version",
    "figure_title",
    "row_key",
    "row_label",
    "sort_order",
    "channel_1_id",
    "channel_1_name",
    "channel_1_state",
    "channel_1_observed_count",
    "channel_1_denominator_count",
    "channel_1_detail",
    "channel_2_id",
    "channel_2_name",
    "channel_2_state",
    "channel_2_observed_count",
    "channel_2_denominator_count",
    "channel_2_detail",
    "channel_3_id",
    "channel_3_name",
    "channel_3_state",
    "channel_3_observed_count",
    "channel_3_denominator_count",
    "channel_3_detail",
)


def _clean_text(value: object, field: str, *, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if _BANNED_CONTROL.search(value):
        raise ValueError(f"{field} contains a control character")
    cleaned = value.strip()
    if not allow_empty and not cleaned:
        raise ValueError(f"{field} must not be empty")
    if len(cleaned) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    return cleaned


def _stable_key(value: object, field: str) -> str:
    cleaned = _clean_text(value, field, maximum=128)
    if not _STABLE_KEY.fullmatch(cleaned):
        raise ValueError(f"{field} is not a stable portable key")
    return cleaned


def _integer(value: object, field: str, *, minimum: int = 0, maximum: int = _MAX_COUNT) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return value


def _exact_keys(data: Mapping[str, object], expected: set[str], field: str) -> None:
    actual = set(data)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"{field} keys mismatch; missing={missing}; extra={extra}")


def _parse_cell(data: object, field: str) -> Cell:
    if not isinstance(data, Mapping):
        raise ValueError(f"{field} must be an object")
    _exact_keys(data, {"state", "observed_count", "denominator_count", "detail"}, field)
    state = _clean_text(data["state"], f"{field}.state", maximum=32)
    if state not in DISPLAY_STATES:
        raise ValueError(f"{field}.state must be one of {DISPLAY_STATES}")
    denominator = _integer(data["denominator_count"], f"{field}.denominator_count")
    observed_raw = data["observed_count"]
    if state == "OBSERVED":
        observed = _integer(observed_raw, f"{field}.observed_count")
        if denominator == 0:
            raise ValueError(f"{field}.denominator_count must be positive for OBSERVED")
        if observed > denominator:
            raise ValueError(f"{field}.observed_count exceeds denominator_count")
    else:
        if observed_raw is not None:
            raise ValueError(f"{field}.observed_count must be null unless state is OBSERVED")
        observed = None
    detail = _clean_text(data["detail"], f"{field}.detail", maximum=256, allow_empty=True)
    return Cell(state, observed, denominator, detail)


def matrix_from_json_data(data: object) -> MatrixModel:
    """Validate and normalize a decoded JSON payload."""
    if not isinstance(data, Mapping):
        raise ValueError("top-level JSON value must be an object")
    _exact_keys(data, {"schema_version", "figure_title", "channels", "rows"}, "top-level")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version must equal {SCHEMA_VERSION}")
    title = _clean_text(data["figure_title"], "figure_title", maximum=160)
    raw_channels = data["channels"]
    if not isinstance(raw_channels, list) or len(raw_channels) != 3:
        raise ValueError("channels must contain exactly three objects")
    channels: list[Channel] = []
    for index, raw in enumerate(raw_channels):
        if not isinstance(raw, Mapping):
            raise ValueError(f"channels[{index}] must be an object")
        _exact_keys(raw, {"channel_id", "channel_name", "display_order"}, f"channels[{index}]")
        channels.append(Channel(
            _stable_key(raw["channel_id"], f"channels[{index}].channel_id"),
            _clean_text(raw["channel_name"], f"channels[{index}].channel_name", maximum=64),
            _integer(raw["display_order"], f"channels[{index}].display_order", minimum=1, maximum=3),
        ))
    if len({channel.channel_id for channel in channels}) != 3:
        raise ValueError("channel_id values must be unique")
    if {channel.display_order for channel in channels} != {1, 2, 3}:
        raise ValueError("display_order values must be exactly 1, 2, and 3")
    channels.sort(key=lambda channel: channel.display_order)
    channel_ids = tuple(channel.channel_id for channel in channels)

    raw_rows = data["rows"]
    if not isinstance(raw_rows, list):
        raise ValueError("rows must be an array")
    rows: list[MatrixRow] = []
    seen_keys: set[str] = set()
    for index, raw in enumerate(raw_rows):
        if not isinstance(raw, Mapping):
            raise ValueError(f"rows[{index}] must be an object")
        _exact_keys(raw, {"row_key", "row_label", "sort_order", "cells"}, f"rows[{index}]")
        row_key = _stable_key(raw["row_key"], f"rows[{index}].row_key")
        if row_key in seen_keys:
            raise ValueError(f"duplicate row_key: {row_key}")
        seen_keys.add(row_key)
        row_label = _clean_text(raw["row_label"], f"rows[{index}].row_label", maximum=512)
        sort_order = _integer(raw["sort_order"], f"rows[{index}].sort_order")
        raw_cells = raw["cells"]
        if not isinstance(raw_cells, Mapping):
            raise ValueError(f"rows[{index}].cells must be an object")
        if set(raw_cells) != set(channel_ids):
            raise ValueError(f"rows[{index}].cells must contain exactly the three declared channel_id values")
        cells = tuple((channel_id, _parse_cell(raw_cells[channel_id], f"rows[{index}].cells.{channel_id}")) for channel_id in channel_ids)
        rows.append(MatrixRow(row_key, row_label, sort_order, cells))
    rows.sort(key=lambda row: (row.sort_order, row.row_key))
    return MatrixModel(title, tuple(channels), tuple(rows))


def _tsv_integer(value: str, field: str, *, allow_empty: bool = False) -> int | None:
    if allow_empty and value == "":
        return None
    if not re.fullmatch(r"0|[1-9][0-9]*", value):
        raise ValueError(f"{field} must be a base-10 nonnegative integer")
    return _integer(int(value), field)


def matrix_from_tsv_text(text: str) -> MatrixModel:
    """Validate and normalize the portable wide-TSV representation."""
    if not text.strip():
        raise ValueError("TSV input is empty")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    if tuple(reader.fieldnames or ()) != TSV_HEADERS:
        raise ValueError("TSV header does not match the governed schema")
    source_rows = list(reader)
    if not source_rows:
        raise ValueError("header-only TSV cannot define title or channels; use JSON for an empty matrix")
    first = source_rows[0]
    title = first["figure_title"]
    channel_payload = [
        {
            "channel_id": first[f"channel_{number}_id"],
            "channel_name": first[f"channel_{number}_name"],
            "display_order": number,
        }
        for number in (1, 2, 3)
    ]
    json_rows: list[dict[str, object]] = []
    for index, row in enumerate(source_rows):
        if row["schema_version"] != SCHEMA_VERSION:
            raise ValueError(f"TSV row {index + 2} has the wrong schema_version")
        if row["figure_title"] != title:
            raise ValueError(f"TSV row {index + 2} changes figure_title")
        for number, channel in enumerate(channel_payload, start=1):
            if row[f"channel_{number}_id"] != channel["channel_id"] or row[f"channel_{number}_name"] != channel["channel_name"]:
                raise ValueError(f"TSV row {index + 2} changes channel {number}")
        cells: dict[str, object] = {}
        for number, channel in enumerate(channel_payload, start=1):
            observed = _tsv_integer(row[f"channel_{number}_observed_count"], f"TSV row {index + 2} channel {number} observed_count", allow_empty=True)
            denominator = _tsv_integer(row[f"channel_{number}_denominator_count"], f"TSV row {index + 2} channel {number} denominator_count")
            cells[str(channel["channel_id"])] = {
                "state": row[f"channel_{number}_state"],
                "observed_count": observed,
                "denominator_count": denominator,
                "detail": row[f"channel_{number}_detail"],
            }
        json_rows.append({
            "row_key": row["row_key"],
            "row_label": row["row_label"],
            "sort_order": _tsv_integer(row["sort_order"], f"TSV row {index + 2} sort_order"),
            "cells": cells,
        })
    return matrix_from_json_data({
        "schema_version": SCHEMA_VERSION,
        "figure_title": title,
        "channels": channel_payload,
        "rows": json_rows,
    })


def load_matrix_input(input_path: str | Path) -> tuple[MatrixModel, str, str]:
    """Load a JSON or TSV file and return model, format, and source hash."""
    source = Path(input_path)
    raw = source.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    suffix = source.suffix.lower()
    if suffix == ".json":
        if not raw.strip():
            raise ValueError("JSON input is empty")
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid UTF-8 JSON input: {exc}") from exc
        return matrix_from_json_data(decoded), "json", source_hash
    if suffix == ".tsv":
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"invalid UTF-8 TSV input: {exc}") from exc
        return matrix_from_tsv_text(text), "tsv", source_hash
    raise ValueError("input filename must end in .json or .tsv")


def _theme(theme_id: str) -> Theme:
    for theme in theme_profiles():
        if theme.theme_id == theme_id:
            return theme
    expected = ", ".join(theme.theme_id for theme in theme_profiles())
    raise ValueError(f"unknown theme_id {theme_id!r}; expected one of: {expected}")


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _shorten(value: str, maximum: int) -> str:
    return value if len(value) <= maximum else value[: maximum - 1].rstrip() + "…"


def _text(x: int, y: int, value: str, theme: Theme, *, size: int = 12, weight: int = 400,
          color: str | None = None, anchor: str = "start") -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{color or theme.ink}">{_esc(value)}</text>'
    )


def _state_style(state: str, theme: Theme) -> tuple[str, str, str | None]:
    return {
        "OBSERVED": ("#007C91", "#FFFFFF", None),
        "WORKFLOW_GAP": ("#E3B341", "#17212B", "workflow-gap-pattern"),
        "BINDING_HOLD": ("#6F5AA8", "#FFFFFF", "binding-hold-pattern"),
        "NOT_RUN": ("#64748B", "#FFFFFF", "not-run-pattern"),
        "NOT_APPLICABLE": (theme.card, theme.ink, "not-applicable-pattern"),
    }[state]


def _pattern_definitions(theme: Theme) -> str:
    return f'''<defs>
<pattern id="workflow-gap-pattern" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><line x1="0" y1="0" x2="0" y2="10" stroke="#17212B" stroke-width="2" opacity=".24"/></pattern>
<pattern id="binding-hold-pattern" width="12" height="12" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1.4" fill="#FFFFFF" opacity=".32"/><circle cx="9" cy="9" r="1.4" fill="#FFFFFF" opacity=".32"/></pattern>
<pattern id="not-run-pattern" width="10" height="10" patternUnits="userSpaceOnUse"><line x1="0" y1="5" x2="10" y2="5" stroke="#FFFFFF" stroke-width="1.5" opacity=".28"/></pattern>
<pattern id="not-applicable-pattern" width="12" height="12" patternUnits="userSpaceOnUse"><path d="M1,1 L11,11 M11,1 L1,11" stroke="{theme.muted}" stroke-width="1" opacity=".25"/></pattern>
</defs>'''


def render_matrix_svg(model: MatrixModel, theme_id: str = DEFAULT_THEME_ID) -> str:
    """Render a deterministic, accessible SVG for a validated model."""
    theme = _theme(theme_id)
    width = 1280
    margin = 24
    key_x, key_w = margin, 128
    label_x, label_w = key_x + key_w, 344
    channel_x = label_x + label_w
    channel_w = 252
    header_y = 92
    row_h = 56
    legend_h = 110
    body_rows = max(1, len(model.rows))
    height = header_y + 52 + body_rows * row_h + legend_h
    parts: list[str] = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="matrix-title matrix-desc">')
    parts.append(f'<title id="matrix-title">{_esc(model.figure_title)}</title>')
    parts.append(f'<desc id="matrix-desc">Three named evidence channels displayed for {len(model.rows)} ordered rows with typed states and explicit denominators.</desc>')
    parts.append(_pattern_definitions(theme))
    parts.append(f'<rect width="100%" height="100%" fill="{theme.paper}"/>')
    parts.append(_text(margin, 36, model.figure_title, theme, size=24, weight=700))
    parts.append(_text(margin, 60, f"Three Channels · {len(model.rows)} Rows · Denominators Shown", theme, size=11, color=theme.muted))
    parts.append(f'<rect x="{margin}" y="{header_y}" width="{width - 2 * margin}" height="42" rx="7" fill="{theme.card}" stroke="{theme.line}"/>')
    parts.append(_text(key_x + 8, header_y + 26, "Row Key", theme, size=10, weight=700))
    parts.append(_text(label_x + 8, header_y + 26, "Row Label", theme, size=10, weight=700))
    for index, channel in enumerate(model.channels):
        x = channel_x + index * channel_w
        parts.append(_text(x + channel_w // 2, header_y + 26, _shorten(channel.channel_name, 30), theme, size=10, weight=700, anchor="middle"))

    row_start = header_y + 48
    if not model.rows:
        parts.append(f'<rect x="{margin}" y="{row_start}" width="{width - 2 * margin}" height="{row_h - 6}" rx="6" fill="{theme.card}" stroke="{theme.line}"/>')
        parts.append(_text(width // 2, row_start + 30, "No Rows Supplied", theme, size=12, weight=700, anchor="middle", color=theme.muted))
    for row_index, row in enumerate(model.rows):
        y = row_start + row_index * row_h
        parts.append(f'<rect x="{margin}" y="{y}" width="{width - 2 * margin}" height="{row_h - 6}" rx="6" fill="{theme.card}" stroke="{theme.line}"/>')
        parts.append(_text(key_x + 8, y + 29, _shorten(row.row_key, 18), theme, size=9, weight=700, color=theme.muted))
        display_label = _shorten(row.row_label, 48)
        parts.append(f'<g>{_text(label_x + 8, y + 29, display_label, theme, size=10, weight=700)}<title>{_esc(row.row_label)}</title></g>')
        cell_map = row.cell_map()
        for channel_index, channel in enumerate(model.channels):
            cell = cell_map[channel.channel_id]
            x = channel_x + channel_index * channel_w + 5
            cell_y = y + 5
            cell_w = channel_w - 10
            cell_h = row_h - 16
            fill, text_color, pattern = _state_style(cell.state, theme)
            parts.append(f'<g><rect x="{x}" y="{cell_y}" width="{cell_w}" height="{cell_h}" rx="5" fill="{fill}" stroke="{theme.line}"/>')
            if pattern:
                parts.append(f'<rect x="{x}" y="{cell_y}" width="{cell_w}" height="{cell_h}" rx="5" fill="url(#{pattern})"/>')
            display_state = cell.state.replace("_", " ").title()
            parts.append(_text(x + cell_w // 2, cell_y + 16, display_state, theme, size=8, weight=700, anchor="middle", color=text_color))
            counts = f"{cell.observed_count} / {cell.denominator_count}" if cell.state == "OBSERVED" else f"Denom {cell.denominator_count}"
            parts.append(_text(x + cell_w // 2, cell_y + 31, counts, theme, size=8, weight=700, anchor="middle", color=text_color))
            detail = f" · {cell.detail}" if cell.detail else ""
            parts.append(f'<title>{_esc(row.row_key)} · {_esc(row.row_label)} · {_esc(channel.channel_name)} · {_esc(display_state)} · {_esc(counts)}{_esc(detail)}</title></g>')

    legend_y = row_start + body_rows * row_h + 18
    parts.append(_text(margin, legend_y, "Display States", theme, size=10, weight=700))
    legend_x = margin
    for state in DISPLAY_STATES:
        fill, text_color, pattern = _state_style(state, theme)
        legend_x += 112 if state != "NOT_APPLICABLE" else 132
        parts.append(f'<rect x="{legend_x}" y="{legend_y - 13}" width="16" height="16" rx="3" fill="{fill}" stroke="{theme.line}"/>')
        if pattern:
            parts.append(f'<rect x="{legend_x}" y="{legend_y - 13}" width="16" height="16" rx="3" fill="url(#{pattern})"/>')
        parts.append(_text(legend_x + 22, legend_y, state.replace("_", " ").title(), theme, size=8, weight=700, color=theme.ink))
    footer_y = height - 18
    parts.append(f'<line x1="{margin}" y1="{footer_y - 16}" x2="{width - margin}" y2="{footer_y - 16}" stroke="{theme.line}"/>')
    parts.append(_text(margin, footer_y, CLAIM_SAFETY + " Judgment deferred.", theme, size=8, weight=700, color=theme.muted))
    parts.append(f'<metadata>figure_id={FIGURE_ID}</metadata>')
    parts.append("</svg>")
    return "\n".join(parts)


def _state_counts(model: MatrixModel) -> dict[str, int]:
    counts = {state: 0 for state in DISPLAY_STATES}
    for row in model.rows:
        for _, cell in row.cells:
            counts[cell.state] += 1
    return counts


def write_matrix(input_path: str | Path, output_dir: str | Path, theme_id: str = DEFAULT_THEME_ID,
                 *, emit_png: bool = False) -> dict[str, object]:
    """Validate input and write SVG, optional 300-DPI PNG, and a portable receipt."""
    model, input_format, input_hash = load_matrix_input(input_path)
    _theme(theme_id)
    svg = render_matrix_svg(model, theme_id)
    svg_bytes = svg.encode("utf-8")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    svg_name = "three_channel_evidence_matrix.svg"
    receipt_name = "three_channel_evidence_matrix.receipt.json"
    pair_receipt = None
    if emit_png:
        pair_receipt = save_figure(
            NativeSvgFigure(svg), figure_id=FIGURE_ID,
            out_stem=root / "three_channel_evidence_matrix",
            renderer="three_channel_native_svg+cairosvg",
            package_dir=root, provenance=f"input_sha256={input_hash};theme_id={theme_id}",
        )
    else:
        (root / svg_name).write_bytes(svg_bytes)
    outputs = [{"format": "SVG", "logical_locator": svg_name,
                "sha256": hashlib.sha256(svg_bytes).hexdigest(), "bytes": len(svg_bytes)}]
    if pair_receipt is not None:
        png_info = pair_receipt["outputs"]["png"]
        outputs.append({"format": "PNG", **png_info,
                        "dpi": 300, "width_in": 7.2, "pixel_width": 2160})
    receipt: dict[str, object] = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "adapter_status": ADAPTER_STATUS,
        "input_format": input_format,
        "input_sha256": input_hash,
        "theme_id": theme_id,
        "figure_id": FIGURE_ID,
        "figure_title": model.figure_title,
        "row_count": len(model.rows),
        "channel_count": len(model.channels),
        "channels": [
            {"channel_id": channel.channel_id, "channel_name": channel.channel_name, "display_order": channel.display_order}
            for channel in model.channels
        ],
        "ordered_row_keys": [row.row_key for row in model.rows],
        "state_counts": _state_counts(model),
        "svg_locator": svg_name,
        "svg_sha256": hashlib.sha256(svg_bytes).hexdigest(),
        "svg_bytes": len(svg_bytes),
        "outputs": outputs,
        "claim_safety_footer": CLAIM_SAFETY + " Judgment deferred.",
        "paired_figure_receipt": pair_receipt,
        "caption": "Cell states describe evidence or workflow display status; they do not infer biological absence.",
    }
    (root / receipt_name).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**receipt, "receipt_locator": receipt_name}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a static three-channel evidence matrix from governed JSON or TSV.")
    parser.add_argument("input", help="Input .json or .tsv file")
    parser.add_argument("--out", required=True, help="Output directory for SVG and rendering receipt")
    parser.add_argument("--theme", default=DEFAULT_THEME_ID, choices=[theme.theme_id for theme in theme_profiles()])
    parser.add_argument("--emit-png", action="store_true", help="Also emit a 7.2-inch 300-DPI PNG via cairosvg")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        receipt = write_matrix(args.input, args.out, args.theme, emit_png=args.emit_png)
    # BC2-407: every validation refusal in this module (_clean_text, _stable_key, _integer,
    # _exact_keys, _parse_cell, matrix_from_json_data, matrix_from_tsv_text, load_matrix_input,
    # _theme -- confirmed by grep, there is no `raise RuntimeError` anywhere in this file) raises
    # ValueError, not RuntimeError. Catching RuntimeError here was dead code: every malformed
    # input this fail-closed adapter is designed to refuse instead produced an uncaught traceback
    # and exit code 1, not the documented clean stderr message + exit code 2.
    except ValueError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    emit(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
