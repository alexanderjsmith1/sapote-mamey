#!/usr/bin/env python3
"""bgc_gene_map.py — whole-BGC gene map: EVERY gene in EVERY BGC, not just the assembly line.

WHY THIS EXISTS. `assembly_line_widget.py` / `assembly_line_pdf.py` show NRPS/PKS assembly-line
domain architecture — which by construction only covers BGCs that HAVE assembly-line domains
(assembly-line domains occur in only a subset of regions). Every RiPP, terpene, saccharide, siderophore,
ectoine and "other" region is invisible in that view. Those are exactly the regions the house
gene-level rule says must not be dismissed by their product label.

This renders the complementary view: each BGC as its genes in true genomic order and scale, drawn
as strand-aware arrows, coloured by antiSMASH's own `/gene_kind` role call, with `sec_met_domains`
markers annotated on the genes that carry them. It covers 100% of the regions in a package,
whatever their class.

SINGLE SOURCE OF TRUTH — reads the package's own `<strain>_gene_context.jsonl` (per-CDS records:
locus_tag, contig, start, end, strand, aa_length, product, gene_kind, gene_functions,
sec_met_domains) and reuses `load_inventory()` from `assembly_line_widget.py` for the products /
boundary header, so class labels and boundary flags match the sibling views exactly.

CLAIM SAFETY (printed on every page): `gene_kind` and `sec_met_domains` are antiSMASH's own
rule-based calls, not verified function; a domain marker is a class-level capacity hypothesis, not
a product, an activity, or a structure. Regions on a contig edge are TRUNCATED — absent genes are
an assembly artefact, not biological absence. Judgment deferred.

Usage:
  bgc_gene_map.py --strain AS-XXX --runs-root <dir> --out <dir> [--per-page 6] [--pdf|--html]
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import importlib.util
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "assembly_line_widget_src_gm", os.path.join(_HERE, "assembly_line_widget.py"))
_alw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_alw)
load_inventory = _alw.load_inventory
find_pkg = _alw.find_pkg

#: antiSMASH's own /gene_kind vocabulary -> (label, colour). Deliberately mirrors the qualifier
#: rather than inventing a taxonomy: the map shows what antiSMASH called, not what we think.
KINDS = [
    ("biosynthetic",            "Core biosynthetic",       "#4f8ef7"),
    ("biosynthetic-additional", "Additional biosynthetic", "#5cae7a"),
    ("transport",               "Transport",               "#e0913a"),
    ("regulatory",              "Regulatory",              "#c05fd6"),
    ("resistance",              "Resistance",              "#d9534f"),
    ("other",                   "Other / unclassified",    "#9aa0ad"),
]
KIND_COLOR = {k: c for k, _, c in KINDS}
UNCALLED = "#c8ced8"   # gene_kind absent entirely — shown, never silently dropped

CLAIM_SAFETY = (
    "CLAIM SAFETY — Gene roles are antiSMASH's own rule-based /gene_kind calls and sec_met_domains "
    "are HMM hypotheses; neither is verified function, and neither asserts a product, an activity "
    "or a structure. Genes with no /gene_kind call are drawn uncoloured rather than dropped. A "
    "region on a contig edge is TRUNCATED — genes absent from the picture are an assembly artefact, "
    "not biological absence. Class-level capacity only; judgment deferred — Mamey extracts, Sapote "
    "judges."
)

MAX_GENES_LABELLED = 14   # beyond this, arrows are drawn but only domain-bearing genes get labels


def load_gene_map(pkg: str, strain: str) -> dict[str, list[dict]]:
    """bgc_id -> [CDS dicts] straight from the package's gene_context.jsonl.

    The first line is a file header record (schema_version / n_cds / claim_safety) and is skipped;
    every later line is {"bgc_id": ..., "cds": [...]}.
    """
    path = os.path.join(pkg, f"{strain}_gene_context.jsonl")
    out: dict[str, list[dict]] = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            bgc, cds = rec.get("bgc_id"), rec.get("cds")
            if bgc and isinstance(cds, list):
                out[bgc] = cds
    return out


def build_payload(strain: str, pkg: str) -> dict:
    """{strain, bgcs:[{bgc_id, products, boundary, n_genes, span_kb, genes:[...]}]} — ALL regions."""
    gene_map = load_gene_map(pkg, strain)
    inv = load_inventory(os.path.join(pkg, f"{strain}_2_inventory.csv"))
    bgcs = []
    for bgc in sorted(gene_map, key=lambda b: int("".join(ch for ch in b if ch.isdigit()) or 0)):
        cds = [c for c in gene_map[bgc] if c.get("start") is not None and c.get("end") is not None]
        if not cds:
            continue
        cds.sort(key=lambda c: c["start"])
        meta = inv.get(bgc, {})
        lo = min(c["start"] for c in cds)
        hi = max(c["end"] for c in cds)
        bgcs.append({
            "bgc_id": bgc,
            "products": meta.get("products", ""),
            "boundary": meta.get("boundary", ""),
            "n_genes": len(cds),
            "lo": lo, "hi": hi,
            "span_kb": round((hi - lo) / 1000.0, 1),
            "genes": cds,
        })
    return {"strain": strain, "bgcs": bgcs}


def _arrow(ax, x0, x1, y, h, color, strand):
    """A strand-aware gene arrow in axes data coords (x in 0..1 of the region span)."""
    from matplotlib.patches import FancyArrow
    width = x1 - x0
    head = min(width * 0.42, 0.012)          # never let the head swallow a short gene
    if strand is not None and int(strand) < 0:
        ax.add_patch(FancyArrow(x1, y + h / 2, -(width - head), 0, width=h,
                                head_width=h, head_length=head, length_includes_head=True,
                                facecolor=color, edgecolor="none"))
    else:
        ax.add_patch(FancyArrow(x0, y + h / 2, width - head, 0, width=h,
                                head_width=h, head_length=head, length_includes_head=True,
                                facecolor=color, edgecolor="none"))


def _draw_bgc(ax, b) -> None:
    ax.set_xlim(-0.01, 1.01); ax.set_ylim(0, 1)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#d8dce3")

    products = b["products"] or "(class n/a)"
    if len(products) > 52:
        products = products[:51] + "…"
    ax.text(0, 1.135, f"{b['bgc_id']} — {products}", transform=ax.transAxes,
            fontsize=7.2, fontweight="bold", color="#1b2129", va="bottom")
    ax.text(0, 1.030, f"{b['n_genes']} genes · {b['span_kb']} kb · boundary: {b['boundary'] or '?'}",
            transform=ax.transAxes, fontsize=5.6, color="#5a6672", va="bottom")
    if b["boundary"] and any(k in str(b["boundary"]).lower() for k in ("edge", "truncat", "full-contig")):
        ax.text(1, 1.030, "TRUNCATED (edge / full-contig)", transform=ax.transAxes, fontsize=5.4,
                color="#b0761f", va="bottom", ha="right")

    span = max(b["hi"] - b["lo"], 1)
    ax.plot([0, 1], [0.5, 0.5], color="#dfe4ea", linewidth=0.8, zorder=0)  # the locus backbone
    label_all = b["n_genes"] <= MAX_GENES_LABELLED

    # Labels are STAGGERED across three tiers and dropped when even the emptiest tier would
    # collide. A first version wrote every label at one height and dense loci (BGC003: 22 genes)
    # rendered an unreadable pile of overlapping rotated text — the same collision class this
    # lane has been fixing all session. Dropping a label is honest (the arrow and its domain
    # marker are still drawn); overlapping text that cannot be read is not.
    tiers_y = (0.70, 0.80, 0.90)
    tier_last_x = [-9.0, -9.0, -9.0]
    MIN_GAP = 0.085                       # axes-fraction separation needed between two labels

    for c in b["genes"]:
        x0 = (c["start"] - b["lo"]) / span
        x1 = (c["end"] - b["lo"]) / span
        kind = (c.get("gene_kind") or "").strip()
        color = KIND_COLOR.get(kind, UNCALLED if not kind else "#9aa0ad")
        _arrow(ax, x0, max(x1, x0 + 0.002), 0.44, 0.12, color, c.get("strand"))
        doms = [d for d in (c.get("sec_met_domains") or []) if d]
        mid = (x0 + x1) / 2
        if doms:                                        # mark the genes carrying HMM domain hits
            ax.plot([mid], [0.665], marker="v", markersize=2.6, color="#3a4450", zorder=3)
        if not (label_all or doms):
            continue
        ti = max(range(len(tiers_y)), key=lambda i: mid - tier_last_x[i])
        if mid - tier_last_x[ti] < MIN_GAP:
            continue                                    # no room on any tier — arrow still drawn
        tier_last_x[ti] = mid
        txt = doms[0] if doms else (c.get("locus_tag") or "")
        ax.text(mid, tiers_y[ti], str(txt)[:16], fontsize=4.3, color="#3a4450",
                ha="center", va="bottom", rotation=0)
        ax.plot([mid, mid], [0.60, tiers_y[ti] - 0.008], color="#c8ced8",
                linewidth=0.35, zorder=1)              # leader line to the gene it names
    ax.text(0, 0.20, f"{b['lo']:,} bp", fontsize=4.6, color="#8b93a0", ha="left", va="top")
    ax.text(1, 0.20, f"{b['hi']:,} bp", fontsize=4.6, color="#8b93a0", ha="right", va="top")
    if not label_all:
        ax.text(0.5, 0.14, "labels shown for domain-bearing genes only", fontsize=4.4,
                color="#8b93a0", ha="center", va="top")


def build_pdf(strain: str, runs_root: str, outdir: str, per_page: int = 6) -> str | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import Patch

    pkg = find_pkg(runs_root, strain)
    if not pkg:
        emit(f"  [SKIP] {strain}: no package found under {runs_root}")
        return None
    payload = build_payload(strain, pkg)
    bgcs = payload["bgcs"]
    if not bgcs:
        emit(f"  [SKIP] {strain}: gene_context.jsonl absent or carried no positioned CDS")
        return None

    rows, cols = (3, 2) if per_page == 6 else (2, 2)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{strain}_bgc_gene_maps.pdf")
    pages = (len(bgcs) + per_page - 1) // per_page
    total_genes = sum(b["n_genes"] for b in bgcs)

    with PdfPages(out) as pdf:
        for p in range(pages):
            chunk = bgcs[p * per_page:(p + 1) * per_page]
            fig, axes = plt.subplots(rows, cols, figsize=(11.69, 8.27))
            axes = axes.ravel()
            for ax in axes[len(chunk):]:
                ax.axis("off")
            for ax, b in zip(axes, chunk):
                _draw_bgc(ax, b)
            fig.suptitle(
                f"{strain} — whole-BGC gene maps · page {p+1} of {pages} "
                f"(ALL {len(bgcs)} regions · {total_genes} genes · every class, not only NRPS/PKS)",
                fontsize=10, fontweight="bold", x=0.02, ha="left", y=0.985)
            handles = [Patch(facecolor=col, label=lab) for _, lab, col in KINDS]
            handles.append(Patch(facecolor=UNCALLED, label="No /gene_kind call"))
            fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.02, 0.055),
                       ncol=4, fontsize=5.6, frameon=False)
            fig.text(0.02, 0.012, CLAIM_SAFETY, fontsize=4.9, color="#5a6672", wrap=True)
            fig.subplots_adjust(left=0.035, right=0.985, top=0.90, bottom=0.115,
                                hspace=0.85, wspace=0.10)
            pdf.savefig(fig)
            plt.close(fig)

    emit(f"  [OK]   {strain}: {len(bgcs)} region(s) / {total_genes} genes over {pages} page(s) -> {out}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strain")
    ap.add_argument("--strains", nargs="+")
    ap.add_argument("--runs-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-page", type=int, default=6, choices=(4, 6))
    a = ap.parse_args()
    strains = a.strains or ([a.strain] if a.strain else None)
    if not strains:
        ap.error("give --strain or --strains")
    n = 0
    for s in strains:
        if build_pdf(s, a.runs_root, a.out, a.per_page):
            n += 1
    emit(f"bgc-gene-map: {n}/{len(strains)} strain PDF(s) -> {a.out}",
         "  antiSMASH /gene_kind + sec_met_domains are rule-based calls, not verified function; "
         "judgment deferred.", sep="\n")
    return 0 if n else 1


if __name__ == "__main__":
    raise SystemExit(main())
