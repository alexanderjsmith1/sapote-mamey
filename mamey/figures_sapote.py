"""figures_sapote.py — deterministic Sapote-layer figures for the Mamey package.

Adds the reader-facing figures that were previously hand-produced per chat:
  * DAPR dual-track scatter        -> {strain}_8c_fig_dapr_scatter.png (+_data.csv)
  * Antibacterial priority ranking -> {strain}_8d_fig_ab_ranked.png   (+_data.csv)
  * Antifungal  priority ranking   -> {strain}_8e_fig_af_ranked.png   (+_data.csv)
  * Claim-safety funnel            -> {strain}_8f_fig_funnel.png       (+_data.csv)

All read ONLY the normalized triage rows + manifest already loaded by render_brief.load_facts(),
so this is an extraction-layer addon (no LLM/Sapote judgment needed). Data-only PNGs + companion
CSVs; capacity-level captions; saccharide policy via figure_policy (single source of truth).
"""
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path
from .figure_save import save_figure
from .render_brief import CL, SCORE_NOTE, KCB_NOTE, _setup_mpl
from .figure_policy import is_pure_saccharide
from .render_safe import shorten_label, clean_scalar, locus_label, safe_kcb_display as _safe_kcb

# tunable defaults (a patch can override via figure_policy if desired)
LEAD_AB_MIN, LEAD_AF_MIN = 70.0, 44.0
RANK_TOPN = 30
_BW = {"Interior": 1.0, "Edge": 0.5, "Full-contig": 0.25}
from .boundary_palette import TRAFFIC_LIGHT as _STRAIN_C


def _foot(extra=""):
    return f"Data-only figure \u00b7 {SCORE_NOTE} \u00b7 {KCB_NOTE} \u00b7 capacity-level" + (f" \u00b7 {extra}" if extra else "")


def _save_pair(fig, png_path, *, renderer: str, provenance: str) -> None:
    target = Path(png_path)
    save_figure(
        fig, figure_id=target.stem, out_stem=target.with_suffix(""),
        renderer=renderer, package_dir=target.parent, provenance=provenance,
    )


def _kcb_short(kcb):
    if not kcb:
        return ""
    s = kcb.split("|")[1].strip() if "|" in kcb else kcb
    for junk in ("knownclusterblast", "Type:", " kn"):
        s = s.replace(junk, "")
    return s.strip()[:18]


def _is_lead_excluded(r):
    """True when the engine already excluded this BGC from lead prioritization (standing-rule
    downgrade or primary-metabolism guard -- the same signals scoring.py::triage_bgcs uses to
    withhold Corrected_rank). AUDIT_374 fix: these reader-facing priority figures
    (DAPR scatter, AB/AF ranked bars, claim-safety funnel, AB/AF vertical panels) previously had
    no way to tell an excluded BGC from a real lead -- render_brief.load_facts()'s normalized
    rows carried no exclusion field at all. 6th instance of the "excluded-BGC leak" pattern (see
    AUDIT_374_META_excluded_bgc_leak_pattern/META_NOTE.md)."""
    from .scoring import is_lead_excluded  # canonical 3-signal predicate (v9.7.376)
    return is_lead_excluded(r)


def _write_csv(png_path, header, rows):
    with open(png_path.replace(".png", "_data.csv"), "w", newline="") as f:
        w = _SafeWriter(f)
        w.writerow(["# provenance", "Mamey deterministic Sapote figure; capacity-level; KCB=similarity not identity"])
        w.writerow(header)
        w.writerows(rows)


# -------------------------------------------------------------------- DAPR scatter
def fig_dapr_scatter(rows, png_path, strain_label, plt):
    pts = [r for r in rows if not is_pure_saccharide(r["products"]) and not _is_lead_excluded(r)]
    fig, ax = plt.subplots(figsize=(7.4, 6.2))
    for b, c in _STRAIN_C.items():
        g = [r for r in pts if r["boundary"] == b]
        if g:
            ax.scatter([r["ab"] for r in g], [r["af"] for r in g], s=46, c=c, alpha=0.6,
                       edgecolors="white", linewidths=0.4, label=b, zorder=3)
    # median guides + dual-threat quadrant
    if pts:
        import statistics as st
        abm = st.median([r["ab"] for r in pts]); afm = st.median([r["af"] for r in pts])
        ax.axvline(abm, color=CL["rule"], lw=0.8, ls="--", zorder=1)
        ax.axhline(afm, color=CL["rule"], lw=0.8, ls="--", zorder=1)
    # label the top-5 AB and top-3 AF leads
    lead = sorted(pts, key=lambda r: -r["ab"])[:5] + sorted(pts, key=lambda r: -r["af"])[:3]
    # v9.7.87 Defect 1: de-collide labels that share an (ab, af) coordinate. On low-diversity
    # strains two leads commonly tie on both axes (e.g. two BGCs both at 39/34, two at 41/32)
    # and the fixed (5,3) offset overprinted them into garbled superimpositions. Group
    # by rounded (ab, af), sort each group by bgc_id (stable), stack with an incremental vertical
    # offset, and draw a thin leader line for the 2nd+ labels so the anchor stays unambiguous.
    from collections import defaultdict as _dd
    lead = list({id(x): x for x in lead}.values())
    _clusters = _dd(list)
    for r in lead:
        _clusters[(round(r["ab"], 1), round(r["af"], 1))].append(r)
    for (_ab, _af), _grp in _clusters.items():
        for _i, r in enumerate(sorted(_grp, key=lambda x: x["bgc_id"])):
            lab = locus_label(r, max_chars=28)  # P-8 node/contig-first anchor (BGC-anchoring rule)
            _dy = 3 + _i * 11
            ax.annotate(lab, (_ab, _af), xytext=(7, _dy), textcoords="offset points",
                        fontsize=7.0, color=CL["ink"], clip_on=False,
                        arrowprops=(dict(arrowstyle="-", color="#bbb", lw=0.4,
                                         shrinkA=0, shrinkB=2) if _i else None))
    # Extend x-axis right margin so labels near the right edge are not clipped.
    # v9.7.86 P-8: node-anchored labels are long (~28 chars), so widen the right padding
    # from 18% to 32% to keep the locus_label anchors from clipping.
    if pts:
        x_max = max(r["ab"] for r in pts)
        x_min = min(r["ab"] for r in pts)
        x_range = max(x_max - x_min, 1)
        ax.set_xlim(x_min - x_range * 0.05, x_max + x_range * 0.32)
    ax.set_xlabel("Antibacterial priority (AB_auto, deterministic)")
    ax.set_ylabel("Antifungal priority (AF_auto, deterministic)")
    ax.set_title(f"DAPR dual-track priority \u2014 {strain_label}", fontsize=10)
    ax.legend(fontsize=7.5, title="boundary", loc="best", framealpha=0.9)
    ax.text(0, -0.12, _foot("marker = one BGC; dashed = cohort medians (dual-threat = upper-right)"),
            transform=ax.transAxes, fontsize=6, color=CL["muted"])
    _save_pair(fig, png_path, renderer="figures_sapote.dapr_scatter",
               provenance=f"normalized_triage_rows={len(rows)}"); plt.close(fig)
    _write_csv(png_path, ["bgc_id", "contig", "region", "boundary", "AB_auto", "AF_auto", "KCB_top"],
               [[r["bgc_id"], r["contig"], r["region"], r["boundary"], r["ab"], r["af"], r["kcb_top"]] for r in pts])
    return png_path


# -------------------------------------------------------------------- ranked companions
def _fig_ranked(rows, png_path, strain_label, plt, axis, axis_label, title):
    pool = sorted([r for r in rows if not is_pure_saccharide(r["products"]) and not _is_lead_excluded(r)],
                  key=lambda r: -r[axis])[:RANK_TOPN]
    if not pool:
        return None
    n = len(pool)
    fig, ax = plt.subplots(figsize=(8.2, max(4.5, n * 0.30)))
    ys = list(range(n))[::-1]
    for yi, r in zip(ys, pool):
        val = r[axis]; c = _STRAIN_C.get(r["boundary"], CL["muted"])
        lab = r["bgc_id"] + (f" ({_kcb_short(r['kcb_top'])})" if _kcb_short(r["kcb_top"]) else "")
        ax.plot([0, val], [yi, yi], color=c, lw=1.4, alpha=0.5, zorder=1)
        ax.scatter([val], [yi], color=c, s=55, edgecolors="white", linewidths=0.6, zorder=3)
        ax.annotate(f"{val:.0f}", (val, yi), xytext=(10, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=9.5, fontweight="bold", color=CL["ink"], zorder=4)
        ax.text(-0.6, yi, lab, va="center", ha="right", fontsize=8, color=c)
    ax.set_yticks([]); ax.set_ylim(-1, n)
    ax.set_xlim(0, (max(r[axis] for r in pool) or 1) * 1.24)
    ax.set_xlabel(axis_label)
    ax.set_title(title, fontsize=10)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.text(0, -0.06, _foot("priority score, not measured potency"), transform=ax.transAxes,
            fontsize=6, color=CL["muted"])
    _save_pair(fig, png_path, renderer=f"figures_sapote.ranked_{axis}",
               provenance=f"normalized_triage_rows={len(rows)};displayed={len(pool)}"); plt.close(fig)
    _write_csv(png_path, ["rank", "bgc_id", "contig", "region", "boundary", axis_label.split()[0]],
               [[i + 1, r["bgc_id"], r["contig"], r["region"], r["boundary"], r[axis]] for i, r in enumerate(pool)])
    return png_path


def fig_ab_ranked(rows, png_path, strain_label, plt):
    return _fig_ranked(rows, png_path, strain_label, plt, "ab",
                       "Antibacterial priority (AB_auto, deterministic score)",
                       f"Antibacterial priority ranking (top {RANK_TOPN}) \u2014 {strain_label}")


def fig_af_ranked(rows, png_path, strain_label, plt):
    return _fig_ranked(rows, png_path, strain_label, plt, "af",
                       "Antifungal priority (AF_auto, deterministic score)",
                       f"Antifungal priority ranking (top {RANK_TOPN}) \u2014 {strain_label}")


# -------------------------------------------------------------------- claim-safety funnel
def fig_funnel(rows, png_path, strain_label, plt):
    raw = len(rows)
    corrected = sum(_BW.get(r["boundary"], 0.25) for r in rows)
    nonsacc = [r for r in rows if not is_pure_saccharide(r["products"])]
    minus_sacc = sum(_BW.get(r["boundary"], 0.25) for r in nonsacc)
    # AUDIT_374 fix: the final "genuine lead-tier" stage must also exclude BGCs the
    # engine already withheld from lead prioritization (standing-rule/primary-metabolism
    # guard) -- their raw AB/AF score is untouched by those guards (only Lead_tier/
    # Corrected_rank are), so an excluded BGC with a high score previously inflated this
    # count exactly as if it were a real lead. `nonsacc` (feeding the "Saccharide BGCs
    # omitted" stage above) is left as saccharide-only so that stage's own label stays
    # accurate; only the leads count gets the extra filter.
    nonexcluded = [r for r in nonsacc if not _is_lead_excluded(r)]
    leads = sum(1 for r in nonexcluded if r["ab"] >= LEAD_AB_MIN or r["af"] >= LEAD_AF_MIN)
    stages = [("Raw BGC calls", raw),
              ("Corrected count\n(Int+\u00bdEdge+\u00bcFC)", round(corrected, 1)),
              ("Saccharide BGCs\nomitted", round(minus_sacc, 1)),
              (f"Genuine lead-tier\n(AB\u2265{int(LEAD_AB_MIN)} or AF\u2265{int(LEAD_AF_MIN)})", leads)]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ys = list(range(len(stages)))[::-1]
    cols = ["#9aa7b1", "#5b88b8", "#caa24a", "#1b8a5a"]
    ax.barh(ys, [s[1] for s in stages], color=cols, height=0.62)
    for yi, (_, v) in zip(ys, stages):
        ax.text(v + max(raw, 1) * 0.012, yi, str(v), va="center", fontsize=10, fontweight="bold", color=CL["ink"])
    ax.set_yticks(ys); ax.set_yticklabels([s[0] for s in stages], fontsize=9)
    ax.set_xlabel("BGCs (count, or corrected weight)")
    ax.set_xlim(0, max(raw, 1) * 1.10)
    ax.set_title(f"Claim-safety funnel \u2014 {strain_label}", fontsize=10)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.text(0, -0.22, _foot("each step a stated deterministic rule"), transform=ax.transAxes,
            fontsize=6, color=CL["muted"])
    _save_pair(fig, png_path, renderer="figures_sapote.claim_safety_funnel",
               provenance=f"normalized_triage_rows={len(rows)}"); plt.close(fig)
    _write_csv(png_path, ["stage", "value", "rule"],
               [["raw_bgc_calls", raw, "count of antiSMASH regions"],
                ["corrected_count", round(corrected, 1), "Interior*1 + Edge*0.5 + FullContig*0.25"],
                ["minus_saccharide_only", round(minus_sacc, 1), "figure_policy.is_pure_saccharide excluded"],
                ["genuine_lead_tier", leads, f"AB_auto>={LEAD_AB_MIN} or AF_auto>={LEAD_AF_MIN}, saccharide-only and standing-rule/primary-metabolism-excluded removed"]])
    return png_path




# ── Combined AB + AF vertical-bar panel (v9.7.72) ─────────────────────────────
# Two side-by-side vertical bar subplots: AB on the left, AF on the right.
# Node/contig-first labels (via locus_label from render_safe). Non-default palette
# matching the boundary-aware colour scheme already used across Mamey figures.
# Missing one axis (all-zero AF or all-zero AB) → single-panel reduced figure.

def fig_ab_af_vertical_panels(rows, png_path, strain_label, plt, topn=None):
    """Vertical-bar AB and AF priority panels side by side.

    Each panel shows top-N BGCs by that score. Labels are node/contig first with
    BGC### in parentheses, wrapped to fit. Non-default palette; boundary-aware
    bar colours. Source CSV sidecar written alongside the PNG.

    Args:
        rows:          normalized triage rows from load_facts()
        png_path:      output PNG path
        strain_label:  strain display label
        plt:           matplotlib.pyplot instance
        topn:          number of BGCs per panel (default RANK_TOPN)
    Returns:
        png_path if produced, else None.
    """
    from .render_safe import locus_label as _ll, wrap_label as _wrap
    import textwrap as _tw
    topn = topn or RANK_TOPN
    pool = [r for r in rows if not is_pure_saccharide(r.get("products")) and not _is_lead_excluded(r)]
    pool_ab = sorted(pool, key=lambda r: -float(r.get("ab") or 0))[:topn]
    pool_af = sorted(pool, key=lambda r: -float(r.get("af") or 0))[:topn]

    has_ab = bool(pool_ab and max(float(r.get("ab") or 0) for r in pool_ab) > 0)
    has_af = bool(pool_af and max(float(r.get("af") or 0) for r in pool_af) > 0)
    if not has_ab and not has_af:
        return None

    n_panels = int(has_ab) + int(has_af)
    fig, axes = plt.subplots(1, n_panels, figsize=(7.2 * n_panels, max(5.5, topn * 0.38 + 2.0)),
                              squeeze=False)

    def _draw_panel(ax, pool, axis, xlabel, title):
        n = len(pool)
        xs = list(range(n))
        vals = [float(r.get(axis) or 0) for r in pool]
        bar_colors = [_STRAIN_C.get(r.get("boundary"), "#9aa7b1") for r in pool]
        bars = ax.bar(xs, vals, color=bar_colors, edgecolor="white", linewidth=0.5, width=0.72)

        # x-axis: node-first labels, wrapped at word boundaries
        labels = []
        for r in pool:
            raw = _ll(r, max_chars=44)
            # wrap to max 2 lines at word boundary
            parts = _tw.wrap(raw, width=18, break_long_words=False)
            labels.append("\n".join(parts[:2]) + ("…" if len(parts) > 2 else ""))
        ax.set_xticks(xs)
        ax.set_xticklabels(labels, rotation=38, ha="right", fontsize=6.5)
        ax.set_ylabel(xlabel, fontsize=8)
        ax.set_ylim(0, (max(vals) or 1) * 1.18)
        ax.set_title(title, fontsize=9.5, fontweight="bold")
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, val + (max(vals) or 1) * 0.012,
                        f"{val:.0f}", ha="center", va="bottom", fontsize=7.5,
                        fontweight="bold", color="#1a1a1a")
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)

    ax_idx = 0
    if has_ab:
        _draw_panel(axes[0][ax_idx], pool_ab, "ab",
                    "Antibacterial priority score (AB_auto, deterministic)",
                    f"AB priority — {strain_label}")
        ax_idx += 1
    if has_af:
        _draw_panel(axes[0][ax_idx], pool_af, "af",
                    "Antifungal priority score (AF_auto, deterministic)",
                    f"AF priority — {strain_label}")

    # boundary legend
    import matplotlib.patches as _mp
    legend_handles = [_mp.Patch(color=c, label=lab)
                      for lab, c in [("Interior", _STRAIN_C["Interior"]),
                                     ("Edge", _STRAIN_C["Edge"]),
                                     ("Full-contig", _STRAIN_C["Full-contig"])]]
    fig.legend(handles=legend_handles, loc="lower center", ncol=3, fontsize=7.5,
               framealpha=0.85, bbox_to_anchor=(0.5, -0.02))

    fig.text(0.01, 0.014,
             f"Data-only · AB/AF = deterministic priority scores, not measured potency · "
             f"Node/contig-first labels · KCB=similarity not identity",
             fontsize=6.0, color=CL["muted"])  # LS-2: ≥6pt; LS-3: y≥0.012
    # Figure-Key-KCB-Class-1: bottom key table — class + KCB anchor per BGC.
    # Shows similarity/class context, not product identity claims.
    key_rows = []
    for r in (pool_ab if has_ab else pool_af)[:10]:
        cls = (r.get("products") or "").split(";")[0].strip()[:22] or "unresolved"
        kcb_ctx = _safe_kcb(r)[:28] or "—"
        key_rows.append(f"{_ll(r, max_chars=28)}  |  {cls}  |  KCB~{kcb_ctx} (similarity)")
    if key_rows:
        key_text = "\n".join(key_rows)
        fig.text(0.01, -0.01,
                 "Class / KCB context (similarity, not identity):  " + "    ·    ".join(key_rows[:3]),
                 fontsize=6.0, color=CL["muted"], va="top", wrap=True)  # LS-2
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    _save_pair(fig, png_path, renderer="figures_sapote.ab_af_vertical_panels",
               provenance=f"normalized_triage_rows={len(rows)};top_n={topn}")
    plt.close(fig)

    # Sidecar CSV — full data for both axes
    all_bgcs = {r["bgc_id"]: r for r in pool_ab + pool_af}
    csv_rows = []
    for bgc_id, r in all_bgcs.items():
        csv_rows.append([
            bgc_id,
            _ll(r, max_chars=80),
            r.get("contig", ""), r.get("region", ""), r.get("boundary", ""),
            float(r.get("ab") or 0), float(r.get("af") or 0),
            r.get("lead_tier", ""),
        ])
    _write_csv(png_path, ["bgc_id", "assembly_locator", "contig", "region", "boundary",
                           "AB_auto", "AF_auto", "lead_tier"], csv_rows)
    return png_path



def write_print_figure_pack(produced_pngs: list[str], pkg_dir: str, strain_label: str, plt) -> dict:
    """Write a print-ready figure pack: PRINT_FIGURE_PACK.md + per-page PDF + manifest.

    Args:
        produced_pngs: list of PNG paths already generated
        pkg_dir:       package directory
        strain_label:  strain display label
        plt:           matplotlib.pyplot instance
    Returns:
        {"pdf": pdf_path, "md": md_path, "manifest": manifest_path}
    """
    import os, csv as _csv, datetime
    from pathlib import Path

    pkg = Path(pkg_dir)
    today = datetime.date.today().isoformat()
    pngs = [p for p in produced_pngs if p.endswith(".png") and os.path.exists(p)]

    # ── per-page PDF ──────────────────────────────────────────────────────────
    pdf_path = str(pkg / f"{Path(pkg).name}_PRINT_FIGURE_PACK.pdf")
    try:
        import matplotlib.image as _mpimg
        from matplotlib.backends.backend_pdf import PdfPages
        with PdfPages(pdf_path) as pdf:
            for png in pngs:
                try:
                    img = _mpimg.imread(png)
                    h, w = img.shape[0], img.shape[1]
                    fig = plt.figure(figsize=(min(11, w / 100.0), min(8.5, h / 100.0)))
                    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
                    ax.imshow(img)
                    pdf.savefig(fig); plt.close(fig)
                except Exception:
                    continue
        pdf_ok = True
    except Exception:
        pdf_ok = False; pdf_path = ""

    # ── PRINT_FIGURE_PACK.md ──────────────────────────────────────────────────
    md_lines = [
        f"# Print figure pack — {strain_label}",
        f"Generated: {today}",
        "",
        "## Figures included",
        "",
    ]
    for p in pngs:
        stem = Path(p).stem
        csv_sidecar = p.replace(".png", "_data.csv")
        has_csv = os.path.exists(csv_sidecar)
        md_lines.append(f"- **{stem}** ({Path(p).name})" +
                        (" + `_data.csv`" if has_csv else ""))
    if pdf_ok and pdf_path:
        md_lines += ["", f"## PDF export", "", f"`{Path(pdf_path).name}` — one figure per page."]

    md_lines += [
        "",
        "## Claim-safety",
        "",
        "All figures show deterministic extraction-layer scores only.",
        "AB/AF scores = priority indices, not measured potency.",
        "KCB = similarity, not identity.",
        "BGC capacity ≠ compound production.",
        "",
        "## Skipped figures",
        "",
        "Figures requiring judgment-layer data (Mode B prose, bench guides, literature)",
        "are not included in this extraction-layer pack.",
    ]
    md_path = str(pkg / "PRINT_FIGURE_PACK.md")
    with open(md_path, "w", encoding="utf-8") as _md_fh:
        _md_fh.write("\n".join(md_lines) + "\n")

    # ── figure manifest CSV ───────────────────────────────────────────────────
    manifest_path = str(pkg / "figure_manifest_print.csv")
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        w = _SafeWriter(f)
        w.writerow(["# provenance", "Mamey print figure pack manifest"])
        w.writerow(["figure_stem", "png_path", "csv_sidecar_exists", "included_in_pdf"])
        for p in pngs:
            stem = Path(p).stem
            has_csv = os.path.exists(p.replace(".png", "_data.csv"))
            w.writerow([stem, Path(p).name, "yes" if has_csv else "no",
                        "yes" if pdf_ok else "no"])

    return {"pdf": pdf_path if pdf_ok else "", "md": md_path, "manifest": manifest_path,
            "n_figures": len(pngs)}

def render_sapote_figures(facts, stem, plt=None):
    """Render all four deterministic Sapote figures. Returns the list of produced file paths."""
    plt = plt or _setup_mpl()
    rows, label = facts["rows"], facts["strain_label"]
    produced = []
    for suffix, fn in [("_8c_fig_dapr_scatter.png", fig_dapr_scatter),
                       ("_8d_fig_ab_ranked.png", fig_ab_ranked),
                       ("_8e_fig_af_ranked.png", fig_af_ranked),
                       ("_8f_fig_funnel.png", fig_funnel),
                       ("_8g_fig_ab_af_panels.png", fig_ab_af_vertical_panels)]:
        p = stem + suffix
        if fn(rows, p, label, plt):
            produced += [p, p.replace(".png", "_data.csv")]
    return produced
