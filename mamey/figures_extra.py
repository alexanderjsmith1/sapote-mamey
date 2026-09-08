"""figures_extra.py — extended deterministic auto-emit figures for the Mamey package.

The v9.7.50 figures_sapote layer added 4 reader-facing figures (DAPR scatter, AB/AF
ranked, claim-safety funnel). This module adds the next tier of figures that previously
had to be produced by hand (or via manual tool invocation) every chat — so a standard
run now CRANKS OUT a full figure pack with zero follow-up requests:

  * {strain}_8g_fig_class_distribution.png   — BGC product-class composition (bar)
  * {strain}_8h_fig_cctt_map.png             — CCTT diagnostic-trigger inventory (barh)
  * {strain}_8i_fig_length_hist.png          — BGC length distribution by edge status (stacked hist)
  * {strain}_8j_fig_edge_composition.png     — Interior / Edge / Full-contig boundary mix (bar)
  * {strain}_8k_fig_novelty_ranked.png       — Top BGCs by novelty score (barh)
  * {strain}_8l_fig_kcb_anchors.png          — Most-cited KCB anchor products (barh)
  * {strain}_8m_fig_genome_atlas.png         — genome-position atlas strip, coloured by class

All read ONLY data already written into the package (`bgc_data.json` + the normalized
triage rows from render_brief.load_facts()), so this is a pure extraction-layer addon —
no LLM/Sapote judgment, no network, no external DB. Every PNG ships its companion
_data.csv. Captions are capacity-level; KCB = similarity not identity; saccharide policy
flows through figure_policy (single source of truth). Each figure is independently
best-effort: one figure failing never blocks the others or the package seal.

Usage is automatic via render_brief; also callable directly:
    from mamey.figures_extra import render_extra_figures
    render_extra_figures(facts, stem, plt, pkg_dir)
"""
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os
from collections import Counter, defaultdict

from .render_brief import CL, SCORE_NOTE, KCB_NOTE, _setup_mpl
from .figure_policy import is_pure_saccharide, omit_saccharides
from .render_safe import shorten_label, locus_label


def _loadj(p):   # B1: context-managed json load (no leaked handle); +utf-8 (B2)
    with open(p, encoding="utf-8") as _f:
        return json.load(_f)


# Shared boundary palette (matches figures_sapote / render_brief).
_BOUND_C = {"Interior": "#2b7a4b", "Edge": "#d98a2b", "Full-contig": "#b03a3a"}
# A small categorical palette for class colouring in the atlas.
_CLASS_PALETTE = [
    "#2b7a4b", "#b5651d", "#3a6ea5", "#b03a3a", "#7a5195",
    "#bc5090", "#58508d", "#ff6361", "#ffa600", "#003f5c",
    "#669966", "#996633", "#666699", "#993366", "#339999",
]


def _foot(extra=""):
    return (f"Data-only figure \u00b7 {SCORE_NOTE} \u00b7 {KCB_NOTE} \u00b7 capacity-level"
            + (f" \u00b7 {extra}" if extra else ""))


def _write_csv(png_path, header, rows):
    with open(png_path.replace(".png", "_data.csv"), "w", newline="") as f:
        w = _SafeWriter(f)
        w.writerow(["# provenance",
                    "Mamey deterministic extraction-layer figure; capacity-level; KCB=similarity not identity"])
        w.writerow(header)
        w.writerows(rows)


def _is_lead_excluded(b):
    """True when the engine already excluded this BGC from lead prioritization (standing-rule
    downgrade, primary-metabolism guard, or mobile-element guard -- the same three flags
    scoring.py::triage_bgcs uses to withhold corrected_rank). AUDIT_374 fix: the figure
    pack previously had no way to tell an excluded BGC from a real lead -- bgc_data.json rows
    carried no exclusion field at all (see the paired cli.py::_emit_bgc_bank fix) -- so every
    BGC-based figure here (class distribution, CCTT map, length histogram, edge composition,
    KCB anchor inventory, genome atlas) counted a housekeeping/rule-excluded BGC exactly like a
    genuine lead. 5th instance of the "excluded-BGC leak" pattern (see
    AUDIT_374_META_excluded_bgc_leak_pattern/META_NOTE.md)."""
    from .scoring import is_lead_excluded  # canonical 3-signal predicate (v9.7.376)
    return is_lead_excluded(b)


def _load_bgcs(pkg):
    """Read the per-strain bgc_data.json the run already emitted (W6). Returns [] if absent.

    Excludes BGCs the engine already flagged out of lead prioritization (standing-rule /
    primary-metabolism / mobile-element) -- see _is_lead_excluded. This is the single load
    point for every BGC-based figure in this module, so the filter applies uniformly rather
    than needing to be re-added per figure function."""
    p = os.path.join(pkg, "bgc_data.json")
    if not os.path.exists(p):
        return []
    try:
        d = _loadj(p)
        return [b for b in (d.get("bgcs", []) or []) if not _is_lead_excluded(b)]
    except Exception:
        return []


def _bgc_census(pkg):
    """Full per-strain BGC total and the lead-exclusion drop, so denominator-sensitive figures
    (e.g. the 8g class distribution) can disclose exactly how many BGCs sit behind their bars.

    _load_bgcs silently removes every lead-prioritization-excluded BGC (housekeeping /
    primary-metabolism / mobile-element) before any figure sees it; that drop, plus the
    saccharide-only omission applied at figure time, is why the 8g bar total did not reconcile
    with the strain's BGC count. Returns {"total": int|None, "lead_excluded": int|None}.
    Best-effort: never raises."""
    p = os.path.join(pkg, "bgc_data.json")
    if not os.path.exists(p):
        return {"total": None, "lead_excluded": None}
    try:
        allb = _loadj(p).get("bgcs", []) or []
        return {"total": len(allb),
                "lead_excluded": sum(1 for b in allb if _is_lead_excluded(b))}
    except Exception:
        return {"total": None, "lead_excluded": None}


def _primary_class(products):
    """First non-saccharide, non-'other' class token, else first token, else 'unknown'."""
    if not products:
        return "unknown"
    toks = [t.strip() for t in str(products).replace(",", ";").split(";") if t.strip()]
    for t in toks:
        if t.lower() not in {"other", "saccharide", "saccharide-like"}:
            return t
    return toks[0] if toks else "unknown"


# --------------------------------------------------------------- class distribution
def fig_class_distribution(bgcs, census, png_path, strain_label, plt):
    kept = omit_saccharides(bgcs, get_products=lambda b: b.get("products"))
    if not kept:
        return None
    counts = Counter(_primary_class(b.get("products")) for b in kept)
    items = counts.most_common()
    labels = [k for k, _ in items]
    vals = [v for _, v in items]
    # v9.7.409 denominator transparency: these bars cover only a SUBSET of the strain's BGCs.
    # Two upstream drops happen before/at this figure and were previously undocumented, so the
    # bar total (n_kept) did not reconcile with the strain's BGC count:
    #   (1) lead-prioritization-excluded BGCs (housekeeping / primary-metabolism / mobile-element)
    #       are removed by _load_bgcs before this function ever sees them (census.lead_excluded);
    #   (2) pure-saccharide regions are omitted here by figure_policy.omit_saccharides.
    # Disclose all of it (full total, both exclusions, plotted count) in the title and CSV.
    census = census or {}
    strain_total = census.get("total")
    lead_excluded = census.get("lead_excluded")
    n_saccharide_omitted = len(bgcs) - len(kept)
    total_disp = strain_total if strain_total is not None else "?"
    fig, ax = plt.subplots(figsize=(max(7, 0.5 * len(labels) + 2), 5.0))
    bars = ax.bar(range(len(labels)), vals, color=CL["accent"], alpha=0.85,
                  edgecolor="white", linewidth=0.5)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=55, ha="right", fontsize=8)
    ax.set_ylabel("BGC count")
    ax.set_title(f"Primary product class per BGC (one class/BGC, n={len(kept)} of {total_disp} strain BGCs; "
                 f"lead-excluded + saccharide-only omitted) \u2014 {strain_label}", fontsize=10)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.05, str(v), ha="center", va="bottom", fontsize=7)
    ax.text(0, -0.30, _foot("bars = primary class for non-saccharide, lead-eligible BGCs only; "
                            "full denominator accounting in the _data.csv"),
            transform=ax.transAxes, fontsize=6, color=CL["muted"])
    fig.savefig(png_path, bbox_inches="tight"); plt.close(fig)
    # Denominator-transparent export: every BGC dropped before the bars is accounted for here.
    with open(png_path.replace(".png", "_data.csv"), "w", newline="") as _f:
        _w = _SafeWriter(_f)
        _w.writerow(["# provenance",
                     "Mamey deterministic extraction-layer figure; capacity-level; KCB=similarity not identity"])
        _w.writerow(["# denominator", "strain_total_bgcs",
                     "" if strain_total is None else strain_total])
        _w.writerow(["# excluded_upstream",
                     "lead_prioritization_excluded (housekeeping/primary-metabolism/mobile-element)",
                     "" if lead_excluded is None else lead_excluded])
        _w.writerow(["# excluded_here",
                     "saccharide_only_omitted (figure_policy.omit_saccharides)", n_saccharide_omitted])
        _w.writerow(["# plotted", "bgcs_shown_as_bars", len(kept)])
        _w.writerow(["primary_class", "bgc_count"])
        for _k, _v in items:
            _w.writerow([_k, _v])
    return png_path


# --------------------------------------------------------------- CCTT trigger map
def fig_cctt_map(bgcs, png_path, strain_label, plt):
    rows = []
    for b in bgcs:
        trig = b.get("cctt_triggers")
        if trig:
            for t in str(trig).replace(",", ";").split(";"):
                t = t.strip()
                if t:
                    rows.append((b.get("bgc_id", "?"), b.get("contig", "?"), t))
    if not rows:
        return None
    # group by trigger class
    by_trig = defaultdict(list)
    for bgc_id, contig, t in rows:
        by_trig[t].append(bgc_id)
    items = sorted(by_trig.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    labels = [f"{t}  ({len(v)})" for t, v in items]
    vals = [len(v) for _, v in items]
    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.42 * len(items) + 1.5)))
    y = list(range(len(items)))[::-1]
    ax.barh(y, vals, color=CL["high"], alpha=0.85, edgecolor="white", linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("BGC count carrying this diagnostic trigger")
    ax.set_title(f"CCTT class-defining trigger inventory \u2014 {strain_label}", fontsize=10)
    ax.text(0, -0.16, _foot("CCTT = class-compatible trigger test; a fired trigger is a class signal, not a structure"),
            transform=ax.transAxes, fontsize=6, color=CL["muted"])
    fig.savefig(png_path, bbox_inches="tight"); plt.close(fig)
    _write_csv(png_path, ["cctt_trigger", "bgc_count", "bgc_ids"],
               [[t, len(v), " ".join(v)] for t, v in items])
    return png_path


# --------------------------------------------------------------- length distribution
def fig_length_hist(bgcs, png_path, strain_label, plt):
    groups = defaultdict(list)
    for b in bgcs:
        L = b.get("length_kb")
        if L in (None, ""):
            continue
        try:
            groups[b.get("edge_status", "Full-contig")].append(float(L))
        except Exception:
            continue
    if not any(groups.values()):
        return None
    order = ["Interior", "Edge", "Full-contig"]
    present = [g for g in order if groups.get(g)] + [g for g in groups if g not in order]
    data = [groups[g] for g in present]
    colors = [_BOUND_C.get(g, "#888888") for g in present]
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    allvals = [v for vs in data for v in vs]
    bins = 18
    ax.hist(data, bins=bins, stacked=True, color=colors, label=present,
            edgecolor="white", linewidth=0.4)
    ax.set_xlabel("BGC length (kb)")
    ax.set_ylabel("BGC count")
    ax.set_title(f"BGC length distribution by boundary \u2014 {strain_label}", fontsize=10)
    ax.legend(fontsize=8, title="boundary")
    ax.text(0, -0.13, _foot("length = antiSMASH region span; Edge/Full-contig regions are truncated (under-estimates)"),
            transform=ax.transAxes, fontsize=6, color=CL["muted"])
    fig.savefig(png_path, bbox_inches="tight"); plt.close(fig)
    out_rows = []
    for g in present:
        for v in groups[g]:
            out_rows.append([g, v])
    _write_csv(png_path, ["edge_status", "length_kb"], out_rows)
    return png_path


# --------------------------------------------------------------- edge composition
def fig_edge_composition(bgcs, png_path, strain_label, plt):
    counts = Counter(b.get("edge_status", "Full-contig") for b in bgcs)
    order = ["Interior", "Edge", "Full-contig"]
    present = [g for g in order if g in counts] + [g for g in counts if g not in order]
    vals = [counts[g] for g in present]
    if not vals:
        return None
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    bars = ax.bar(range(len(present)), vals,
                  color=[_BOUND_C.get(g, "#888888") for g in present],
                  alpha=0.88, edgecolor="white", linewidth=0.5)
    ax.set_xticks(range(len(present)))
    ax.set_xticklabels(present, fontsize=9)
    ax.set_ylabel("BGC count")
    total = sum(vals)
    interior = counts.get("Interior", 0)
    edge = counts.get("Edge", 0)
    fc = counts.get("Full-contig", 0)
    corrected = interior + 0.5 * edge + 0.25 * fc
    ax.set_title(f"BGC boundary composition \u2014 {strain_label}", fontsize=10)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.1, str(v), ha="center", va="bottom", fontsize=8)
    ax.text(0, -0.16,
            _foot(f"raw={total} \u00b7 corrected={corrected:g} (Interior + \u00bd\u00b7Edge + \u00bc\u00b7Full-contig)"),
            transform=ax.transAxes, fontsize=6, color=CL["muted"])
    fig.savefig(png_path, bbox_inches="tight"); plt.close(fig)
    _write_csv(png_path, ["boundary", "bgc_count"], [[g, counts[g]] for g in present]
               + [["__corrected__", corrected]])
    return png_path


# --------------------------------------------------------------- novelty ranking
def fig_novelty_ranked(rows, png_path, strain_label, plt, topn=25):
    pts = [r for r in rows if not is_pure_saccharide(r.get("products", "")) and r.get("novelty") not in (None, "", 0)]
    pts = sorted(pts, key=lambda r: -float(r.get("novelty") or 0))[:topn]
    if not pts:
        return None
    pts = pts[::-1]
    labels = [locus_label(r, max_chars=44) for r in pts]
    vals = [float(r.get("novelty") or 0) for r in pts]
    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.34 * len(pts) + 1.5)))
    y = list(range(len(pts)))
    ax.barh(y, vals, color=CL["med"], alpha=0.9, edgecolor="white", linewidth=0.4)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7 if len(pts) > 18 else 8)
    ax.set_xlabel("Novelty priority (Novelty_auto, deterministic)")
    ax.set_title(f"Top {len(pts)} BGCs by novelty score \u2014 {strain_label}", fontsize=10)
    ax.text(0, -0.13, _foot("Novelty_auto is an auto-computed priority score, not a measurement of true novelty"),
            transform=ax.transAxes, fontsize=6, color=CL["muted"])
    fig.savefig(png_path, bbox_inches="tight"); plt.close(fig)
    _write_csv(png_path, ["bgc_id", "contig", "products", "Novelty_auto"],
               [[r["bgc_id"], r.get("contig", ""), r.get("products", ""), r.get("novelty")] for r in pts[::-1]])
    return png_path


# --------------------------------------------------------------- KCB anchor inventory
def fig_kcb_anchors(bgcs, png_path, strain_label, plt, topn=20):
    # Claim-safety: the pipeline writes sentinel values (UNRESOLVED / "do not use product name")
    # for BGCs whose product identity is withheld under their claim ceiling. Counting those as an
    # "anchor product" inverts the claim ceiling — it surfaces a bar for exactly the compounds the
    # engine refused to name. Exclude the withheld set from the anchor tally.
    _WITHHELD = {"none", "nan", "", "unresolved", "unresolved (capacity not architecture-classifiable)",
                 "unresolved; do not use product name", "do not use product name", "n/a", "na"}
    counts = Counter()
    withheld_n = 0
    for b in bgcs:
        anchor = str(b.get("closest_kcb_product") or "").strip()
        al = anchor.lower()
        if (not anchor) or al in _WITHHELD or al.startswith("unresolved"):
            if al.startswith("unresolved"):
                withheld_n += 1
            continue
        counts[anchor[:42]] += 1
    items = counts.most_common(topn)
    if not items:
        return None
    items = items[::-1]
    labels = [k for k, _ in items]
    vals = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(9.5, max(3.5, 0.38 * len(items) + 1.5)))
    y = list(range(len(items)))
    ax.barh(y, vals, color=CL["accent"], alpha=0.85, edgecolor="white", linewidth=0.4)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7 if len(items) > 14 else 8)
    ax.set_xlabel("BGC count anchored to this KCB product (similarity)")
    ax.set_title(f"Most-cited KCB anchor products \u2014 {strain_label}", fontsize=10)
    # disclose the withheld count so the reader knows they were excluded on purpose, not dropped
    note = "KCB anchors are nearest-neighbour similarity signals, never product identity calls"
    if withheld_n:
        note += f"; {withheld_n} BGC(s) with withheld/unresolved identity excluded (claim ceiling)"
    ax.text(0, -0.14, _foot(note),
            transform=ax.transAxes, fontsize=6, color=CL["muted"])
    fig.savefig(png_path, bbox_inches="tight"); plt.close(fig)
    _write_csv(png_path, ["kcb_anchor_product", "bgc_count"], [[k, v] for k, v in items[::-1]])
    return png_path


# --------------------------------------------------------------- genome atlas strip
def fig_genome_atlas(bgcs, png_path, strain_label, plt):
    """One row per contig that carries a BGC; coloured tiles per BGC by primary class."""
    kept = [b for b in bgcs if not is_pure_saccharide(b.get("products", ""))]
    if not kept:
        return None
    # group BGCs by contig
    by_contig = defaultdict(list)
    for b in kept:
        by_contig[b.get("contig", "?")].append(b)
    # order contigs by number of BGCs then name
    contigs = sorted(by_contig.keys(), key=lambda c: (-len(by_contig[c]), str(c)))
    # cap to top 28 contigs for readability; note how many were dropped
    shown = contigs[:28]
    # build class -> colour map
    classes = []
    for b in kept:
        c = _primary_class(b.get("products"))
        if c not in classes:
            classes.append(c)
    cmap = {c: _CLASS_PALETTE[i % len(_CLASS_PALETTE)] for i, c in enumerate(classes)}

    fig, ax = plt.subplots(figsize=(11, max(4, 0.42 * len(shown) + 1.6)))
    for yi, contig in enumerate(shown):
        bs = sorted(by_contig[contig], key=lambda b: str(b.get("bgc_id", "")))
        for xi, b in enumerate(bs):
            cls = _primary_class(b.get("products"))
            ax.add_patch(plt.Rectangle((xi, yi - 0.4), 0.92, 0.8,
                                       facecolor=cmap[cls], edgecolor="white", linewidth=0.6))
            tile_label = b.get("bgc_id", "").replace("BGC", "")
            if len(str(tile_label)) <= 4:  # avoid tile-label collisions in dense contigs
                ax.text(xi + 0.46, yi, tile_label,
                        ha="center", va="center", fontsize=6.0, color="white", fontweight="bold")  # LS-2
    maxw = max(len(by_contig[c]) for c in shown)
    ax.set_xlim(-0.2, maxw + 0.2)
    ax.set_ylim(-0.8, len(shown) - 0.2)
    ax.set_yticks(range(len(shown)))
    ax.set_yticklabels([shorten_label(c, max_chars=26) for c in shown], fontsize=7)
    ax.set_xticks([])
    ax.invert_yaxis()
    ax.set_title(f"Genome BGC atlas \u2014 {strain_label}", fontsize=10)
    # legend placed OUTSIDE the axes (right gutter) so it never covers BGC tiles
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=cmap[c], edgecolor="white", label=c) for c in classes[:16]]
    ax.legend(handles=handles, fontsize=6.5, ncol=1, loc="center left",
              bbox_to_anchor=(1.01, 0.5), framealpha=0.9, title="primary class")
    extra = "" if len(contigs) <= 28 else f"showing 28 of {len(contigs)} BGC-bearing contigs"
    ax.text(0, -0.10, _foot(extra or "each tile = one BGC; tiles grouped by contig; saccharide-only omitted"),
            transform=ax.transAxes, fontsize=6, color=CL["muted"])
    fig.savefig(png_path, bbox_inches="tight"); plt.close(fig)
    _write_csv(png_path, ["contig", "bgc_id", "primary_class", "products", "edge_status", "length_kb"],
               [[b.get("contig", ""), b.get("bgc_id", ""), _primary_class(b.get("products")),
                 b.get("products", ""), b.get("edge_status", ""), b.get("length_kb", "")]
                for c in shown for b in by_contig[c]])
    return png_path


# --------------------------------------------------------------- orchestrator
def fig_two_pathway(pkg, png_path, strain_label, plt):
    """8n — gene-only two-pathway map. One track per BGC window flagged as carrying two
    mechanistically-distinct biosynthetic engines (e.g. NRPS + RiPP) separated by a gap. KCB-
    independent: derived from domain architecture only. Empty/None when no window is flagged."""
    try:
        from .two_pathway import two_pathway_by_bgc
    except Exception:
        return None
    verdicts = two_pathway_by_bgc(pkg)
    flagged = {b: v for b, v in verdicts.items() if v.get("two_pathway")}
    if not flagged:
        return None

    _CLASS_COLOR = {"PKS": "#3b6ea5", "NRPS": "#b5651d", "RiPP": "#4a7c59",
                    "terpene": "#7d5ba6", "other": "#888888"}
    # one row per flagged BGC; draw each split as engine1 -- gap -- engine2
    items = sorted(flagged.items())
    fig, ax = plt.subplots(figsize=(10, max(3, 0.6 * len(items) + 1.4)))
    rows_csv = []
    for yi, (bgc, v) in enumerate(items):
        sp = v["splits"][0]  # the primary split for the track
        c1, c2, gap = sp["c1"], sp["c2"], sp["gap"]
        # normalized track: engine1 box | gap | engine2 box
        ax.add_patch(plt.Rectangle((0, yi - 0.3), 1.0, 0.6,
                                   facecolor=_CLASS_COLOR.get(c1, "#888"), edgecolor="white"))
        ax.add_patch(plt.Rectangle((2.2, yi - 0.3), 1.0, 0.6,
                                   facecolor=_CLASS_COLOR.get(c2, "#888"), edgecolor="white"))
        ax.plot([1.0, 2.2], [yi, yi], color=CL["muted"], linewidth=1.0, linestyle="--")
        ax.text(0.5, yi, c1, ha="center", va="center", fontsize=7, color="white", fontweight="bold")
        ax.text(2.7, yi, c2, ha="center", va="center", fontsize=7, color="white", fontweight="bold")
        ax.text(1.6, yi + 0.32, f"{gap/1000:.0f} kb", ha="center", va="bottom",
                fontsize=6, color=CL["muted"])
        ax.text(-0.1, yi, bgc, ha="right", va="center", fontsize=7)
        rows_csv.append([bgc, c1, c2, gap, "+".join(v.get("classes", [])), v["detail"]])

    ax.set_xlim(-1.4, 3.6)
    ax.set_ylim(-0.8, len(items) - 0.2)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.invert_yaxis()
    for s in ("top", "right", "bottom", "left"):
        ax.spines[s].set_visible(False)
    ax.set_title(f"Gene-only two-pathway map \u2014 {strain_label}", fontsize=10)
    ax.text(0, -0.12, _foot("each track = one window with two mechanistically-distinct engines; "
                            "gene-architecture only, KCB-independent; capacity-level signal"),
            transform=ax.transAxes, fontsize=6, color=CL["muted"])
    fig.savefig(png_path, bbox_inches="tight"); plt.close(fig)
    _write_csv(png_path, ["bgc_id", "engine1_class", "engine2_class", "gap_bp",
                          "classes", "detail"], rows_csv)
    return png_path


def render_extra_figures(facts, stem, plt=None, pkg=None):
    """Render the extended figure pack. Each figure is best-effort and independent.

    facts : the dict from render_brief.load_facts() (provides triage rows + strain_label)
    stem  : output path stem, e.g. '<pkg>/SID-XXX'
    pkg   : package directory (to locate bgc_data.json); inferred from stem if None.
    Returns the list of produced file paths (PNG + companion CSV for each that emitted).
    """
    plt = plt or _setup_mpl()
    label = facts.get("strain_label", "unknown strain")
    rows = facts.get("rows", [])
    if pkg is None:
        pkg = os.path.dirname(stem)
    bgcs = _load_bgcs(pkg)
    census = _bgc_census(pkg)  # full total + lead-exclusion drop, for denominator disclosure (8g)

    produced = []
    # (suffix, callable, args) — bgc-data figures and triage-row figures.
    jobs = [
        ("_8g_fig_class_distribution.png", fig_class_distribution, (bgcs, census)),
        ("_8h_fig_cctt_map.png",           fig_cctt_map,           (bgcs,)),
        ("_8i_fig_length_hist.png",        fig_length_hist,        (bgcs,)),
        ("_8j_fig_edge_composition.png",   fig_edge_composition,   (bgcs,)),
        ("_8k_fig_novelty_ranked.png",     fig_novelty_ranked,     (rows,)),
        ("_8l_fig_kcb_anchors.png",        fig_kcb_anchors,        (bgcs,)),
        ("_8m_fig_genome_atlas.png",       fig_genome_atlas,       (bgcs,)),
        ("_8n_fig_two_pathway.png",        fig_two_pathway,        (pkg,)),
    ]
    for suffix, fn, args in jobs:
        p = stem + suffix
        try:
            if fn(*args, p, label, plt):
                produced += [p, p.replace(".png", "_data.csv")]
        except Exception:
            # best-effort: one figure failing never blocks the rest or the package seal
            continue
    return produced
