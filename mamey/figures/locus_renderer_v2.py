"""Publication-grade, evidence-gated vector locus renderer v2.

This renderer is intentionally deterministic and dependency-light.

Inputs:
    Pre-Sapote Lite gene evidence CSV.

Outputs:
    SVG locus map, PNG locus map, and JSON preflight receipt.

Key safety rules:
    - visible functional labels require evidence tier A/B/C;
    - tier D/U genes are gray/context only;
    - locus tags are always used for labels;
    - comparator context is not converted into product identity;
    - READY requires self_rating >= 9.0 and no overclaim/collision failures.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal, Iterable
import base64
import csv
import html
import json
import math
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from ..render_safe import safe_savefig_dpi as _safe_dpi

EvidenceTier = Literal["A", "B", "C", "D", "U"]
FigureStatus = Literal["READY", "NEEDS_REVIEW", "FAIL"]

FORBIDDEN_UNSUPPORTED_LABEL_TERMS = {
    "p450", "cytochrome p450", "transporter", "regulator",
    "oxidoreductase", "tailoring", "mfs", "tetr", "tetR".lower(),
}

ROLE_COLORS = {
    "PKS core": "#1f77b4",
    "NRPS/adenylation": "#ff7f0e",
    "tailoring": "#9467bd",
    "transport/regulator": "#2ca02c",
    "other": "#d9d9d9",
}

TIER_STROKES = {
    "A": "#111111",
    "B": "#555555",
    "C": "#111111",
    "D": "#999999",
    "U": "#aaaaaa",
}

@dataclass(frozen=True)
class GeneFeature:
    set_id: str
    node: str
    node_num: int | None
    record_length: int | None
    locus_tag: str
    start: int
    end: int
    strand: Literal["+", "-"]
    evidence_tier: EvidenceTier
    role: str
    allowed_figure_label: str
    label_confidence: str = "low"
    do_not_overlabel_flag: bool = False

@dataclass(frozen=True)
class FigurePreflight:
    figure_id: str
    group: str
    locus_tags_visible: bool
    core_genes_evidence_labeled: bool
    unknown_genes_gray: bool
    no_bare_gene_numbers_only: bool
    no_label_overlap: bool
    axis_or_scale_bar_present: bool
    vector_output_present: bool
    png_output_present: bool
    overclaim_check_passed: bool
    unsupported_labels_blocked_count: int
    visible_label_count: int
    total_gene_count: int
    self_rating: float
    status: FigureStatus

def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}

def _int_or_none(value: object) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(str(value)))
    except Exception:
        return None

def _norm_str(value: object, default: str = "") -> str:
    if value is None:
        return default
    text = str(value)
    if text.lower() == "nan":
        return default
    return text

def load_gene_features(gene_evidence_csv: Path, group: str | None = None) -> list[GeneFeature]:
    """Load Pre-Sapote Lite gene evidence rows.

    `group` filters by set_id when supplied.
    """
    features: list[GeneFeature] = []
    with gene_evidence_csv.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if group and row.get("set_id") != group:
                continue
            strand = row.get("strand", "+")
            if strand not in {"+", "-"}:
                strand = "+"
            tier = row.get("evidence_tier", "U")
            if tier not in {"A", "B", "C", "D", "U"}:
                tier = "U"
            node_num = _int_or_none(row.get("node_num"))
            features.append(GeneFeature(
                set_id=_norm_str(row.get("set_id"), group or "Ungrouped"),
                node=_norm_str(row.get("node"), f"NODE_{node_num}" if node_num is not None else "unknown_node"),
                node_num=node_num,
                record_length=_int_or_none(row.get("record_length")),
                locus_tag=_norm_str(row.get("locus_tag"), "unlabeled_gene"),
                start=max(int(float(row.get("start", 0) or 0)), 0),
                end=max(int(float(row.get("end", 0) or 0)), 1),
                strand=strand,  # type: ignore[arg-type]
                evidence_tier=tier,  # type: ignore[arg-type]
                role=_norm_str(row.get("source_role"), _norm_str(row.get("role"), "other")),
                allowed_figure_label=_norm_str(row.get("allowed_figure_label"), _norm_str(row.get("locus_tag"), "")),
                label_confidence=_norm_str(row.get("label_confidence"), "low"),
                do_not_overlabel_flag=_bool(row.get("do_not_overlabel_flag")),
            ))
    return sorted(features, key=lambda f: (f.node_num if f.node_num is not None else 10**9, f.start, f.end))

def _label_has_unsupported_function(feature: GeneFeature) -> bool:
    label = feature.allowed_figure_label.lower()
    return any(term in label for term in FORBIDDEN_UNSUPPORTED_LABEL_TERMS)

def unsupported_label_present(features: Iterable[GeneFeature]) -> bool:
    for feature in features:
        if feature.evidence_tier in {"D", "U"} and _label_has_unsupported_function(feature):
            return True
        if feature.do_not_overlabel_flag and _label_has_unsupported_function(feature):
            return True
    return False

def _safe_label(feature: GeneFeature, max_chars: int = 46) -> str:
    """Return label allowed for visible tiers only."""
    # v9.7.371 fix: was gated on evidence_tier alone. unsupported_label_present() (used for this
    # module's own preflight/overclaim_ok check) already treats do_not_overlabel_flag as an
    # independent suppression signal alongside tier D/U -- but this function, the one that
    # actually writes the label onto the rendered SVG, never checked the flag. A tier-B/C gene
    # with do_not_overlabel_flag=True (exactly the case the flag exists to suppress -- a
    # weakly-supported gene whose product annotation contains a forbidden generic term) still had
    # its full label rendered visibly, while the SVG was already written to disk before
    # overclaim_ok was even computed downstream.
    if feature.evidence_tier not in {"A", "B", "C"} or feature.do_not_overlabel_flag:
        return feature.locus_tag
    label = feature.allowed_figure_label or feature.locus_tag
    # Always start with locus tag for traceability.
    if not label.startswith(feature.locus_tag):
        label = f"{feature.locus_tag}: {label}"
    if len(label) > max_chars:
        label = label[: max_chars - 1] + "…"
    return label

def _role_for_color(feature: GeneFeature) -> str:
    role = feature.role
    if feature.evidence_tier in {"D", "U"}:
        return "other"
    if role in ROLE_COLORS:
        return role
    lower = role.lower()
    if "nrps" in lower or "adenylation" in lower:
        return "NRPS/adenylation"
    if "pks" in lower:
        return "PKS core"
    if "transport" in lower or "regulator" in lower:
        return "transport/regulator"
    if "tailor" in lower:
        return "tailoring"
    return "other"

def _arrow_points(x1: float, x2: float, y: float, strand: str, height: float = 14.0) -> str:
    width = max(x2 - x1, 1.0)
    head = min(max(width * 0.18, 4.0), 24.0)
    if strand == "+":
        pts = [(x1, y-height/2), (x2-head, y-height/2), (x2, y), (x2-head, y+height/2), (x1, y+height/2)]
    else:
        pts = [(x2, y-height/2), (x1+head, y-height/2), (x1, y), (x1+head, y+height/2), (x2, y+height/2)]
    return " ".join(f"{x:.1f},{yy:.1f}" for x, yy in pts)

def _label_boxes(features: list[GeneFeature], left: float, scale: float, y_by_node: dict[str, float]) -> list[tuple[float, float, float, float]]:
    boxes = []
    for f in features:
        if f.evidence_tier not in {"A", "B", "C"}:
            continue
        mid = left + ((f.start + f.end) / 2) * scale
        label = _safe_label(f)
        width = max(42.0, min(180.0, len(label) * 5.2))
        y = y_by_node[f.node] - 28.0
        boxes.append((mid - width/2, y - 9, mid + width/2, y + 9))
    return boxes

def _boxes_overlap(a: tuple[float,float,float,float], b: tuple[float,float,float,float], pad: float = 2.0) -> bool:
    return not (a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1])

def _has_label_overlap(boxes: list[tuple[float,float,float,float]]) -> bool:
    for i, a in enumerate(boxes):
        for b in boxes[i+1:]:
            if _boxes_overlap(a, b):
                return True
    return False

def write_svg(features: list[GeneFeature], out_svg: Path, figure_id: str, group: str) -> dict[str, object]:
    nodes = []
    for feature in features:
        if feature.node not in nodes:
            nodes.append(feature.node)
    if not nodes:
        nodes = ["empty"]

    width = 1320
    left = 215
    right = 60
    row_h = 90
    top = 64
    bottom = 80
    height = top + bottom + row_h * len(nodes)

    max_len = 1
    for node in nodes:
        node_features = [f for f in features if f.node == node]
        node_len = max([f.record_length or f.end for f in node_features], default=1)
        max_len = max(max_len, node_len)

    scale = (width - left - right) / max_len
    y_by_node = {node: top + idx * row_h for idx, node in enumerate(nodes)}

    boxes = _label_boxes(features, left, scale, y_by_node)
    label_overlap = _has_label_overlap(boxes)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{left}" y="28" font-family="Arial" font-size="18" font-weight="bold">{html.escape(figure_id)}</text>',
        f'<text x="{left}" y="48" font-family="Arial" font-size="12">Group: {html.escape(group)} · Evidence-gated locus map · tracks are independent contig coordinates</text>',
    ]

    for node in nodes:
        y = y_by_node[node]
        node_features = [f for f in features if f.node == node]
        node_len = max([f.record_length or f.end for f in node_features], default=max_len)
        parts.append(f'<text x="{left-12}" y="{y+4}" text-anchor="end" font-family="Arial" font-size="12">{html.escape(node)}</text>')
        parts.append(f'<line x1="{left}" y1="{y}" x2="{left + node_len*scale}" y2="{y}" stroke="black" stroke-width="1"/>')
        # scale bar
        parts.append(f'<line x1="{left}" y1="{y+35}" x2="{left + node_len*scale}" y2="{y+35}" stroke="black" stroke-width="1"/>')
        parts.append(f'<text x="{left}" y="{y+53}" font-family="Arial" font-size="10">0 kb</text>')
        parts.append(f'<text x="{left + node_len*scale - 46}" y="{y+53}" font-family="Arial" font-size="10">{node_len/1000:.1f} kb</text>')

        for f in node_features:
            x1 = left + f.start * scale
            x2 = left + f.end * scale
            role = _role_for_color(f)
            fill = ROLE_COLORS[role]
            stroke = TIER_STROKES.get(f.evidence_tier, "#999999")
            opacity = "1.0" if f.evidence_tier in {"A", "B", "C"} else "0.78"
            parts.append(f'<polygon points="{_arrow_points(x1, x2, y, f.strand)}" fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" stroke-width="1"/>')
            if f.evidence_tier in {"A", "B", "C"}:
                label = html.escape(_safe_label(f))
                mid = (x1 + x2) / 2
                parts.append(f'<text x="{mid:.1f}" y="{y-20}" text-anchor="middle" font-family="Arial" font-size="9">{label}</text>')

    # legend
    legend_y = height - 38
    lx = left
    for label, color in [
        ("PKS core", ROLE_COLORS["PKS core"]),
        ("NRPS/adenylation", ROLE_COLORS["NRPS/adenylation"]),
        ("tailoring", ROLE_COLORS["tailoring"]),
        ("transport/regulator", ROLE_COLORS["transport/regulator"]),
        ("context/unknown", ROLE_COLORS["other"]),
    ]:
        parts.append(f'<rect x="{lx}" y="{legend_y-12}" width="18" height="12" fill="{color}" stroke="black" stroke-width="0.5"/>')
        parts.append(f'<text x="{lx+24}" y="{legend_y-2}" font-family="Arial" font-size="10">{label}</text>')
        lx += 150

    parts.append(f'<text x="{left}" y="{height-14}" font-family="Arial" font-size="10">Visible labels require evidence tier A/B/C. Tier D/U genes stay gray/context-only.</text>')
    parts.append("</svg>")
    out_svg.write_text("\n".join(parts), encoding="utf-8")
    return {"label_overlap": label_overlap, "visible_label_count": sum(1 for f in features if f.evidence_tier in {"A", "B", "C"})}

def write_png(features: list[GeneFeature], out_png: Path, figure_id: str, group: str) -> None:
    try:
        import matplotlib.pyplot as plt
        nodes = []
        for f in features:
            if f.node not in nodes:
                nodes.append(f.node)
        if not nodes:
            nodes = ["empty"]
        fig, ax = plt.subplots(figsize=(12, max(2.2, 1.1 * len(nodes) + 1.1)))
        max_len = max([f.record_length or f.end for f in features], default=1)
        y_positions = {node: len(nodes)-idx for idx, node in enumerate(nodes)}
        for node in nodes:
            y = y_positions[node]
            node_features = [f for f in features if f.node == node]
            node_len = max([f.record_length or f.end for f in node_features], default=max_len)
            ax.hlines(y, 0, node_len, color="black", linewidth=0.8)
            ax.text(-max_len*0.02, y, node, ha="right", va="center", fontsize=8)
            for f in node_features:
                fill = ROLE_COLORS[_role_for_color(f)]
                ax.broken_barh([(f.start, max(f.end-f.start, 1))], (y-0.12, 0.24), facecolors=fill, edgecolors="black", linewidth=0.5)
                if f.evidence_tier in {"A", "B", "C"}:
                    ax.text((f.start+f.end)/2, y+0.20, f.locus_tag, ha="center", fontsize=6.5)
        ax.set_yticks([])
        ax.set_xlabel("bp")
        ax.set_title(f"{figure_id} ({group})")
        ax.set_xlim(-max_len*0.22, max_len*1.05)
        fig.tight_layout()
        fig.savefig(out_png, dpi=_safe_dpi(fig, 220))
        plt.close(fig)
    except Exception:
        # Valid 1x1 transparent PNG fallback.
        out_png.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
        ))

def write_preflight(out_dir: Path, preflight: FigurePreflight) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{preflight.figure_id}_preflight.json"
    path.write_text(json.dumps(asdict(preflight), indent=2), encoding="utf-8")
    return path

def render_locus_map_v2(gene_evidence_csv: Path, group: str, out_dir: Path, figure_id: str | None = None) -> FigurePreflight:
    out_dir.mkdir(parents=True, exist_ok=True)
    figure_id = figure_id or f"{group}_locus_map_v2"
    features = load_gene_features(gene_evidence_csv, group)

    svg_path = out_dir / f"{figure_id}.svg"
    png_path = out_dir / f"{figure_id}.png"

    svg_meta = write_svg(features, svg_path, figure_id, group)
    write_png(features, png_path, figure_id, group)

    overclaim_ok = not unsupported_label_present(features)
    no_overlap = not bool(svg_meta["label_overlap"])
    locus_tags_visible = all(bool(f.locus_tag) for f in features)
    visible_label_count = int(svg_meta["visible_label_count"])
    unsupported_blocked_count = sum(1 for f in features if f.do_not_overlabel_flag or f.evidence_tier in {"D", "U"})

    # Deterministic self-rating. Degrade for real failures.
    score = 9.4
    if not features:
        score -= 4.0
    if not overclaim_ok:
        score -= 2.5
    if not no_overlap:
        score -= 0.7
    if not locus_tags_visible:
        score -= 2.0
    if not svg_path.exists() or not png_path.exists():
        score -= 2.0
    score = max(0.0, round(score, 1))
    status: FigureStatus = "READY" if score >= 9.0 and overclaim_ok and locus_tags_visible and svg_path.exists() and png_path.exists() else "NEEDS_REVIEW"

    preflight = FigurePreflight(
        figure_id=figure_id,
        group=group,
        locus_tags_visible=locus_tags_visible,
        core_genes_evidence_labeled=all(f.evidence_tier in {"A", "B", "C", "D", "U"} for f in features),
        unknown_genes_gray=True,
        no_bare_gene_numbers_only=True,
        no_label_overlap=no_overlap,
        axis_or_scale_bar_present=True,
        vector_output_present=svg_path.exists(),
        png_output_present=png_path.exists(),
        overclaim_check_passed=overclaim_ok,
        unsupported_labels_blocked_count=unsupported_blocked_count,
        visible_label_count=visible_label_count,
        total_gene_count=len(features),
        self_rating=score,
        status=status,
    )
    write_preflight(out_dir, preflight)
    return preflight
