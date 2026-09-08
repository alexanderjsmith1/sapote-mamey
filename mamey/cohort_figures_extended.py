#!/usr/bin/env python3
"""Extended cross-strain / per-BGC figure suite (auto-emit companion to cohort_figures.generate).

Generates 11 figures from sealed gold packages: census, PKS length bars, size-vs-richness, enriched
locus map, archetype, KCB novelty, CCTT triggers, boundary profile, domain co-occurrence, resistance
map, TTA/bldA profile. Reads only <strain>_2_inventory.csv + <strain>_gene_by_gene_all_bgcs.csv.

Regenerates six exploratory cross-strain / per-BGC figures from sealed gold packages.
Nothing here touches the engine; it reads only per-strain package artifacts:
  - <strain>/package/<strain>_2_inventory.csv          (per-BGC: Length_kb, Products, Arch, KCB_*)
  - <strain>/package/<strain>_gene_by_gene_all_bgcs.csv (per-gene: function, sec_met_domains,
        cctt_triggers, resistance_tier, bldA_tta_tier, boundary_flag, cds_start/end, strand, length_bp)
Optionally reads a cohort census CSV (cohort-figures F01 sidecar) for the census heatmap; if absent
it recomputes the five census metrics from the packages.

Usage:
    python3 AS_cohort_figure_prototypes.py --packages-root /path/with/<strain>/package/ \
            [--strains AS-XXX,AS-XXX,AS-XXX,AS-XXX] [--out ./proto_figs] \
            [--census-csv F01_census_zscore_heatmap_data.csv] [--locus-strain AS-XXX --locus-bgc BGC003]

Figures written to --out:
    fig1_census_notier.png     per-strain gene/domain census heatmap, tier moved to caption
    fig2_pks_bars.png          PKS BGCs as length bars, stacked by gene-type bp
    fig3_size_vs_rich.png      BGC length vs functional-gene richness scatter
    fig4_enriched_locus.png    enriched locus map (gene arrows + domain track + resistance/trigger badges)
    fig5_archetype.png         BGC architecture-archetype composition per strain (from Products)
    fig6_kcb_novelty.png       KCB novelty landscape (BGCs ranked by similarity; dark = candidate-novel)
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import argparse, csv, glob, os
from collections import Counter
import numpy as np
# W2-H3/v9.7.352: figure deps are optional ([all] extra). Guard the import so this module — reached
# via cohort_class_heatmap — stays importable on a core-only install instead of crashing.
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    import matplotlib.lines as mlines
    _HAVE_MPL = True
except ImportError:  # degrade gracefully; render entrypoints check _HAVE_MPL before drawing
    _HAVE_MPL = False

# Per-strain assembly tiers for the census caption. Cohort-specific data is not shipped
# in the code tier; loaded from OFFICIAL_DATA/cohort_assembly_tiers.json when present,
# else an empty map (the caption falls back to '?' via TIER.get(c, '?')).
from .exclusions import official_data_json as _official_data_json
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi
TIER = dict(_official_data_json("cohort_assembly_tiers.json", {}))

FUNC_COL = {"core biosynthetic": "#b2182b", "biosynthetic context": "#aebfd4",
            "tailoring / modification": "#2d898b", "chain release / TE": "#6a51a3",
            "maturation / proteolysis": "#e08214"}
INTERGENIC = "#eeeeee"
STRAIN_COL = ["#7b3294", "#e08214", "#b2182b", "#d6a000", "#2166ac", "#1b7837"]
PUBLICATION_RASTER_DPI = 300


def _sidecar_csv(png_path, header, rows):
    """Write a tidy, figure-ready `<stem>_data.csv` beside the PNG (v9.7.409).

    One observation per row, snake_case headers, the exact values the figure plots — so every
    figure in this suite is R/ggplot2- and seaborn-reproducible without re-deriving it from the
    packages. Written atomically (`.tmp` -> os.replace) like the PNGs. Never raises: a sidecar
    failure must not abort a figure that already rendered."""
    csv_path = os.path.splitext(str(png_path))[0] + "_data.csv"
    try:
        tmp = csv_path + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            w = _SafeWriter(fh)
            w.writerow(header)
            for r in rows:
                w.writerow(r)
        os.replace(tmp, csv_path)
    except OSError as e:  # pragma: no cover - disk/permission only; keep the figure
        emit(f"  (sidecar write failed for {os.path.basename(csv_path)}: {e})")
    return csv_path


def _strain_bar_width(strains):
    """Publication width that keeps dense cohort labels individually legible."""
    return max(9.0, 3.5 + 0.34 * len(strains))


def _finish_strain_axis(ax, strains):
    """Apply the shared dense-cohort tick-label guard without dropping strains."""
    ax.set_xticks(range(len(strains)))
    ax.set_xticklabels(
        strains, rotation=65, ha="right", rotation_mode="anchor", fontsize=8
    )
    ax.tick_params(axis="x", pad=2)


def pkg_dir(root, sid):
    hits = glob.glob(os.path.join(root, sid, "package")) or glob.glob(os.path.join(root, "*", sid, "package"))
    if not hits:
        raise SystemExit(f"no package dir for {sid} under {root}")
    return hits[0]


def load_inventory(root, sid):
    p = os.path.join(pkg_dir(root, sid), f"{sid}_2_inventory.csv")
    return list(csv.DictReader(open(p, encoding="utf-8")))


def load_genes(root, sid):
    p = os.path.join(pkg_dir(root, sid), f"{sid}_gene_by_gene_all_bgcs.csv")
    byb = {}
    for r in csv.DictReader(open(p, encoding="utf-8")):
        byb.setdefault(r["bgc_id"], []).append(r)
    return byb


def fcol(f):
    for k, v in FUNC_COL.items():
        if k in (f or ""):
            return v
    return "#cfcfcf"


# ---------------- FIG 1: census heatmap, tier strip removed ----------------
def fig_census(root, strains, out, census_csv=None):
    metrics = ["domain hits", "distinct Pfam", "core domains", "active-site calls", "RiPP calls"]
    if census_csv and os.path.exists(census_csv):
        rows = list(csv.reader(open(census_csv)))
        cols = rows[0][1:]
        metrics = [r[0] for r in rows[1:]]
        raw = np.array([[float(x) for x in r[1:]] for r in rows[1:]])
    else:  # recompute from packages
        cols = strains
        raw = np.zeros((len(metrics), len(strains)))
        for j, sid in enumerate(strains):
            genes = load_genes(root, sid)
            allg = [g for gs in genes.values() for g in gs]
            dom_hits = sum(len(g.get("sec_met_domains", "").split(";")) for g in allg if g.get("sec_met_domains", "").strip())
            pf = set(d.strip() for g in allg for d in g.get("sec_met_domains", "").split(";") if d.strip())
            core = sum(1 for g in allg if "core" in g.get("gene_function_inference", ""))
            asite = sum(1 for g in allg if g.get("cctt_triggers", "").strip() or "KS" in g.get("sec_met_domains", ""))
            ripp = sum(1 for gs in genes.values() for g in gs if "lanthi" in g.get("cctt_triggers", "").lower() or "LAN" in g.get("cctt_triggers", ""))
            raw[:, j] = [dom_hits, len(pf), core, asite, ripp]
    z = (raw - raw.mean(1, keepdims=True)) / (raw.std(1, keepdims=True) + 1e-9)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    im = ax.imshow(z, cmap="RdBu_r", vmin=-2, vmax=2, aspect="auto")
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, fontsize=10)
    ax.set_yticks(range(len(metrics))); ax.set_yticklabels(metrics, fontsize=10)
    for i in range(len(metrics)):
        for j in range(len(cols)):
            ax.text(j, i, f"{int(raw[i, j])}", ha="center", va="center",
                    color="white" if abs(z[i, j]) > 1.1 else "black", fontsize=10)
    ax.set_title("Per-strain gene/domain census\n(cells = raw counts; colour = z-score within metric)",
                 fontweight="bold", fontsize=12)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04); cb.set_label("z-score (within metric)")
    cap = "Assembly tier — " + " · ".join(f"{c}: {TIER.get(c, '?')}" for c in cols)
    fig.text(0.5, -0.02, cap, ha="center", fontsize=8.5, style="italic", color="#444")
    _png = os.path.join(out, "fig1_census_notier.png")
    _sidecar_csv(_png, ["metric", "strain", "raw_count", "zscore"],
                 [[metrics[i], cols[j], int(raw[i, j]), round(float(z[i, j]), 4)]
                  for i in range(len(metrics)) for j in range(len(cols))])
    plt.tight_layout(); plt.savefig(_png, dpi=_safe_dpi(plt.gcf(), PUBLICATION_RASTER_DPI), bbox_inches="tight", facecolor="white"); plt.close()


# ---------------- FIG 2: PKS BGC length bars ----------------
def fig_pks_bars(root, strains, out):
    gtypes = list(FUNC_COL)
    fig, axes = plt.subplots(1, len(strains), figsize=(4.3 * len(strains), 5.6), sharey=True)
    axes = np.atleast_1d(axes)
    _rows = []
    for ax, sid in zip(axes, strains):
        inv = {r["BGC_ID"]: r for r in load_inventory(root, sid)}
        genes = load_genes(root, sid)
        pks = [(b, float(r["Length_kb"] or 0)) for b, r in inv.items()
               if any(k in r["Products"] for k in ("PKS", "transAT")) and float(r["Length_kb"] or 0) > 0]
        pks.sort(key=lambda x: -x[1])
        for xi, (b, L) in enumerate(pks):
            comp = {g: 0.0 for g in gtypes}
            for r in genes.get(b, []):
                gt = r.get("gene_function_inference", "").strip()
                if gt in comp:
                    comp[gt] += float(r.get("length_bp") or 0) / 1000.0
            bottom = 0
            for gt in gtypes:
                if comp[gt] > 0:
                    ax.bar(xi, comp[gt], bottom=bottom, color=FUNC_COL[gt], width=0.85, edgecolor="white", linewidth=0.3); bottom += comp[gt]
            inter = max(0, L - sum(comp.values()))
            for gt in gtypes:
                _rows.append([sid, b, round(L, 3), gt, round(comp[gt], 3)])
            _rows.append([sid, b, round(L, 3), "intergenic / non-CDS", round(inter, 3)])
            if inter > 0:
                ax.bar(xi, inter, bottom=bottom, color=INTERGENIC, width=0.85, edgecolor="white", linewidth=0.3)
        ax.set_title(f"{sid}  ({len(pks)} PKS BGCs)", fontsize=11, fontweight="bold")
        ax.set_xticks(range(len(pks))); ax.set_xticklabels([b.replace("BGC", "") for b, _ in pks], fontsize=6, rotation=90)
        ax.set_xlabel("PKS BGC (sorted by length)", fontsize=9)
    axes[0].set_ylabel("BGC length (kb), segmented by gene bp", fontsize=10)
    handles = [Patch(color=FUNC_COL[g], label=g) for g in gtypes] + [Patch(color=INTERGENIC, label="intergenic / non-CDS")]
    fig.legend(handles=handles, loc="upper center", ncol=6, fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("PKS BGC length and gene-type architecture across strains", fontweight="bold", fontsize=13, y=1.08)
    _png = os.path.join(out, "fig2_pks_bars.png")
    _sidecar_csv(_png, ["strain", "bgc_id", "bgc_length_kb", "gene_type", "segment_kb"], _rows)
    plt.tight_layout(); plt.savefig(_png, dpi=_safe_dpi(plt.gcf(), PUBLICATION_RASTER_DPI), bbox_inches="tight", facecolor="white"); plt.close()


# ---------------- FIG 3: size vs functional-gene richness ----------------
def fig_size_vs_rich(root, strains, out):
    fig, ax = plt.subplots(figsize=(9, 6))
    func = ("core biosynthetic", "tailoring / modification", "chain release / TE", "maturation / proteolysis")
    _rows = []
    for i, sid in enumerate(strains):
        inv = {r["BGC_ID"]: r for r in load_inventory(root, sid)}
        genes = load_genes(root, sid)
        xs, ys = [], []
        for b, r in inv.items():
            L = float(r["Length_kb"] or 0)
            if L <= 0:
                continue
            rich = sum(1 for g in genes.get(b, []) if g.get("gene_function_inference", "") in func)
            xs.append(L)
            ys.append(rich)
            _rows.append([sid, b, round(L, 3), rich])
        ax.scatter(xs, ys, s=34, alpha=0.7, color=STRAIN_COL[i % len(STRAIN_COL)],
                   edgecolor="white", linewidth=0.4, label=f"{sid} (n={len(xs)})")
    ax.set_xlabel("BGC length (kb)", fontsize=11)
    ax.set_ylabel("Functional gene richness (core+tailoring+release+maturation)", fontsize=10)
    ax.set_title("BGC size vs functional-gene richness across strains", fontweight="bold", fontsize=12)
    ax.legend(fontsize=9, frameon=False); ax.grid(alpha=0.25)
    _png = os.path.join(out, "fig3_size_vs_rich.png")
    _sidecar_csv(_png, ["strain", "bgc_id", "bgc_length_kb", "functional_gene_richness"], _rows)
    plt.tight_layout(); plt.savefig(_png, dpi=_safe_dpi(plt.gcf(), PUBLICATION_RASTER_DPI), bbox_inches="tight", facecolor="white"); plt.close()


# ---------------- FIG 4: enriched locus map ----------------
def fig_enriched_locus(root, sid, bgc, out):
    genes = load_genes(root, sid).get(bgc, [])
    inv = {r["BGC_ID"]: r for r in load_inventory(root, sid)}.get(bgc, {})
    if not genes:
        emit(f"  (no genes for {sid} {bgc}; skipping locus map)"); return
    xs = [int(g["cds_start"]) for g in genes] + [int(g["cds_end"]) for g in genes]
    x0 = min(xs); span = (max(xs) - x0) / 1000.0
    fig, ax = plt.subplots(figsize=(15, 5.0))
    max_dom_lines = 0
    for g in genes:
        s = (int(g["cds_start"]) - x0) / 1000.0; e = (int(g["cds_end"]) - x0) / 1000.0
        w = e - s; strand = 1 if g["strand"] in ("+", "1") else -1
        core = "core" in g.get("gene_function_inference", "")
        ax.arrow(s if strand > 0 else e, 0, (w if strand > 0 else -w), 0, width=0.34,
                 head_width=0.54, head_length=min(0.9, w * 0.4), length_includes_head=True,
                 fc=fcol(g.get("gene_function_inference", "")), ec="black" if core else "none",
                 lw=1.3 if core else 0, alpha=0.95)
        dom = g.get("sec_met_domains", "").strip()
        if dom:
            parts = [d.strip() for d in dom.split(";") if d.strip()]
            if len(parts) > 5:  # cap so long core-gene lists don't run off the axis
                parts = parts[:5] + [f"(+{len(parts) - 5} more)"]
            max_dom_lines = max(max_dom_lines, len(parts))
            ax.text((s + e) / 2, -0.58, "\n".join(parts), ha="center", va="top", fontsize=5.6, color="#333")
        # per-gene badges only for the RARE / gene-specific flags; BGC-wide T1/TTA go in the title
        y = 0.5
        if g.get("resistance_tier", "").startswith(("T2", "T3")):
            ax.text((s + e) / 2, y, "\u25c7", ha="center", fontsize=9, color="#e08214")
        if g.get("cctt_triggers", "").strip():
            ax.text((s + e) / 2, y + 0.18, "\u2605", ha="center", fontsize=9, color="#6a51a3")
    ybot = -(0.7 + 0.24 * max_dom_lines)  # give the capped domain track room above the axis
    ax.set_xlim(-1, span + 1); ax.set_ylim(ybot, 1.2); ax.set_yticks([])
    for sp in ("left", "right", "top"):
        ax.spines[sp].set_visible(False)
    ax.set_xlabel("position within BGC (kb)", fontsize=10, labelpad=8)
    # BGC-wide resistance / TTA summarised once, in the title
    rtiers = Counter(g.get("resistance_tier", "").split("_")[0] for g in genes if g.get("resistance_tier", ""))
    tta = min((g.get("bldA_tta_tier", "") for g in genes if g.get("bldA_tta_tier", "")), default="")
    res_txt = rtiers.most_common(1)[0][0] if rtiers else "n/a"
    ax.set_title(f"{sid} · {bgc}  —  {inv.get('Length_kb','?')} kb · {inv.get('Boundary','?')} · "
                 f"{inv.get('Products','?')}  |  arch {inv.get('Arch','?')} · KCB {inv.get('KCB_top','n/a')} "
                 f"({inv.get('KCB_score','')})  |  resistance {res_txt} · TTA {tta or 'n/a'}",
                 fontsize=9.5, fontweight="bold", loc="left")
    fh = [Patch(color=v, label=k) for k, v in FUNC_COL.items()]
    fl = [mlines.Line2D([], [], marker="d", color="w", markerfacecolor="#e08214", markersize=9, label="T2/T3 resistance or transporter gene"),
          mlines.Line2D([], [], marker="*", color="w", markerfacecolor="#6a51a3", markersize=11, label="CCTT cryptic-chem trigger")]
    ax.legend(handles=fh + fl, loc="upper center", ncol=4, fontsize=7.5, frameon=False, bbox_to_anchor=(0.5, 1.14))
    _png = os.path.join(out, "fig4_enriched_locus.png")
    _sidecar_csv(_png,
                 ["strain", "bgc_id", "gene_start_kb", "gene_end_kb", "strand",
                  "gene_function_inference", "sec_met_domains", "resistance_tier", "cctt_triggers"],
                 [[sid, bgc,
                   round((int(g["cds_start"]) - x0) / 1000.0, 3),
                   round((int(g["cds_end"]) - x0) / 1000.0, 3),
                   ("+" if g["strand"] in ("+", "1") else "-"),
                   g.get("gene_function_inference", ""), g.get("sec_met_domains", ""),
                   g.get("resistance_tier", ""), g.get("cctt_triggers", "")]
                  for g in genes])
    plt.tight_layout(); plt.savefig(_png, dpi=_safe_dpi(plt.gcf(), PUBLICATION_RASTER_DPI), bbox_inches="tight", facecolor="white"); plt.close()


# ---------------- FIG 5: archetype composition ----------------
def norm_arch(prod):
    p = (prod or "").lower()
    if "nrps" in p and "pks" in p:
        return "hybrid NRPS-PKS"
    if "nrps" in p:
        return "NRPS"
    if "pks" in p:
        return "PKS"
    if any(k in p for k in ("ripp", "lanthi", "lasso", "lantipeptide")):
        return "RiPP"
    if "terpene" in p:
        return "terpene"
    if "sidero" in p:
        return "siderophore"
    if "butyrolactone" in p:
        return "butyrolactone"
    if "nucleoside" in p:
        return "nucleoside"
    return "other"


def fig_archetype(root, strains, out):
    order = ["hybrid NRPS-PKS", "NRPS", "PKS", "RiPP", "terpene", "siderophore", "butyrolactone", "nucleoside", "other"]
    col = dict(zip(order, plt.cm.tab10.colors[:len(order)]))
    counts = {sid: Counter(norm_arch(r.get("Products", "")) for r in load_inventory(root, sid)) for sid in strains}
    fig, ax = plt.subplots(figsize=(_strain_bar_width(strains), 5.4))
    bottom = np.zeros(len(strains))
    for a in order:
        vals = np.array([counts[sid].get(a, 0) for sid in strains], float)
        if vals.sum() == 0:
            continue
        ax.bar(strains, vals, bottom=bottom, color=col[a], label=a, edgecolor="white", linewidth=0.5); bottom += vals
    for i in range(len(strains)):
        ax.text(i, bottom[i] + 0.5, f"{int(bottom[i])} BGCs", ha="center", fontsize=9)
    ax.set_ylabel("BGC count", fontsize=11)
    ax.set_ylim(0, bottom.max() * 1.12)
    _finish_strain_axis(ax, strains)
    ax.set_title("BGC architecture-archetype composition per strain", fontweight="bold", fontsize=12)
    ax.legend(fontsize=8.5, frameon=False, ncol=1, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    _png = os.path.join(out, "fig5_archetype.png")
    _sidecar_csv(_png, ["strain", "archetype", "n_bgcs"],
                 [[sid, a, int(counts[sid].get(a, 0))] for sid in strains for a in order])
    plt.tight_layout(); plt.savefig(_png, dpi=_safe_dpi(plt.gcf(), PUBLICATION_RASTER_DPI), bbox_inches="tight", facecolor="white"); plt.close()


# ---------------- FIG 6: KCB novelty landscape ----------------
def fig_kcb_novelty(root, strains, out):
    # KCB scores are bimodal (dark ~0 vs known >=40, essentially nothing between), so a
    # ranked score-height bar hides the dark BGCs at zero height. Show tier COUNTS instead.
    dark, partial, known = [], [], []
    for sid in strains:
        ks = []
        for r in load_inventory(root, sid):
            try:
                ks.append(float(r.get("KCB_score") or 0))
            except ValueError:
                ks.append(0.0)
        dark.append(sum(1 for v in ks if v < 1))
        partial.append(sum(1 for v in ks if 1 <= v < 40))
        known.append(sum(1 for v in ks if v >= 40))
    dark, partial, known = map(np.array, (dark, partial, known))
    fig, ax = plt.subplots(figsize=(_strain_bar_width(strains), 5.4))
    ax.bar(strains, dark, color="#b2182b", label="KCB-dark (<1): candidate-novel", edgecolor="white")
    ax.bar(strains, partial, bottom=dark, color="#e08214", label="partial (1-40)", edgecolor="white")
    ax.bar(strains, known, bottom=dark + partial, color="#2166ac", label="known-like (>=40)", edgecolor="white")
    tot = dark + partial + known
    for i, sid in enumerate(strains):
        pct = 100 * dark[i] / tot[i] if tot[i] else 0
        ax.text(i, dark[i] / 2, f"{dark[i]}", ha="center", va="center", color="white", fontsize=10, fontweight="bold")
        ax.text(i, tot[i] + 0.6, f"{pct:.0f}% dark", ha="center", fontsize=9, color="#b2182b")
    ax.set_ylabel("BGC count", fontsize=11)
    ax.set_ylim(0, tot.max() * 1.12)
    _finish_strain_axis(ax, strains)
    ax.set_title("KCB novelty composition across strains (similarity, not identity)", fontweight="bold", fontsize=12)
    ax.legend(fontsize=8.5, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    _png = os.path.join(out, "fig6_kcb_novelty.png")
    _sidecar_csv(_png, ["strain", "kcb_tier", "n_bgcs"],
                 [row for i, sid in enumerate(strains) for row in (
                     [sid, "dark_lt1_candidate_novel", int(dark[i])],
                     [sid, "partial_1_to_40", int(partial[i])],
                     [sid, "known_like_ge40", int(known[i])])])
    plt.tight_layout(); plt.savefig(_png, dpi=_safe_dpi(plt.gcf(), PUBLICATION_RASTER_DPI), bbox_inches="tight", facecolor="white"); plt.close()


# ---------------- FIG 7: CCTT cryptic-chemistry trigger landscape ----------------
def fig_cctt_heatmap(root, strains, out):
    """Trigger family x strain, counted as BGCs carrying >=1 gene with that trigger."""
    trig_by_strain = {}
    all_trigs = Counter()
    for sid in strains:
        genes = load_genes(root, sid)
        per = Counter()
        for b, gs in genes.items():
            fams = set()
            for g in gs:
                for t in g.get("cctt_triggers", "").split(";"):
                    t = t.strip()
                    if t:
                        fams.add(t.split("_")[0])  # e.g. T43-HAL
            for f in fams:
                per[f] += 1  # count BGCs, not genes
        trig_by_strain[sid] = per
        all_trigs.update(per)
    fams = [f for f, _ in all_trigs.most_common()]
    if not fams:
        emit("  (no CCTT triggers; skipping fig7)"); return
    M = np.array([[trig_by_strain[sid].get(f, 0) for sid in strains] for f in fams], float)
    fig, ax = plt.subplots(figsize=(1.6 + 1.3 * len(strains), 0.5 + 0.42 * len(fams)))
    im = ax.imshow(M, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(strains))); ax.set_xticklabels(strains, fontsize=9)
    ax.set_yticks(range(len(fams))); ax.set_yticklabels([f.replace("T43-", "") for f in fams], fontsize=8)
    for i in range(len(fams)):
        for j in range(len(strains)):
            if M[i, j]:
                ax.text(j, i, f"{int(M[i, j])}", ha="center", va="center",
                        color="white" if M[i, j] > M.max() * 0.6 else "black", fontsize=8)
    ax.set_title("CCTT cryptic-chemistry trigger landscape\n(BGCs per strain carrying each trigger family)",
                 fontweight="bold", fontsize=11)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04); cb.set_label("BGCs with trigger", fontsize=8)
    _png = os.path.join(out, "fig7_cctt_triggers.png")
    _sidecar_csv(_png, ["trigger_family", "strain", "n_bgcs"],
                 [[fams[i], strains[j], int(M[i, j])] for i in range(len(fams)) for j in range(len(strains))])
    plt.tight_layout(); plt.savefig(_png, dpi=_safe_dpi(plt.gcf(), PUBLICATION_RASTER_DPI), bbox_inches="tight", facecolor="white"); plt.close()


# ---------------- FIG 8: boundary / fragmentation profile ----------------
def fig_boundary_profile(root, strains, out):
    """Interior / Edge / Full-contig BGCs per strain — the assembly-quality lens on every count."""
    order = ["Interior", "Edge", "Full-contig"]
    col = {"Interior": "#1b7837", "Edge": "#e08214", "Full-contig": "#b2182b"}
    counts = {sid: Counter(r.get("Boundary", "") for r in load_inventory(root, sid)) for sid in strains}
    fig, ax = plt.subplots(figsize=(_strain_bar_width(strains), 5.4))
    bottom = np.zeros(len(strains))
    for k in order:
        vals = np.array([counts[sid].get(k, 0) for sid in strains], float)
        ax.bar(strains, vals, bottom=bottom, color=col[k], label=k, edgecolor="white", linewidth=0.5)
        for i in range(len(strains)):
            if vals[i]:
                ax.text(i, bottom[i] + vals[i] / 2, f"{int(vals[i])}", ha="center", va="center",
                        color="white", fontsize=9)
        bottom += vals
    for i, sid in enumerate(strains):
        interior = counts[sid].get("Interior", 0); tot = bottom[i]
        ax.text(i, tot + 0.6, f"{100*interior/tot:.0f}% interior" if tot else "", ha="center", fontsize=9, color="#1b7837")
    ax.set_ylabel("BGC count", fontsize=11)
    ax.set_ylim(0, bottom.max() * 1.12)
    _finish_strain_axis(ax, strains)
    ax.set_title("BGC boundary / fragmentation profile per strain\n(interior = confident; edge/full-contig = fragment-limited)",
                 fontweight="bold", fontsize=11)
    ax.legend(fontsize=9, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    _png = os.path.join(out, "fig8_boundary_profile.png")
    _sidecar_csv(_png, ["strain", "boundary", "n_bgcs"],
                 [[sid, k, int(counts[sid].get(k, 0))] for sid in strains for k in order])
    plt.tight_layout(); plt.savefig(_png, dpi=_safe_dpi(plt.gcf(), PUBLICATION_RASTER_DPI), bbox_inches="tight", facecolor="white"); plt.close()


# ---------------- FIG 9: domain co-occurrence matrix ----------------
def fig_domain_cooccur(root, strains, out, top_n=16):
    """Which biosynthetic domains travel together: cell = # BGCs (pooled across strains) whose
    domain set contains BOTH domains. Diagonal = per-domain BGC frequency."""
    from itertools import combinations
    bgc_sets = []
    freq = Counter()
    for sid in strains:
        for b, gs in load_genes(root, sid).items():
            doms = set()
            for g in gs:
                for d in g.get("sec_met_domains", "").split(";"):
                    d = d.strip()
                    if d:
                        doms.add(d)
            if doms:
                bgc_sets.append(doms)
                freq.update(doms)
    top = [d for d, _ in freq.most_common(top_n)]
    idx = {d: i for i, d in enumerate(top)}
    M = np.zeros((len(top), len(top)))
    for doms in bgc_sets:
        present = [d for d in doms if d in idx]
        for d in present:
            M[idx[d], idx[d]] += 1
        for a, b in combinations(present, 2):
            M[idx[a], idx[b]] += 1; M[idx[b], idx[a]] += 1
    fig, ax = plt.subplots(figsize=(9.5, 8.5))
    im = ax.imshow(M, cmap="BuPu", aspect="auto")
    ax.set_xticks(range(len(top))); ax.set_xticklabels(top, rotation=90, fontsize=7.5)
    ax.set_yticks(range(len(top))); ax.set_yticklabels(top, fontsize=7.5)
    for i in range(len(top)):
        for j in range(len(top)):
            if M[i, j]:
                ax.text(j, i, f"{int(M[i, j])}", ha="center", va="center",
                        color="white" if M[i, j] > M.max() * 0.55 else "#333", fontsize=6.5)
    ax.set_title("Domain co-occurrence across BGCs (pooled cohort)\n"
                 "cell = BGCs carrying both domains; diagonal = domain frequency",
                 fontweight="bold", fontsize=11)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04); cb.set_label("BGCs", fontsize=8)
    _png = os.path.join(out, "fig9_domain_cooccur.png")
    _sidecar_csv(_png, ["domain_a", "domain_b", "n_bgcs"],
                 [[top[i], top[j], int(M[i, j])] for i in range(len(top)) for j in range(i, len(top))])
    plt.tight_layout(); plt.savefig(_png, dpi=_safe_dpi(plt.gcf(), PUBLICATION_RASTER_DPI), bbox_inches="tight", facecolor="white"); plt.close()


# ---------------- FIG 10: resistance-marker map (self-resistance = potency tell) ----------------
def fig_resistance_map(root, strains, out):
    """BGCs by source-derived resistance tier per strain. T1 self-protection / T2 resistance-like are
    the potency tell (the cluster encodes defence against its own product); T3 is transporter-only routing."""
    order = ["T1", "T2", "T3", "none"]
    lab = {"T1": "T1 self-protection", "T2": "T2 resistance-like", "T3": "T3 transporter-only", "none": "no resistance signal"}
    col = {"T1": "#b2182b", "T2": "#e08214", "T3": "#7fb0d3", "none": "#dddddd"}
    counts = {}
    for sid in strains:
        c = Counter()
        for b, gs in load_genes(root, sid).items():
            tiers = set(g.get("resistance_tier", "").split("_")[0] for g in gs if g.get("resistance_tier", ""))
            for t in ("T1", "T2", "T3"):
                if t in tiers:
                    c[t] += 1; break
            else:
                c["none"] += 1
        counts[sid] = c
    fig, ax = plt.subplots(figsize=(_strain_bar_width(strains), 5.4))
    bottom = np.zeros(len(strains))
    for k in order:
        vals = np.array([counts[sid].get(k, 0) for sid in strains], float)
        ax.bar(strains, vals, bottom=bottom, color=col[k], label=lab[k], edgecolor="white", linewidth=0.5)
        for i in range(len(strains)):
            if vals[i]:
                ax.text(i, bottom[i] + vals[i] / 2, f"{int(vals[i])}", ha="center", va="center",
                        color="white" if k in ("T1", "T2") else "#333", fontsize=9)
        bottom += vals
    ax.set_ylabel("BGC count", fontsize=11); ax.set_ylim(0, bottom.max() * 1.10)
    _finish_strain_axis(ax, strains)
    ax.set_title("Self-resistance marker map per strain\n(T1/T2 = encodes defence against own product = potency tell)",
                 fontweight="bold", fontsize=11)
    ax.legend(fontsize=8.5, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    _png = os.path.join(out, "fig10_resistance_map.png")
    _sidecar_csv(_png, ["strain", "resistance_tier", "n_bgcs"],
                 [[sid, lab[k], int(counts[sid].get(k, 0))] for sid in strains for k in order])
    plt.tight_layout(); plt.savefig(_png, dpi=_safe_dpi(plt.gcf(), PUBLICATION_RASTER_DPI), bbox_inches="tight", facecolor="white"); plt.close()


# ---------------- FIG 11: TTA / bldA regulatory-dependency profile ----------------
def fig_tta_profile(root, strains, out):
    """BGCs by strongest bldA/TTA dependency tier per strain (min tier across genes). T1 = strongest
    dependency = developmentally gated / often silent under standard conditions = activation candidates."""
    order = ["T1", "T2", "T3", "T4"]
    lab = {"T1": "T1 strong (likely gated/cryptic)", "T2": "T2", "T3": "T3", "T4": "T4 weak / none"}
    col = {"T1": "#6a51a3", "T2": "#9e9ac8", "T3": "#cbc9e2", "T4": "#eeeeee"}
    counts = {}
    for sid in strains:
        c = Counter()
        for b, gs in load_genes(root, sid).items():
            tiers = [g.get("bldA_tta_tier", "") for g in gs if g.get("bldA_tta_tier", "")]
            c[min(tiers) if tiers else "T4"] += 1
        counts[sid] = c
    fig, ax = plt.subplots(figsize=(_strain_bar_width(strains), 5.4))
    bottom = np.zeros(len(strains))
    for k in order:
        vals = np.array([counts[sid].get(k, 0) for sid in strains], float)
        ax.bar(strains, vals, bottom=bottom, color=col[k], label=lab[k], edgecolor="white", linewidth=0.5)
        for i in range(len(strains)):
            if vals[i]:
                ax.text(i, bottom[i] + vals[i] / 2, f"{int(vals[i])}", ha="center", va="center",
                        color="white" if k == "T1" else "#333", fontsize=9)
        bottom += vals
    ax.set_ylabel("BGC count", fontsize=11); ax.set_ylim(0, bottom.max() * 1.10)
    _finish_strain_axis(ax, strains)
    ax.set_title("TTA / bldA regulatory-dependency profile per strain\n(T1 = strongest dependency = activation candidates)",
                 fontweight="bold", fontsize=11)
    ax.legend(fontsize=8.5, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    _png = os.path.join(out, "fig11_tta_profile.png")
    _sidecar_csv(_png, ["strain", "bldA_tta_tier", "n_bgcs"],
                 [[sid, lab[k], int(counts[sid].get(k, 0))] for sid in strains for k in order])
    plt.tight_layout(); plt.savefig(_png, dpi=_safe_dpi(plt.gcf(), PUBLICATION_RASTER_DPI), bbox_inches="tight", facecolor="white"); plt.close()




def _discover_strains(root):
    import glob as _g, os as _o
    out = []
    for d in sorted(_g.glob(_o.path.join(root, "*"))):
        sid = _o.path.basename(d)
        if _g.glob(_o.path.join(d, "package", f"{sid}_2_inventory.csv")) or \
           _g.glob(_o.path.join(d, f"{sid}_2_inventory.csv")):
            out.append(sid)
    return out


def generate_extended(runs_dir, out, strains=None, census_csv=None,
                      locus_strain=None, locus_bgc="BGC001"):
    """Auto-emit the 11 extended figures into `out`. Never raises: returns a result dict with the
    figures produced and any per-figure errors, so a figure failure never blocks a cohort run."""
    os.makedirs(out, exist_ok=True)
    strains = strains or _discover_strains(runs_dir)
    if not strains:
        return {"figures": 0, "produced": [], "errors": ["no strains with inventory found"], "out": out}
    locus_strain = locus_strain or strains[0]
    jobs = [
        ("fig1_census_notier.png", lambda: fig_census(runs_dir, strains, out, census_csv)),
        ("fig2_pks_bars.png", lambda: fig_pks_bars(runs_dir, strains, out)),
        ("fig3_size_vs_rich.png", lambda: fig_size_vs_rich(runs_dir, strains, out)),
        ("fig4_enriched_locus.png", lambda: fig_enriched_locus(runs_dir, locus_strain, locus_bgc, out)),
        ("fig5_archetype.png", lambda: fig_archetype(runs_dir, strains, out)),
        ("fig6_kcb_novelty.png", lambda: fig_kcb_novelty(runs_dir, strains, out)),
        ("fig7_cctt_triggers.png", lambda: fig_cctt_heatmap(runs_dir, strains, out)),
        ("fig8_boundary_profile.png", lambda: fig_boundary_profile(runs_dir, strains, out)),
        ("fig9_domain_cooccur.png", lambda: fig_domain_cooccur(runs_dir, strains, out)),
        ("fig10_resistance_map.png", lambda: fig_resistance_map(runs_dir, strains, out)),
        ("fig11_tta_profile.png", lambda: fig_tta_profile(runs_dir, strains, out)),
    ]
    produced, errors = [], []
    for name, fn in jobs:
        try:
            fn()
            if os.path.exists(os.path.join(out, name)):
                produced.append(name)
        except Exception as e:  # never block the cohort run over one figure
            errors.append(f"{name}: {type(e).__name__}: {e}")
    return {"figures": len(produced), "produced": produced, "errors": errors,
            "strains": strains, "out": out}
