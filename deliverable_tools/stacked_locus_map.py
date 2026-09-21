#!/usr/bin/env python3
"""Render a portable, claim-safe stacked locus map from a JSON specification.

The input uses track-relative base-pair coordinates.  Tracks therefore share a
true base-pair scale while an author can reverse a comparator before writing the
specification.  Optional ribbons are descriptive homology links supplied by the
caller; this renderer does not infer homology or biological function.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path


ROLE_COLORS = {
    "core_biosynthesis": "#1F6F8B",
    "tailoring_redox": "#D58B32",
    "transport": "#5B8E55",
    "regulation_resistance": "#8A5C8E",
    "other": "#A8B2B7",
}
ROLE_LABELS = {
    "core_biosynthesis": "Core biosynthesis",
    "tailoring_redox": "Tailoring / redox",
    "transport": "Transport",
    "regulation_resistance": "Regulation / resistance",
    "other": "Other / unresolved",
}
CLAIM_CEILING = (
    "Gene order, submitted role labels, and submitted homology ribbons are comparative context only. "
    "They do not establish pathway completeness, exact product identity, expression, production, "
    "activity, mechanism, novelty, or host adaptation."
)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def complete_identity(value):
    parts = [part.strip() for part in str(value).split("/")]
    if len(parts) != 4 or any(not part for part in parts):
        raise ValueError("LOCUS_MAP_GATE: query identity must be strain / full node-or-contig / region / BGC alias")
    if parts[3] == "UNRESOLVED_BGC_ALIAS":
        raise ValueError("LOCUS_MAP_GATE: unresolved BGC aliases are prohibited")
    return " / ".join(parts)


def validate_spec(spec):
    if spec.get("schema_version") != "1.0":
        raise ValueError("LOCUS_MAP_GATE: schema_version must be 1.0")
    spec["query_identity"] = complete_identity(spec.get("query_identity", ""))
    tracks = spec.get("tracks")
    if not isinstance(tracks, list) or len(tracks) < 2:
        raise ValueError("LOCUS_MAP_GATE: at least two tracks are required")
    track_ids = set()
    gene_index = {}
    for track in tracks:
        track_id = str(track.get("track_id", "")).strip()
        if not track_id or track_id in track_ids:
            raise ValueError("LOCUS_MAP_GATE: track IDs must be nonblank and unique")
        track_ids.add(track_id)
        genes = track.get("genes")
        if not isinstance(genes, list) or not genes:
            raise ValueError(f"LOCUS_MAP_GATE: track {track_id} has no genes")
        last_start = -1
        for gene in genes:
            gene_id = str(gene.get("id", "")).strip()
            symbol = str(gene.get("symbol", "")).strip()
            if not gene_id or not symbol or (track_id, gene_id) in gene_index:
                raise ValueError(f"LOCUS_MAP_GATE: track {track_id} has blank or duplicate gene identity")
            try:
                start, end, strand = int(gene["start"]), int(gene["end"]), int(gene["strand"])
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"LOCUS_MAP_GATE: gene {gene_id} has invalid coordinates") from None
            if start < 0 or end <= start or strand not in (-1, 1) or start < last_start:
                raise ValueError(f"LOCUS_MAP_GATE: gene {gene_id} has invalid or unsorted coordinates")
            if gene.get("role", "other") not in ROLE_COLORS:
                raise ValueError(f"LOCUS_MAP_GATE: gene {gene_id} has an unknown role")
            last_start = start
            gene_index[(track_id, gene_id)] = gene
    for ribbon in spec.get("ribbons", []):
        upper = (str(ribbon.get("upper_track", "")), str(ribbon.get("upper_gene", "")))
        lower = (str(ribbon.get("lower_track", "")), str(ribbon.get("lower_gene", "")))
        if upper not in gene_index or lower not in gene_index:
            raise ValueError("LOCUS_MAP_GATE: ribbon refers to an unknown track or gene")
        try:
            identity = float(ribbon["identity_pct"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("LOCUS_MAP_GATE: ribbon identity_pct is required") from None
        if not 0 <= identity <= 100:
            raise ValueError("LOCUS_MAP_GATE: ribbon identity_pct must be between 0 and 100")
    return spec


def label_lanes(genes, maximum_lanes):
    """Assign non-overlapping text intervals to lanes or fail closed."""
    lane_ends = [-math.inf] * maximum_lanes
    assigned = {}
    for gene in genes:
        midpoint = (gene["start"] + gene["end"]) / 2000.0
        half_width = max(0.34, len(gene["symbol"]) * 0.043)
        left, right = midpoint - half_width, midpoint + half_width
        for lane, occupied_until in enumerate(lane_ends):
            if left > occupied_until + 0.08:
                assigned[gene["id"]] = lane
                lane_ends[lane] = right
                break
        else:
            raise ValueError(
                f"LOCUS_MAP_LABEL_COLLISION: {gene['id']} cannot be placed without overlap in {maximum_lanes} lanes"
            )
    return assigned


def arrow_polygon(gene, y, height=0.30):
    start, end, strand = gene["start"] / 1000.0, gene["end"] / 1000.0, gene["strand"]
    width = end - start
    head = min(0.24, max(0.08, width * 0.32))
    low, high = y - height / 2, y + height / 2
    if strand == 1:
        return [(start, low), (end - head, low), (end, y), (end - head, high), (start, high)]
    return [(end, low), (start + head, low), (start, y), (start + head, high), (end, high)]


def render(spec_path, out_prefix, receipt_path=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mamey.render_safe import safe_savefig_dpi as _safe_dpi
    from matplotlib.patches import Patch, PathPatch, Polygon
    from matplotlib.path import Path as MplPath

    source = Path(spec_path)
    spec = validate_spec(json.loads(source.read_text(encoding="utf-8")))
    out_prefix = Path(out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    max_lanes = int(spec.get("max_label_lanes", 4))
    if max_lanes < 1 or max_lanes > 6:
        raise ValueError("LOCUS_MAP_GATE: max_label_lanes must be between 1 and 6")
    lanes = {track["track_id"]: label_lanes(track["genes"], max_lanes) for track in spec["tracks"]}
    x_max = max(gene["end"] for track in spec["tracks"] for gene in track["genes"]) / 1000.0
    y_by_track = {track["track_id"]: (len(spec["tracks"]) - 1 - index) * 2.15 for index, track in enumerate(spec["tracks"])}
    gene_by_key = {(track["track_id"], gene["id"]): gene for track in spec["tracks"] for gene in track["genes"]}

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5})
    fig_height = max(5.8, 2.1 + 2.15 * len(spec["tracks"]))
    fig, ax = plt.subplots(figsize=(14.2, fig_height), constrained_layout=False)
    fig.subplots_adjust(left=.075, right=.985, top=.79, bottom=.20)

    for ribbon in spec.get("ribbons", []):
        upper_gene = gene_by_key[(ribbon["upper_track"], ribbon["upper_gene"])]
        lower_gene = gene_by_key[(ribbon["lower_track"], ribbon["lower_gene"])]
        x1 = (upper_gene["start"] + upper_gene["end"]) / 2000.0
        x2 = (lower_gene["start"] + lower_gene["end"]) / 2000.0
        y1 = y_by_track[ribbon["upper_track"]] - .20
        y2 = y_by_track[ribbon["lower_track"]] + .20
        mid = (y1 + y2) / 2
        path = MplPath([(x1, y1), (x1, mid), (x2, mid), (x2, y2)], [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4])
        alpha = .07 + .0022 * float(ribbon["identity_pct"])
        ax.add_patch(PathPatch(path, facecolor="none", edgecolor="#6C7E86", linewidth=.6 + float(ribbon["identity_pct"]) / 75, alpha=min(.34, alpha), zorder=0))

    used_roles = []
    for track in spec["tracks"]:
        y = y_by_track[track["track_id"]]
        ax.plot([0, x_max], [y, y], color="#587178", linewidth=.75, zorder=1)
        for gene in track["genes"]:
            role = gene.get("role", "other")
            if role not in used_roles:
                used_roles.append(role)
            ax.add_patch(Polygon(arrow_polygon(gene, y), closed=True, facecolor=ROLE_COLORS[role], edgecolor="white", linewidth=.55, zorder=3))
            midpoint = (gene["start"] + gene["end"]) / 2000.0
            lane = lanes[track["track_id"]][gene["id"]]
            ax.text(midpoint, y + .28 + lane * .23, gene["symbol"], ha="center", va="bottom", fontsize=7.1, color="#17373C", zorder=4)
        left_label = track.get("boundary_left", "left boundary")
        right_label = track.get("boundary_right", "right boundary")
        track_end = max(gene["end"] for gene in track["genes"]) / 1000.0
        for x, label, align in ((0, left_label, "left"), (track_end, right_label, "right")):
            ax.plot([x, x], [y - .34, y + .54 + max_lanes * .09], color="#334E55", linestyle=(0, (2, 2)), linewidth=.85, zorder=2)
            ax.text(x, y - .43, label, ha=align, va="top", fontsize=6.5, color="#52666C")
        ax.text(-.20, y + .68 + max_lanes * .04, track["label"], ha="left", va="bottom", fontsize=9.2, fontweight="bold", color="#17373C")

    scale_length = 2 if x_max >= 5 else 1
    scale_y = -.75
    scale_x = max(.35, x_max - scale_length - .35)
    ax.plot([scale_x, scale_x + scale_length], [scale_y, scale_y], color="#17373C", linewidth=1.8)
    ax.plot([scale_x, scale_x], [scale_y - .06, scale_y + .06], color="#17373C", linewidth=1.2)
    ax.plot([scale_x + scale_length, scale_x + scale_length], [scale_y - .06, scale_y + .06], color="#17373C", linewidth=1.2)
    ax.text(scale_x + scale_length / 2, scale_y - .10, f"{scale_length} kb", ha="center", va="top", fontsize=7.5)

    ax.set_xlim(-.35, x_max + .35)
    ax.set_ylim(-1.12, max(y_by_track.values()) + 1.42)
    ax.set_yticks([])
    ax.set_xlabel("Track-relative genomic position (kb; shared true scale)", labelpad=8)
    ax.spines[["left", "right", "top"]].set_visible(False)
    ax.spines["bottom"].set_color("#87979B")
    ax.tick_params(axis="x", colors="#52666C")
    ax.grid(axis="x", color="#DCE4E5", linewidth=.45, zorder=-2)

    title = spec.get("title", "Stacked locus comparison")
    fig.suptitle(title, x=.075, y=.965, ha="left", fontsize=15, fontweight="bold", color="#17373C")
    fig.text(.075, .915, spec["query_identity"], ha="left", fontsize=10.5, fontweight="bold", color="#0B7A75")
    subtitle = spec.get("subtitle", "")
    if subtitle:
        fig.text(.075, .875, subtitle, ha="left", fontsize=8.5, color="#52666C")
    handles = [Patch(facecolor=ROLE_COLORS[role], edgecolor="none", label=ROLE_LABELS[role]) for role in ROLE_COLORS if role in used_roles]
    if spec.get("ribbons"):
        handles.append(Patch(facecolor="#6C7E86", alpha=.25, edgecolor="none", label="Submitted protein identity ribbon"))
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(.985, .845), frameon=False, ncol=min(3, len(handles)), fontsize=7.2, handlelength=1.2, columnspacing=1.1)
    claim = spec.get("claim_ceiling", CLAIM_CEILING)
    fig.text(.075, .055, claim, ha="left", va="bottom", fontsize=7.4, color="#6A4B1F", wrap=True)

    outputs = {}
    for suffix in ("svg", "png", "pdf"):
        path = Path(str(out_prefix) + f".{suffix}")
        fig.savefig(path, dpi=_safe_dpi(fig, 360) if suffix == "png" else None, bbox_inches="tight")
        outputs[suffix] = {"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
    plt.close(fig)
    receipt = {
        "status": "PASS",
        "schema_version": spec["schema_version"],
        "query_identity": spec["query_identity"],
        "track_count": len(spec["tracks"]),
        "gene_count": sum(len(track["genes"]) for track in spec["tracks"]),
        "ribbon_count": len(spec.get("ribbons", [])),
        "label_collision_gate": "PASS_NO_OVERLAP_WITHIN_ALLOCATED_LANES",
        "source_spec": {"file": source.name, "sha256": sha256(source), "bytes": source.stat().st_size},
        "outputs": outputs,
        "claim_ceiling": claim,
    }
    if receipt_path:
        receipt_file = Path(receipt_path)
        receipt_file.parent.mkdir(parents=True, exist_ok=True)
        receipt_file.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out-prefix", required=True)
    parser.add_argument("--receipt")
    args = parser.parse_args(argv)
    try:
        receipt = render(args.spec, args.out_prefix, args.receipt)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error))
    sys.stdout.write(json.dumps(receipt, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
