#!/usr/bin/env python3
"""Hash-bound Figure Factory consumer for existing MLSA/GToTree IQ-TREE outputs.

This module renders; it never infers a tree, relabels tips by prefix, or derives
ANI/BGC/domain/Mode-B/bioassay annotations. Those evidence channels meet only through an
explicit one-to-one tip/strain crosswalk supplied by the scientific adapter.
"""
from __future__ import annotations

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

# Composer delta (PF402-03 repair): bundle-root bootstrap so the tool imports from any
# working directory, as its sibling tools do (test_tool_front_doors gate).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.figure_policy import (
    CAPTION_METHOD_SCHEMA,
    PUBLICATION_PROFILES,
    plan_heatmap_scale,
    validate_caption_methods,
    validate_layout_rectangles,
    validate_publication_artwork,
    validate_tick_label_data_clearance,
)

SCHEMA_VERSION = "sapote.tree-figure-factory.v1"
TREE_CHANNELS = frozenset({"MLSA_PROTEIN5", "MLSA_16S_SEPARATE", "CORE_GENOME_GTOTTREE_IQTREE"})
INPUT_ROLES = frozenset({
    "tree", "alignment", "tree_workflow_receipt", "model_receipt", "seed_receipt",
    "outgroup_roster", "final_tip_roster", "tip_crosswalk", "annotation_matrix",
})
ANNOTATION_CHANNELS = frozenset({"ANI", "BGC", "DOMAIN", "MODE_B", "ASSEMBLY", "BIOASSAY"})
TRACK_COLORS = {
    "ANI": "#0072B2", "BGC": "#009E73", "DOMAIN": "#E69F00",
    "MODE_B": "#CC79A7", "ASSEMBLY": "#666666", "BIOASSAY": "#D55E00",
}
CLAIM_CEILING = (
    "MLSA, core-genome topology, ANI, BGC, domain, Mode B, and strain-level bioassay evidence "
    "remain separate. Bioassay values describe the recorded strain-level assay and are not "
    "attributed to a locus or compound. "
    "Visual proximity does not establish product identity, HGT, ancestry direction, activity, "
    "or equivalence between MLSA and core-genome topology."
)


class Node:
    __slots__ = ("name", "length", "support", "children", "parent")

    def __init__(self) -> None:
        self.name = ""
        self.length = 0.0
        self.support = ""
        self.children: list[Node] = []
        self.parent: Node | None = None

    def leaves(self):
        if not self.children:
            yield self
        for child in self.children:
            yield from child.leaves()


def parse_newick(text: str) -> Node:
    """Parse the canonical IQ-TREE Newick subset and fail on unsupported syntax."""
    source = text.strip()
    if not source.endswith(";"):
        raise ValueError("tree must terminate with a semicolon")
    if "[" in source or "]" in source:
        raise ValueError("Newick comments/annotations are unsupported; export canonical Newick")
    source = source[:-1]
    position = 0

    def skip_space() -> None:
        nonlocal position
        while position < len(source) and source[position].isspace():
            position += 1

    def label() -> str:
        nonlocal position
        skip_space()
        if position < len(source) and source[position] in "'\"":
            quote = source[position]
            position += 1
            value = []
            while position < len(source):
                if source[position] == quote:
                    if position + 1 < len(source) and source[position + 1] == quote:
                        value.append(quote); position += 2; continue
                    position += 1
                    return "".join(value)
                value.append(source[position]); position += 1
            raise ValueError("unterminated quoted Newick label")
        start = position
        while position < len(source) and source[position] not in "(),:":
            position += 1
        return source[start:position].strip()

    def node() -> Node:
        nonlocal position
        skip_space()
        if position >= len(source):
            raise ValueError("unexpected end of Newick")
        current = Node()
        if source[position] == "(":
            position += 1
            while True:
                child = node(); child.parent = current; current.children.append(child)
                skip_space()
                if position >= len(source):
                    raise ValueError("unclosed Newick clade")
                if source[position] == ",":
                    position += 1; continue
                if source[position] == ")":
                    position += 1; break
                raise ValueError(f"unexpected Newick token at character {position}")
            current.support = label()
        else:
            current.name = label()
            if not current.name:
                raise ValueError("every Newick tip requires an explicit label")
        skip_space()
        if position < len(source) and source[position] == ":":
            position += 1
            start = position
            while position < len(source) and source[position] not in "(),":
                position += 1
            token = source[start:position].strip()
            try:
                current.length = float(token)
            except ValueError as exc:
                raise ValueError(f"invalid branch length {token!r}") from exc
            if not math.isfinite(current.length) or current.length < 0:
                raise ValueError("branch lengths must be finite and non-negative")
        return current

    root = node()
    skip_space()
    if position != len(source):
        raise ValueError(f"unparsed Newick content at character {position}")
    tips = tip_order(root)
    if len(tips) != len(set(tips)):
        raise ValueError("tree contains duplicate tip labels")
    return root


def tip_order(root: Node) -> list[str]:
    return [tip.name for tip in root.leaves()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_file(root: Path, locator: str) -> Path:
    relative = Path(locator)
    if relative.is_absolute():
        raise ValueError("input locators must be relative")
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("input locator escapes external_data_root") from exc
    if not path.is_file():
        raise FileNotFoundError(locator)
    return path


def _bind_inputs(config: Mapping[str, Any], root: Path) -> dict[str, dict[str, Any]]:
    inputs = list(config.get("inputs", []))
    by_role = {str(row.get("role", "")): dict(row) for row in inputs}
    if len(inputs) != len(INPUT_ROLES) or set(by_role) != INPUT_ROLES:
        raise ValueError(f"inputs require exactly these roles: {sorted(INPUT_ROLES)}")
    for role, row in by_role.items():
        expected = str(row.get("sha256", "")).lower()
        if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
            raise ValueError(f"{role} requires an exact lowercase SHA-256")
        path = _safe_file(root, str(row.get("logical_locator", "")))
        actual = sha256_file(path)
        if expected != actual:
            raise ValueError(f"{role} SHA-256 mismatch")
        row.update(path=path, sha256=actual, bytes=path.stat().st_size)
    return by_role


def _read_tsv(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or any(field not in reader.fieldnames for field in required):
            raise ValueError(f"{path.name} is missing required fields {required}")
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def load_crosswalk(path: Path) -> dict[str, dict[str, str]]:
    rows = _read_tsv(path, ("newick_label", "strain", "display_label", "role", "genus"))
    by_tip: dict[str, dict[str, str]] = {}
    strains: set[str] = set()
    for number, row in enumerate(rows, 1):
        if not all(row[field] for field in ("newick_label", "strain", "display_label", "role", "genus")):
            raise ValueError(f"crosswalk row {number} is incomplete")
        if row["newick_label"] in by_tip:
            raise ValueError(f"duplicate crosswalk newick_label: {row['newick_label']}")
        if row["strain"] in strains:
            raise ValueError(f"duplicate crosswalk strain: {row['strain']}")
        if row["role"] not in {"STUDY", "REFERENCE", "OUTGROUP", "EXTERNAL_BENCHMARK"}:
            raise ValueError(f"invalid crosswalk role: {row['role']}")
        by_tip[row["newick_label"]] = row
        strains.add(row["strain"])
    return by_tip


def _validate_join(root: Node, bindings: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, dict[str, str]]]:
    roster = _read_tsv(bindings["final_tip_roster"]["path"], ("newick_label", "state", "reason"))
    if len({row["newick_label"] for row in roster}) != len(roster):
        raise ValueError("final tip roster contains duplicate labels")
    if any(row["state"] not in {"INCLUDED", "OMITTED"} for row in roster):
        raise ValueError("final tip roster state must be INCLUDED or OMITTED")
    if any(not row["reason"] for row in roster):
        raise ValueError("every final tip roster row requires a reason")
    included = [row for row in roster if row["state"] == "INCLUDED"]
    omitted = [row for row in roster if row["state"] == "OMITTED"]
    tree_tips = tip_order(root)
    included_labels = {row["newick_label"] for row in included}
    if set(tree_tips) != included_labels or len(tree_tips) != len(included):
        raise ValueError("tree tips must equal the explicit INCLUDED roster exactly")
    crosswalk = load_crosswalk(bindings["tip_crosswalk"]["path"])
    roster_labels = {row["newick_label"] for row in roster}
    if set(crosswalk) != roster_labels:
        raise ValueError("crosswalk labels must equal the complete final tip roster")
    outgroups = _read_tsv(bindings["outgroup_roster"]["path"], ("newick_label",))
    if len(outgroups) != 1 or outgroups[0]["newick_label"] not in included_labels:
        raise ValueError("outgroup roster must contain exactly one included tip")
    outgroup = outgroups[0]["newick_label"]
    if crosswalk[outgroup]["role"] != "OUTGROUP":
        raise ValueError("outgroup crosswalk row must carry role OUTGROUP")
    if sum(row["role"] == "OUTGROUP" for row in crosswalk.values()) != 1:
        raise ValueError("crosswalk must carry exactly one OUTGROUP role")
    return included, omitted, crosswalk


def _load_annotations(path: Path, included_strains: set[str]) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    raw = _read_tsv(path, ("strain", "channel", "feature", "value", "state"))
    rows, keys = [], set()
    for number, row in enumerate(raw, 1):
        if row["strain"] not in included_strains:
            raise ValueError(f"annotation row {number} is not an included crosswalk strain")
        if row["channel"] not in ANNOTATION_CHANNELS:
            raise ValueError(f"annotation row {number} has invalid channel")
        if not row["feature"]:
            raise ValueError(f"annotation row {number} has blank feature")
        key = (row["strain"], row["channel"], row["feature"])
        if key in keys:
            raise ValueError(f"duplicate annotation key: {key}")
        keys.add(key)
        if row["state"] == "OBSERVED":
            try:
                value = float(row["value"])
            except ValueError as exc:
                raise ValueError(f"annotation row {number} requires a numeric observed value") from exc
            if not math.isfinite(value):
                raise ValueError(f"annotation row {number} is non-finite")
        elif row["state"] in {"MISSING", "NOT_MEASURED", "NOT_APPLICABLE"}:
            if row["value"]:
                raise ValueError(f"annotation row {number} non-observed state must have blank value")
            value = None
        else:
            raise ValueError(f"annotation row {number} has invalid typed state")
        rows.append({**row, "value": value})
    columns = sorted({(row["channel"], row["feature"]) for row in rows})
    return rows, columns


def _verify_method_receipts(bindings: Mapping[str, Mapping[str, Any]], channel: str,
                            methods: Mapping[str, Any]) -> None:
    expected = (
        ("tree_workflow_receipt", "tree_channel", channel),
        ("tree_workflow_receipt", "tool", str(methods["tool"])),
        ("model_receipt", "model", str(methods["model"])),
        ("seed_receipt", "seed", str(methods["seed"])),
    )
    cache: dict[str, Any] = {}
    for role, field, value in expected:
        if role not in cache:
            try:
                cache[role] = json.loads(bindings[role]["path"].read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"{role} must be a readable JSON object") from exc
        if str(cache[role].get(field, "")) != value:
            raise ValueError(f"{role}.{field} does not match the configured method")


def assemble_overlay(order, crosswalk, annotations, columns):
    """Exact join only; absence of any included tip or strain is a refusal."""
    by_key = {(row["strain"], row["channel"], row["feature"]): row for row in annotations}
    output = []
    for tip in order:
        if tip not in crosswalk:
            raise ValueError(f"unmapped tree tip: {tip}")
        mapped = crosswalk[tip]
        cells = [by_key.get((mapped["strain"], channel, feature), {
            "state": "MISSING", "value": None,
        }) for channel, feature in columns]
        output.append({"tip": tip, **mapped, "cells": cells})
    return output


def _node_coordinates(root: Node) -> tuple[dict[Node, float], dict[Node, float], str]:
    tips = list(root.leaves())
    y = {tip: float(index) for index, tip in enumerate(tips)}
    has_lengths = any(node.length > 0 for node in _walk(root) if node.parent is not None)
    mode = "BRANCH_LENGTH" if has_lengths else "TOPOLOGY_DEPTH"
    x: dict[Node, float] = {root: 0.0}

    def visit(node: Node, depth: int) -> None:
        for child in node.children:
            x[child] = x[node] + (child.length if has_lengths else 1.0)
            visit(child, depth + 1)
        if node.children:
            y[node] = sum(y[child] for child in node.children) / len(node.children)

    visit(root, 0)
    return x, y, mode


def _walk(root: Node):
    yield root
    for child in root.children:
        yield from _walk(child)


def _wrapped_display_label(value: str, profile: str) -> str:
    """Wrap explicit display labels without changing or inferring their content."""
    width = 18 if profile == "SINGLE_COLUMN" else 30
    return "\n".join(textwrap.wrap(
        value, width=width, break_long_words=True, break_on_hyphens=False,
        replace_whitespace=False, drop_whitespace=False,
    ))


def _is_perfect_support(value: str) -> bool:
    tokens = [token.strip() for token in value.split("/")]
    if not tokens or any(not token for token in tokens):
        return False
    try:
        return all(float(token) == 100.0 for token in tokens)
    except ValueError:
        return False


def _render(root: Node, rows: list[dict[str, Any]], columns: list[tuple[str, str]], stage: Path, profile: str) -> tuple[list[Path], dict[str, Any]]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["svg.hashsalt"] = "sapote-tree-figure-factory-v1"
        matplotlib.rcParams["svg.fonttype"] = "none"
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("tree Figure Factory requires the figures extra") from exc
    width = PUBLICATION_PROFILES[profile]["width_in"]
    height = max(3.5, 0.42 * len(rows) + 1.5)
    annotation_ratio = max(1.0, 0.48 * len(columns))
    fig, (tree_axis, track_axis) = plt.subplots(
        1, 2, figsize=(width, height),
        gridspec_kw={"width_ratios": [2.7, annotation_ratio]},
    )
    bottom_margin = 0.28 if profile == "SINGLE_COLUMN" else 0.20
    fig.subplots_adjust(
        left=0.025, right=0.985, top=0.92,
        bottom=bottom_margin,
        wspace=0.08,
    )
    x, y, geometry_mode = _node_coordinates(root)
    maximum_x = max(x.values()) or 1.0
    support_text = []
    perfect_support_count = 0
    for node in _walk(root):
        if node.children:
            tree_axis.plot([x[node], x[node]], [min(y[c] for c in node.children), max(y[c] for c in node.children)], color="#333333", lw=0.8)
            if node.support:
                if _is_perfect_support(node.support):
                    tree_axis.plot(x[node], y[node], marker="o", markersize=3.2,
                                   color="#333333", markeredgewidth=0)
                    perfect_support_count += 1
                else:
                    support_text.append(tree_axis.text(
                        x[node] + maximum_x * 0.012,
                        y[node], node.support, fontsize=8, ha="left", va="bottom",
                        bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.4},
                    ))
        if node.parent is not None:
            tree_axis.plot([x[node.parent], x[node]], [y[node], y[node]], color="#333333", lw=0.8)
    tip_text = []
    for row in rows:
        node = next(tip for tip in root.leaves() if tip.name == row["tip"])
        tip_text.append(tree_axis.text(
            maximum_x + maximum_x * 0.03, y[node],
            _wrapped_display_label(row["display_label"], profile), fontsize=8,
            va="center", ha="left", color="#111111",
            fontweight="bold" if row["role"] == "OUTGROUP" else "normal",
        ))
    tree_axis.set_xlim(0, maximum_x * (2.65 if profile == "SINGLE_COLUMN" else 2.25))
    tree_axis.set_ylim(-0.8, len(rows) - 0.2)
    tree_axis.invert_yaxis(); tree_axis.axis("off")
    tree_axis.set_title("Tree" if profile == "SINGLE_COLUMN" else "Recorded phylogeny", fontsize=9)
    if perfect_support_count:
        tree_axis.text(0.02, -0.09, "● = 100/100 support", transform=tree_axis.transAxes,
                       fontsize=8, ha="left", va="top", clip_on=False)

    value_groups = defaultdict(list)
    for row in rows:
        for (channel, feature), cell in zip(columns, row["cells"]):
            if cell["state"] == "OBSERVED":
                value_groups[(channel, feature)].append({"category": feature, "value": cell["value"]})
    scale = {}
    for key, values in value_groups.items():
        scale[key] = plan_heatmap_scale(values, value_field="value", category_field="category", lower_quantile=0.0, upper_quantile=1.0)
    for row_index, row in enumerate(rows):
        for column_index, ((channel, feature), cell) in enumerate(zip(columns, row["cells"])):
            color = "#E6E6E6"
            alpha = 1.0
            if cell["state"] == "OBSERVED":
                bounds = scale[(channel, feature)]
                low, high = bounds["normalization_minimum"], bounds["normalization_maximum"]
                alpha = 0.30 + 0.70 * min(1.0, max(0.0, (cell["value"] - low) / (high - low)))
                color = TRACK_COLORS[channel]
            track_axis.add_patch(Rectangle((column_index, row_index - 0.42), 0.92, 0.84,
                                           facecolor=color, edgecolor="#FFFFFF", alpha=alpha))
            if cell["state"] != "OBSERVED":
                track_axis.text(column_index + 0.46, row_index, "·", ha="center", va="center", fontsize=8)
    track_axis.set_xlim(0, max(1, len(columns))); track_axis.set_ylim(-0.8, len(rows) - 0.2)
    track_axis.invert_yaxis(); track_axis.set_yticks([])
    track_axis.set_xticks([index + 0.46 for index in range(len(columns))])
    track_axis.set_xticklabels([f"{channel}\n{feature}" for channel, feature in columns], rotation=90, fontsize=8)
    track_axis.set_title("Tracks" if profile == "SINGLE_COLUMN" else "Separate annotation tracks", fontsize=9)
    for spine in track_axis.spines.values(): spine.set_visible(False)
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    visible_track_ticks = [
        item for item in track_axis.get_xticklabels()
        if item.get_visible() and item.get_text().strip()
    ]
    if visible_track_ticks:
        lowest_tick_y = min(
            item.get_window_extent(renderer=renderer).y0 for item in visible_track_ticks
        )
        if lowest_tick_y < 6.0:
            bottom_margin += (6.0 - lowest_tick_y) / fig.bbox.height
            if bottom_margin >= 0.80:
                raise ValueError("annotation track labels leave insufficient data height")
            fig.subplots_adjust(bottom=bottom_margin)
            fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    boxes = []
    for index, item in enumerate(tip_text):
        box = item.get_window_extent(renderer=renderer)
        boxes.append({"id": f"tip-{index}", "group": "tip-labels", "x0": box.x0, "y0": box.y0, "x1": box.x1, "y1": box.y1})
    for index, item in enumerate(support_text):
        box = item.get_window_extent(renderer=renderer)
        boxes.append({"id": f"support-{index}", "group": "support-labels", "x0": box.x0, "y0": box.y0, "x1": box.x1, "y1": box.y1})
    layout = validate_layout_rectangles(boxes, canvas_width_px=fig.bbox.width, canvas_height_px=fig.bbox.height)
    tick_boxes = []
    for index, item in enumerate(visible_track_ticks):
        box = item.get_window_extent(renderer=renderer)
        tick_boxes.append({
            "id": f"tracks-x-tick-{index}", "axis_id": "tracks",
            "x0": box.x0, "y0": box.y0, "x1": box.x1, "y1": box.y1,
        })
    data_box = track_axis.get_window_extent(renderer=renderer)
    layout["tick_label_data_clearance"] = validate_tick_label_data_clearance(
        tick_boxes,
        [{
            "id": "tracks-data-rectangle", "axis_id": "tracks",
            "x0": data_box.x0, "y0": data_box.y0,
            "x1": data_box.x1, "y1": data_box.y1,
        }],
        canvas_width_px=fig.bbox.width,
        canvas_height_px=fig.bbox.height,
    )
    layout["bottom_margin_fraction"] = round(bottom_margin, 6)
    stem = f"tree_bgc_overlay_{profile.casefold()}"
    svg, png = stage / f"{stem}.svg", stage / f"{stem}.png"
    fig.savefig(svg, metadata={"Date": None, "Creator": "Sapote-Mamey Tree Figure Factory"})
    fig.savefig(png, dpi=300, metadata={"Software": "Sapote-Mamey Tree Figure Factory"})
    plt.close(fig)
    return [svg, png], {
        "profile": profile, "geometry_mode": geometry_mode, "layout": layout,
        "svg": validate_publication_artwork(svg, profile=profile),
        "png": validate_publication_artwork(png, profile=profile),
    }


def _write_tsv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


GROUP_ROLE_ORDER = ("STUDY", "REFERENCE", "OUTGROUP", "EXTERNAL_BENCHMARK")


def group_denominators(rows: list[dict[str, Any]]) -> str:
    """Per-ROLE plotted-row denominators for the caption's `group_denominators` field.

    v9.7.412 (Razzle Dazzle Rose): the previous text listed every tip as `ROLE(rows=1; strain=X)` —
    a literal `rows=1` per tip is a tip list, not a denominator (the count was 1 by construction and
    never informative), and it bloated the caption with one entry per strain. A group denominator is
    the number of plotted rows per role. Format keeps `rows=<int>` (what `figure_policy` validates:
    the string must carry `rows=` and a digit) and still enumerates every strain per group, so nothing
    downstream loses the per-row information. Roles appear in canonical order, then any other role
    alphabetically; deterministic for identical input.
    """
    by_role: dict[str, list[str]] = {}
    for row in rows:
        by_role.setdefault(str(row["role"]), []).append(str(row["strain"]))
    ordered = [r for r in GROUP_ROLE_ORDER if r in by_role] + sorted(r for r in by_role if r not in GROUP_ROLE_ORDER)
    return "; ".join(f"{role}(rows={len(by_role[role])}; strains={','.join(by_role[role])})" for role in ordered)


def build_publication(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    channel = str(config.get("tree_channel", ""))
    if channel not in TREE_CHANNELS:
        raise ValueError(f"tree_channel must be one of {sorted(TREE_CHANNELS)}")
    if config.get("annotation_scope") != "STRAIN_AGGREGATE_ONLY":
        raise ValueError("annotation_scope must be STRAIN_AGGREGATE_ONLY")
    root_path = Path(config["external_data_root"]).expanduser().resolve()
    bindings = _bind_inputs(config, root_path)
    tree = parse_newick(bindings["tree"]["path"].read_text(encoding="utf-8"))
    included, omitted, crosswalk = _validate_join(tree, bindings)
    included_strains = {crosswalk[row["newick_label"]]["strain"] for row in included}
    annotations, columns = _load_annotations(bindings["annotation_matrix"]["path"], included_strains)
    if not columns:
        raise ValueError("annotation matrix has no tracks")
    rows = assemble_overlay(tip_order(tree), crosswalk, annotations, columns)
    methods = dict(config.get("methods", {}))
    for field in ("tool", "model", "seed", "outgroup", "support", "source_release", "software_versions"):
        if not str(methods.get(field, "")).strip():
            raise ValueError(f"methods.{field} is required")
    _verify_method_receipts(bindings, channel, methods)

    output = Path(config["output_dir"])
    if not output.is_absolute(): output = (config_path.parent / output).resolve()
    if output.exists(): raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".tree-figure-factory.", dir=output.parent))
    try:
        graphics, profiles = [], []
        for profile in ("SINGLE_COLUMN", "DOUBLE_COLUMN"):
            created, receipt = _render(tree, rows, columns, stage, profile)
            graphics.extend(created); profiles.append(receipt)
        plot_rows = []
        for index, row in enumerate(rows):
            flat = {f"{channel}::{feature}": (cell["value"] if cell["state"] == "OBSERVED" else cell["state"])
                    for (channel, feature), cell in zip(columns, row["cells"])}
            plot_rows.append({"tip_order_index": index, "newick_label": row["tip"], "strain": row["strain"],
                              "display_label": row["display_label"], "role": row["role"], "genus": row["genus"], **flat})
        plot_data = stage / "tree_bgc_overlay_plotdata.tsv"
        _write_tsv(plot_data, list(plot_rows[0]), plot_rows)
        omitted_rows = [{**row, "strain": crosswalk[row["newick_label"]]["strain"],
                         "display_label": crosswalk[row["newick_label"]]["display_label"]} for row in omitted]
        omitted_path = stage / "tree_bgc_overlay_omitted_tips.tsv"
        _write_tsv(omitted_path, ["newick_label", "state", "reason", "strain", "display_label"], omitted_rows)
        source_bindings = "; ".join(
            f"{role}:{item['logical_locator']}; sha256={item['sha256']}; bytes={item['bytes']}"
            for role, item in sorted(bindings.items())
        )
        group_text = group_denominators(rows)
        caption = {
            "caption_schema_version": CAPTION_METHOD_SCHEMA,
            "figure_question": str(config.get("figure_question", "")).strip(),
            "source": "existing sealed phylogeny workflow outputs plus adapter-owned annotation matrix",
            "source_bindings": source_bindings,
            "source_release": methods["source_release"],
            "software_versions": methods["software_versions"],
            "unit_of_analysis": "one explicitly crosswalked included tree tip and separate strain-level annotation tracks",
            "inclusion_exclusion_roles": f"included tips={len(included)}; omitted tips={len(omitted)}; one explicit outgroup",
            "denominator": f"{len(included)} included tree tips",
            "group_denominators": group_text,
            "typed_missingness": f"plotted_rows={len(rows)}; typed_rows={len(annotations)}; rows_missing_state_key=0",
            "benchmark_sensitivity": (
                f"available={sum(row['role'] == 'EXTERNAL_BENCHMARK' for row in crosswalk.values())}; "
                f"selected={sum(row['role'] == 'EXTERNAL_BENCHMARK' for row in rows)}; "
                "default_off=true; external benchmarks remain excluded from study n and percentages"
            ),
            "transformation": "recorded topology and branch lengths; per-track value scaling without cross-channel pooling",
            "visual_grammar": "Tree lines encode the supplied topology and branch lengths; labels use the explicit crosswalk; colored cells encode separate annotation channels; dots encode typed non-observation.",
            "statistics_uncertainty": "support labels are reproduced from the supplied tree; no new statistic is computed",
            "comparison_group": f"explicit final roster for {channel}",
            "genus_control": "NOT_APPLICABLE; topology is not pooled into a genus comparison",
            "contradictions": "MLSA/core-genome topology equivalence is not asserted; separate channels are not reconciled by this renderer",
            "interpretation_boundary": CLAIM_CEILING,
        }
        validate_caption_methods(caption, nonstandard_visual=True)
        caption_path = stage / "tree_bgc_overlay_caption_methods.json"
        caption_path.write_text(json.dumps(caption, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        owner_notes = stage / "tree_bgc_overlay_owner_notes.json"
        owner_notes.write_text(json.dumps({"owner_notes": config.get("owner_notes", []),
                                           "scientific_caption_inclusion": False,
                                           "plotted_canvas_inclusion": False}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        artifacts = graphics + [plot_data, omitted_path, caption_path, owner_notes]
        receipt = {
            "schema_version": SCHEMA_VERSION, "status": "PASS_ENGINEERING_CANDIDATE",
            "tree_channel": channel, "annotation_scope": "STRAIN_AGGREGATE_ONLY",
            "methods": methods, "inputs": [{"role": role, "logical_locator": item["logical_locator"],
                "sha256": item["sha256"], "bytes": item["bytes"]} for role, item in sorted(bindings.items())],
            "tip_counts": {"included": len(included), "omitted": len(omitted)},
            "explicit_omission_receipt": omitted_path.name, "profiles": profiles,
            "channel_separation": sorted({channel for channel, _ in columns}),
            "claim_ceiling": CLAIM_CEILING,
            "outputs": [{"logical_locator": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in artifacts],
            "authority_state": "ENGINEERING_CANDIDATE_ONLY_NOT_SCIENTIFIC_ACCEPTANCE_NOT_INTEGRATED_NOT_RELEASED",
        }
        (stage / "tree_bgc_overlay_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        stage.replace(output)
        return receipt
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="hash-bound phylogeny Figure Factory consumer")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = build_publication(args.config)
    except Exception as exc:
        sys.stderr.write(f"tree_bgc_overlay: REFUSED: {type(exc).__name__}: {exc}\n")
        return 2
    sys.stdout.write(json.dumps(receipt, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
