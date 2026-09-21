#!/usr/bin/env python3
"""Compare exact GCF members at gene-order and antiSMASH-domain level.

The tool consumes a bound membership table and region GBKs. Protein relationships
are deterministic reciprocal best 5-mer Jaccard matches, not BLAST identities.
It emits evidence tables, a source receipt, and an optional static figure.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey._gbk_shim import parse_genbank_text
from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from mamey.render_safe import safe_savefig_dpi as _safe_dpi

CLAIM_CEILING = (
    "Gene order, antiSMASH domain calls, protein 5-mer similarity, and BiG-SCAPE distance "
    "are comparative context only. They do not establish pathway completeness, product identity, "
    "expression, production, activity, mechanism, novelty, or host adaptation."
)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tsv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write_tsv(path, rows, fields):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = _SafeDictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def complete_identity(row):
    values = [row.get("strain", ""), row.get("full_node_or_contig", ""), row.get("region", ""), row.get("bgc_alias", "")]
    if any(not value or value == "UNRESOLVED_BGC_ALIAS" for value in values):
        raise ValueError("GCF_CONTEXT_GATE: every selected locus requires strain / full node-or-contig / region / BGC alias")
    return " / ".join(values)


def safe_gbk_name(row):
    return "_".join([row["strain"], row["full_node_or_contig"], row["region"], row["bgc_alias"]]) + ".gbk"


def first(values, default=""):
    return values[0] if values else default


def domain_name(feature):
    return first(feature.qualifiers.get("aSDomain")) or first(feature.qualifiers.get("label")).split("_")[-1]


def parse_locus(row, gbk_dir=None):
    source = Path(gbk_dir) / safe_gbk_name(row) if gbk_dir else Path(row["source_path"])
    if not source.is_file():
        raise ValueError(f"GCF_CONTEXT_GATE: missing GBK for {complete_identity(row)}")
    records = parse_genbank_text(source.read_text(encoding="utf-8"))
    if len(records) != 1:
        raise ValueError(f"GCF_CONTEXT_GATE: expected one GenBank record for {complete_identity(row)}")
    record = records[0]
    domains_by_tag = {}
    for feature in record.features:
        if feature.type != "aSDomain":
            continue
        tag = first(feature.qualifiers.get("locus_tag"))
        name = domain_name(feature)
        if tag and name:
            domains_by_tag.setdefault(tag, []).append((feature.location.start, name))
    genes = []
    for feature in record.features:
        if feature.type != "CDS":
            continue
        tag = first(feature.qualifiers.get("locus_tag"))
        translation = first(feature.qualifiers.get("translation"))
        domains = [name for _, name in sorted(domains_by_tag.get(tag, []))]
        functions = feature.qualifiers.get("gene_functions", [])
        gene_kind = first(feature.qualifiers.get("gene_kind"), "unclassified")
        label = " / ".join(domains)
        if not label and functions:
            label = functions[0].split(":", 1)[-1].strip()
        if not label:
            label = "unannotated CDS"
        genes.append({
            "index": len(genes) + 1,
            "start": feature.location.start,
            "end": feature.location.end,
            "strand": feature.location.strand,
            "locus_tag": tag,
            "gene_kind": gene_kind,
            "label": label,
            "domains": domains,
            "translation": translation,
            "translation_sha256": hashlib.sha256(translation.encode()).hexdigest() if translation else "",
        })
    if not genes:
        raise ValueError(f"GCF_CONTEXT_GATE: no CDS features for {complete_identity(row)}")
    core_strands = [gene["strand"] for gene in genes if gene["domains"] or "fatty_acid:" in gene["label"]]
    orientation = Counter(core_strands).most_common(1)[0][0] if core_strands else 1
    ordered = genes if orientation == 1 else list(reversed(genes))
    signature = []
    for gene in ordered:
        signature.extend(gene["domains"])
    return {
        "row": row,
        "identity": complete_identity(row),
        "source": source,
        "source_sha256": sha256(source),
        "source_bytes": source.stat().st_size,
        "record_length": len(record.seq),
        "genes": genes,
        "orientation": orientation,
        "domain_signature": signature,
    }


def kmers(sequence, k=5):
    return {sequence[index:index + k] for index in range(max(0, len(sequence) - k + 1))}


def protein_similarity(left, right):
    if not left or not right:
        return 0.0, 0.0
    left_kmers, right_kmers = kmers(left), kmers(right)
    union = left_kmers | right_kmers
    score = len(left_kmers & right_kmers) / len(union) if union else 0.0
    length_ratio = min(len(left), len(right)) / max(len(left), len(right))
    return score, length_ratio


def reciprocal_best(focal, partner, minimum_score=0.12, minimum_length_ratio=0.65):
    scores = {}
    for f_index, f_gene in enumerate(focal["genes"]):
        for p_index, p_gene in enumerate(partner["genes"]):
            scores[(f_index, p_index)] = protein_similarity(f_gene["translation"], p_gene["translation"])
    best_focal = {
        f_index: max(range(len(partner["genes"])), key=lambda p_index: scores[(f_index, p_index)])
        for f_index in range(len(focal["genes"]))
    }
    best_partner = {
        p_index: max(range(len(focal["genes"])), key=lambda f_index: scores[(f_index, p_index)])
        for p_index in range(len(partner["genes"]))
    }
    matches = []
    for f_index, p_index in best_focal.items():
        score, length_ratio = scores[(f_index, p_index)]
        if best_partner[p_index] == f_index and score >= minimum_score and length_ratio >= minimum_length_ratio:
            matches.append({
                "focal_index": f_index + 1,
                "partner_index": p_index + 1,
                "focal_gene": focal["genes"][f_index],
                "partner_gene": partner["genes"][p_index],
                "protein_5mer_jaccard": score,
                "protein_length_ratio": length_ratio,
            })
    return matches


def lcs_length(values, reverse=False):
    sequence = [-value for value in values] if reverse else values
    tails = []
    import bisect
    for value in sequence:
        place = bisect.bisect_left(tails, value)
        if place == len(tails):
            tails.append(value)
        else:
            tails[place] = value
    return len(tails)


def order_summary(matches):
    positions = [match["partner_index"] for match in sorted(matches, key=lambda item: item["focal_index"])]
    if not positions:
        return "UNRESOLVED", 0.0
    same = lcs_length(positions)
    inverted = lcs_length(positions, reverse=True)
    return ("SAME_ORIENTATION" if same >= inverted else "INVERTED_ORIENTATION", max(same, inverted) / len(positions))


def edge_map(path):
    edges = {}
    for row in read_tsv(path):
        left = row.get("record_a_id") or row.get("source")
        right = row.get("record_b_id") or row.get("target")
        if not left or not right:
            raise ValueError("GCF_CONTEXT_GATE: direct-edge table lacks record identifiers")
        edges[frozenset((left, right))] = float(row["distance"])
    return edges


def build_context(membership_path, direct_edges_path, family_id, focal_strain, out_dir, gbk_dir=None, figure_png=None, figure_pdf=None):
    members = [row for row in read_tsv(membership_path) if str(row["family_id"]) == str(family_id)]
    if len(members) < 2:
        raise ValueError("GCF_CONTEXT_GATE: selected family must contain at least two loci")
    if any(row.get("identity_status") != "COMPLETE" for row in members):
        raise ValueError("GCF_CONTEXT_GATE: selected family contains an incomplete identity")
    loci = [parse_locus(row, gbk_dir) for row in members]
    focal_candidates = [locus for locus in loci if locus["row"]["strain"] == focal_strain]
    if len(focal_candidates) != 1:
        raise ValueError("GCF_CONTEXT_GATE: selected family requires exactly one focal locus")
    focal = focal_candidates[0]
    edges = edge_map(direct_edges_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    gene_rows = []
    for locus in loci:
        for gene in locus["genes"]:
            gene_rows.append({
                "complete_identity": locus["identity"], "gene_index": gene["index"],
                "locus_tag": gene["locus_tag"], "start": gene["start"], "end": gene["end"],
                "strand": gene["strand"], "gene_kind": gene["gene_kind"], "gene_label": gene["label"],
                "antismash_domains": ";".join(gene["domains"]), "translation_sha256": gene["translation_sha256"],
                "source_gbk_sha256": locus["source_sha256"],
            })
    write_tsv(out / "GCF_GENE_DOMAIN_CONTEXT.tsv", gene_rows, list(gene_rows[0]))
    rbh_rows = []
    summary_rows = []
    rbh_by_identity = {}
    for locus in loci:
        matches = [] if locus is focal else reciprocal_best(focal, locus)
        rbh_by_identity[locus["identity"]] = matches
        orientation, collinear_fraction = order_summary(matches)
        scores = [match["protein_5mer_jaccard"] for match in matches]
        for match in matches:
            rbh_rows.append({
                "focal_complete_identity": focal["identity"], "partner_complete_identity": locus["identity"],
                "focal_gene_index": match["focal_index"], "focal_locus_tag": match["focal_gene"]["locus_tag"],
                "partner_gene_index": match["partner_index"], "partner_locus_tag": match["partner_gene"]["locus_tag"],
                "protein_5mer_jaccard": f'{match["protein_5mer_jaccard"]:.6f}',
                "protein_length_ratio": f'{match["protein_length_ratio"]:.6f}',
                "method": "RECIPROCAL_BEST_5MER_JACCARD",
            })
        key = frozenset((focal["row"]["record_id"], locus["row"]["record_id"]))
        summary_rows.append({
            "complete_identity": locus["identity"], "record_id": locus["row"]["record_id"],
            "boundary_state": locus["row"].get("boundary_state", "UNRESOLVED"),
            "cds_count": len(locus["genes"]), "antismash_domain_signature": ">".join(locus["domain_signature"]),
            "direct_bigscape_distance_to_focal": "0.000000" if locus is focal else f'{edges.get(key, math.nan):.6f}',
            "focal_reciprocal_best_gene_pairs": len(matches),
            "median_protein_5mer_jaccard": f"{statistics.median(scores):.6f}" if scores else "",
            "rbh_order_orientation": "FOCAL" if locus is focal else orientation,
            "rbh_collinear_fraction": "" if locus is focal else f"{collinear_fraction:.6f}",
            "source_gbk_sha256": locus["source_sha256"],
        })
    write_tsv(out / "GCF_FOCAL_RECIPROCAL_BEST_GENES.tsv", rbh_rows, list(rbh_rows[0]) if rbh_rows else [
        "focal_complete_identity", "partner_complete_identity", "focal_gene_index", "focal_locus_tag",
        "partner_gene_index", "partner_locus_tag", "protein_5mer_jaccard", "protein_length_ratio", "method",
    ])
    write_tsv(out / "GCF_LOCUS_COMPARISON_SUMMARY.tsv", summary_rows, list(summary_rows[0]))
    receipt = {
        "status": "PASS", "family_id": str(family_id), "focal_complete_identity": focal["identity"],
        "member_count": len(loci), "gene_count": len(gene_rows), "reciprocal_best_pairs": len(rbh_rows),
        "method": "RECIPROCAL_BEST_5MER_JACCARD; minimum score 0.12; minimum length ratio 0.65",
        "claim_ceiling": CLAIM_CEILING,
        "sources": [{
            "complete_identity": locus["identity"], "file": locus["source"].name,
            "sha256": locus["source_sha256"], "bytes": locus["source_bytes"],
        } for locus in loci],
    }
    if figure_png or figure_pdf:
        render_figure(loci, focal, edges, rbh_by_identity, figure_png, figure_pdf, family_id)
        receipt["figure_png_locator"] = Path(figure_png).name if figure_png else None
        receipt["figure_pdf_locator"] = Path(figure_pdf).name if figure_pdf else None
    receipt_path = out / "GCF_CONTEXT_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def render_figure(loci, focal, edges, rbh_by_identity, png_path, pdf_path, family_id):
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrow, Patch

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
    fig = plt.figure(figsize=(15, 10), constrained_layout=False)
    grid = fig.add_gridspec(2, 2, width_ratios=(2.2, 1), height_ratios=(1.55, 1), left=.08, right=.97, top=.91, bottom=.12, hspace=.3, wspace=.25)
    ax_gene = fig.add_subplot(grid[0, :])
    ax_net = fig.add_subplot(grid[1, 0])
    ax_dom = fig.add_subplot(grid[1, 1])
    colors = {"core": "#0B7A75", "additional": "#D6A72C", "regulatory": "#8B5A3C", "other": "#8FA4A6"}
    for row_index, locus in enumerate(loci):
        y = len(loci) - 1 - row_index
        anchor = next((gene for gene in locus["genes"] if "TIGR00747" in gene["domains"] or "fabH" in gene["label"]), locus["genes"][len(locus["genes"]) // 2])
        anchor_mid = (anchor["start"] + anchor["end"]) / 2
        sign = locus["orientation"]
        for gene in locus["genes"]:
            start = sign * (gene["start"] - anchor_mid) / 1000
            end = sign * (gene["end"] - anchor_mid) / 1000
            left, right = sorted((start, end))
            width = right - left
            category = "core" if gene["domains"] or "fabH" in gene["label"] else "regulatory" if gene["gene_kind"] == "regulatory" else "additional" if "biosynthetic" in gene["gene_kind"] else "other"
            direction = 1 if gene["strand"] * sign == 1 else -1
            x = left if direction == 1 else right
            ax_gene.add_patch(FancyArrow(x, y, direction * width, 0, width=.32, head_width=.5, head_length=min(.22, width * .3), length_includes_head=True, color=colors[category], linewidth=.4))
            if gene["domains"] or "fabH" in gene["label"]:
                ax_gene.text((left + right) / 2, y + .34, "/".join(gene["domains"]) or "fabH", ha="center", va="bottom", fontsize=6, rotation=28)
        ax_gene.text(-12.4, y, locus["identity"], ha="right", va="center", fontsize=7)
    ax_gene.axvline(0, color="#153B4A", linewidth=.8, linestyle="--")
    ax_gene.set_xlim(-12, 12); ax_gene.set_ylim(-.8, len(loci) - .2); ax_gene.set_yticks([])
    ax_gene.set_xlabel("Distance from normalized fabH/TIGR00747 anchor (kb; core transcription orientation normalized)")
    ax_gene.set_title("A. Gene order and antiSMASH core-domain context", loc="left", fontweight="bold")
    ax_gene.spines[["top", "right", "left"]].set_visible(False)
    ax_gene.legend(handles=[Patch(color=value, label=key.capitalize()) for key, value in colors.items()], ncol=4, frameon=False, loc="upper right")

    positions = {}
    for index, locus in enumerate(loci):
        angle = 2 * math.pi * index / len(loci) + math.pi / 4
        positions[locus["row"]["record_id"]] = (-.85 + .62 * math.cos(angle), .62 * math.sin(angle))
    for pair, distance in edges.items():
        if not pair.issubset(positions):
            continue
        left_id, right_id = tuple(pair)
        x1, y1 = positions[left_id]; x2, y2 = positions[right_id]
        ax_net.plot([x1, x2], [y1, y2], color="#A4B1B3", linewidth=max(.7, 4 * (1 - distance)), zorder=1)
        ax_net.text((x1 + x2) / 2, (y1 + y2) / 2, f"{distance:.3f}", fontsize=6, color="#4F5D61")
    node_colors = ["#D6A72C", "#0B7A75", "#3E6E9E", "#8B5A3C"]
    # AQUARIUS .436: the fixed 4-color list IndexErrors at >=5 members; a bare index % len
    # would instead collapse distinct loci onto one node color, making panel B's color key
    # non-unique. Keep the house 4 for <=4 loci; sample tab20 for larger families so every
    # locus keeps a unique, stable color.
    node_palette = node_colors if len(loci) <= len(node_colors) else [plt.cm.tab20(i / max(1, len(loci) - 1)) for i in range(len(loci))]
    for index, locus in enumerate(loci):
        x, y = positions[locus["row"]["record_id"]]
        color = node_palette[index]
        ax_net.scatter([x], [y], s=180 if locus is focal else 120, color=color, edgecolor="white", linewidth=1.5, zorder=2)
        legend_y = .83 - index * .48
        ax_net.scatter([.25], [legend_y], s=55, color=color, edgecolor="white", linewidth=.8)
        wrapped_identity = locus["identity"].replace(" / region", "\n/ region", 1)
        ax_net.text(.34, legend_y, f"L{index + 1} · {wrapped_identity}", ha="left", va="center", fontsize=5.8, linespacing=1.05)
    ax_net.set_xlim(-1.65, 2.45); ax_net.set_ylim(-1.12, 1.12); ax_net.axis("off")
    ax_net.set_title("B. GCF network (edge labels are direct BiG-SCAPE distances)", loc="left", fontweight="bold")

    domain_order = []
    for locus in loci:
        for domain in locus["domain_signature"]:
            if domain not in domain_order:
                domain_order.append(domain)
    matrix = [[locus["domain_signature"].count(domain) for domain in domain_order] for locus in loci]
    ax_dom.imshow(matrix, cmap="YlGnBu", vmin=0, vmax=max((max(row) for row in matrix if row), default=0) or 1, aspect="auto")
    ax_dom.set_xticks(range(len(domain_order)), domain_order, rotation=45, ha="right", fontsize=7)
    ax_dom.set_yticks(range(len(loci)), [f"L{index + 1}" for index in range(len(loci))], fontsize=7)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            ax_dom.text(j, i, str(value), ha="center", va="center", fontsize=7, color="#153B4A")
    ax_dom.set_title("C. antiSMASH domain counts", loc="left", fontweight="bold")

    fig.suptitle(f"GCF {family_id}: exact-locus comparison centered on {focal['identity']}", fontsize=14, fontweight="bold", color="#153B4A")
    fig.text(.08, .045, CLAIM_CEILING, ha="left", va="bottom", fontsize=7.5, color="#5E4420", wrap=True)
    for path in [png_path, pdf_path]:
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(path, dpi=_safe_dpi(fig, 300) if str(path).lower().endswith(".png") else None, bbox_inches="tight")
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--membership", required=True)
    parser.add_argument("--direct-edges", required=True)
    parser.add_argument("--family-id", required=True)
    parser.add_argument("--focal-strain", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--gbk-dir")
    parser.add_argument("--figure-png")
    parser.add_argument("--figure-pdf")
    args = parser.parse_args(argv)
    try:
        receipt = build_context(args.membership, args.direct_edges, args.family_id, args.focal_strain, args.out_dir, args.gbk_dir, args.figure_png, args.figure_pdf)
    except ValueError as error:
        raise SystemExit(str(error))
    sys.stdout.write(json.dumps(receipt, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
