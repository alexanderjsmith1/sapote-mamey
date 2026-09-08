"""render_brief.py — deterministic extraction-layer strain brief for the Mamey package.

Reads ONLY artifacts the sealed package already produced (manifest.json + *_4_triage_board.csv)
and renders a human-readable brief (PDF) + data-only figures (PNG) + a figure-data CSV.
No new analysis, no judgment-layer slots filled, no claim beyond capacity-level.

Deviation from the v1.9.14 reference spec: renders the PDF via matplotlib PdfPages (pure-Python,
no wkhtmltopdf dependency) so the step is portable and the non-blocking guard catches any render
exception. All hard rules (spec §4) are preserved in the output text layer.
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
import json, csv, glob, os, datetime
from collections import Counter
from .render_safe import safe_kcb_display as _safe_kcb
from .dedup_and_guard import derive_release  # SSOT for the release tag (v9.7.236: AS- is PUBLIC)
from .bioactivity_metadata import display_text as _bioactivity_text


def _loadj(p):   # B1: context-managed json load (no leaked handle); +utf-8 (B2)
    with open(p, encoding="utf-8") as _f:
        return json.load(_f)


AFFILIATION = ""
CORRECTED_FORMULA = "Interior + \u00bd\u00b7Edge + \u00bc\u00b7Full-contig"
KCB_NOTE = "KCB = similarity, not identity"
SCORE_NOTE = "AB/AF/Novelty are auto-computed priority scores, not activity measurements"
GAP_NOTE = ("Mode B, DAPR, fermentation, layperson and bench-guide deliverables are produced by "
            "the Sapote judgment pass and are not part of this sealed extraction package.")


def _gap_note(has_lay: bool = False, has_ferm: bool = False) -> str:
    """v9.7.371 fix: GAP_NOTE unconditionally claimed fermentation/layperson content is "not
    part of this sealed extraction package", but PDF-003/PDF-004 (v9.7.67) conditionally add
    exactly those pages to the SAME PDF when the judgment store has them -- so a brief that
    includes a Layperson's Overview or Fermentation page also told the reader on page 1 that no
    such content exists. This variant drops an item from the "not part of this package" list
    once its page is actually present, so the footer never contradicts the document it's in."""
    omitted = ["Mode B", "DAPR"]
    if not has_ferm:
        omitted.append("fermentation")
    if not has_lay:
        omitted.append("layperson")
    omitted.append("bench-guide")
    listed = ", ".join(omitted[:-1]) + " and " + omitted[-1] if len(omitted) > 1 else omitted[0]
    return (f"{listed} deliverables are produced by the Sapote judgment pass and are not part "
            f"of this sealed extraction package."
            + (" (This PDF includes the layperson and/or fermentation pages below, drawn from "
               "the judgment layer where already authored.)" if (has_lay or has_ferm) else ""))
# the 7 judgment slots the brief must never render as populated (spec §3)
JUDGMENT_SLOTS = ["top_bgc_targets", "split_pathway_candidates", "hallucination_traps_triggered",
                  "wet_lab_priorities", "metabolomics_targets", "missingness", "recommended_next_steps"]

CL = {"ink": "#1a1a1a", "muted": "#6b6b6b", "rule": "#d8d4cc",
      "interior": "#2b7a4b", "edge": "#d98a2b", "fc": "#b03a3a", "accent": "#b5651d",
      "exc": "#7a1f1f", "high": "#b5651d", "med": "#9a8c5a", "inv": "#a9a39a"}

# #15: assembly-tier interior-%% bands, surfaced next to the tier label in the brief.
_TIER_BAND = {"GOOD": "interior ≥70%", "MODERATE": "interior 45–70%", "POOR": "interior 20–45%", "VERY_POOR": "interior <20%", "UNKNOWN": "interior n/a"}


# ----------------------------------------------------------------------- data
def _find(pkg, suffix):
    hits = glob.glob(os.path.join(pkg, f"*{suffix}"))
    return hits[0] if hits else None

def load_facts(pkg):
    """Pull the brief's data contract from manifest + triage. Every field traces to a file."""
    m = _loadj(os.path.join(pkg, "manifest.json"))
    tri = _find(pkg, "_4_triage_board.csv")
    rows = list(csv.DictReader(open(tri, encoding="utf-8"))) if tri else []
    def col(r, *names):                       # tolerate header supersets / renames
        for n in names:
            if n in r and r[n] != "":
                return r[n]
        return ""
    norm = []
    for r in rows:
        norm.append({
            "rank": col(r, "Rank", "Corrected_rank"),
            "bgc_id": col(r, "BGC_ID"),
            "contig": col(r, "Contig", "Node_ID"),
            "region": col(r, "antiSMASH_Region", "Composite_region"),
            "products": col(r, "Products"),
            "boundary": col(r, "Boundary") or "Full-contig",
            "arch": col(r, "Arch", "Arch_Capacity"),
            "ab": _num(col(r, "AB_auto")),
            "af": _num(col(r, "AF_auto")),
            "novelty": _num(col(r, "Novelty_auto")),
            "lead_tier": col(r, "Lead_tier_auto"),
            "kcb_top": col(r, "KCB_top"),
            "kcb_score": col(r, "KCB_score"),
            "cctt": col(r, "CCTT_triggers"),
            # AUDIT_374 fix: the triage board carries these three lead-exclusion signals
            # (the same ones scoring.py::triage_bgcs uses to withhold Corrected_rank), but this
            # normalized row never surfaced them -- so every figures_sapote.py consumer of these
            # rows (DAPR scatter, AB/AF ranked bars, claim-safety funnel, AB/AF vertical panels)
            # had no way to tell a standing-rule-excluded/primary-metabolism-flagged BGC from a
            # real lead. 6th instance of the "excluded-BGC leak" pattern (see
            # AUDIT_374_META_excluded_bgc_leak_pattern/META_NOTE.md).
            "standing_rule": col(r, "Standing_rule"),
            "primary_metab_flag": col(r, "Primary_metab_flag"),
            "corrected_rank": col(r, "Corrected_rank"),
        })
    return {"manifest": m, "rows": norm,
            "display_name": m.get("display_name", m.get("strain_id", "unknown strain")),
            "strain_label": strain_display_label(m),
            "release": _release_status(m)}

def strain_display_label(manifest, *, short=False):
    """Human-facing strain label (#29). NEVER derived from the accession prefix.
    Precedence: "<Genus species> strain <ID>" when taxonomy resolves -> strain_id/display_name (canonical id)
    -> accession WITH an explicit warning (last resort, so a missing name is loud, not silent)."""
    m = manifest or {}
    tax = str(m.get("taxonomy", "") or "").strip()
    sid = str(m.get("strain_id", "") or m.get("display_name", "") or "").strip()
    acc = str(m.get("accession", "") or m.get("gca", "") or "").strip()
    # reject a sid that is itself an accession-prefix echo (the WWKH/WWJO bug): a bare alphanumeric run that
    # prefixes the accession is the database token, not a strain name. (A real id like AS-XXX / PENDING-XXX
    # has a hyphen and is never treated as an echo.)
    _s = sid.replace("PENDING-", "")
    if acc and _s and "-" not in sid and _s.isalnum() and acc.upper().startswith(_s.upper()) and len(_s) < len(acc):
        sid = ""
    # 1) standing binomial form, only when taxonomy is real (not a PENDING/placeholder)
    if tax and "PENDING" not in tax.upper() and "sp. (" not in tax.lower() and sid:
        label = f"{tax} strain {sid.replace('PENDING-', '')}"
        return (label[:46].rstrip() + "\u2026") if short and len(label) > 47 else label
    # 2/3) canonical id, never the accession
    if sid:
        return sid
    # 4) last resort: the WHOLE accession, flagged — never a sliced prefix
    if acc:
        return f"{acc} (NO STRAIN NAME \u2014 accession shown)"
    return "UNNAMED STRAIN"

def _num(x):
    try: return float(x)
    except Exception: return 0.0

def _release_status(m):
    # v9.7.335: this hardcoded PRIVATE for any AS- strain and ignored the manifest, so one sealed
    # package labelled itself PUBLIC in manifest_short.json / _1_intake.json (what the redaction
    # tooling reads) and PRIVATE on page 1 of the brief (what a human reads). The harm is
    # asymmetric: a script publishes while an analyst withholds. The manifest is the single source
    # of truth — release derivation belongs to dedup_and_guard, not to a renderer.
    rel = m.get("release")
    if rel:
        return str(rel)
    sid = str(m.get("strain_id", "")) + " " + str(m.get("display_name", ""))
    if "AS-" in sid:
        # v9.7.236 PI decision: AS- is PUBLIC. Derive via the SSOT (dedup_and_guard),
        # not a raw prefix test, so AJS-/PENDING- still fail safe to PRIVATE.
        return derive_release(str(m.get("strain_id", "")) or sid)
    return "SID-public"


# -------------------------------------------------------------------- figures
def _setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.edgecolor": CL["muted"], "axes.linewidth": 0.8, "figure.dpi": 150})
    return plt


def fig_landscape(rows, png_path, strain, plt):
    # W3: apply the shared saccharide FIGURE policy — pure-saccharide regions are omitted from the figure
    # (not the data). The single source of truth is figure_policy; the renderer must not re-derive it.
    from .figure_policy import omit_saccharides, is_pure_saccharide
    from .render_safe import shorten_label, wrap_label, locus_label
    fig_rows = omit_saccharides(rows, get_products=lambda r: r.get("products"))
    # W1: rule-based cap with an ON-FIGURE note, not a silent rows[:40]. Pure-saccharide rows are already
    # gone, so the cap only ever trims genuine surplus leads — and it says so on the figure + in the CSV.
    CAP = 40
    ordered = fig_rows[:CAP]
    n_more = len(fig_rows) - len(ordered)
    n = max(len(ordered), 1)
    fig, ax = plt.subplots(figsize=(8.4, min(0.26 * n + 2.0, 10.2)))
    ys = list(range(n))[::-1]
    bcol = {"Interior": CL["interior"], "Edge": CL["edge"], "Full-contig": CL["fc"]}
    for y, r in zip(ys, ordered):
        c = bcol.get(r["boundary"], CL["fc"])
        ax.barh(y + 0.18, r["ab"], height=0.34, color=c, zorder=3)
        ax.barh(y - 0.18, r["af"], height=0.34, color=c, alpha=0.42, zorder=3)
        # W2: tier swatch lives in a RIGHT gutter (past the 0–100 bar axis), not on the bars.
        ax.scatter(105, y, marker="s", s=26, color=_tier_color(r["lead_tier"]), zorder=5, clip_on=False)
    ax.set_yticks(ys)
    # Boss-ready labels are compact. Full contig/region locator remains in the sidecar CSV.
    ax.set_yticklabels([wrap_label(locus_label(r, max_chars=36), width=28, max_lines=2) for r in ordered], fontsize=6.2)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Auto priority score (solid = antibacterial \u00b7 faded = antifungal)", fontsize=8)
    ax.set_title(f"BGC priority landscape \u2014 {strain}", fontsize=11, loc="left", pad=8)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis="x", color=CL["rule"], linewidth=0.6, zorder=0)
    # tier-swatch legend (the right-gutter squares) so the gutter is self-explaining
    from matplotlib.lines import Line2D
    _tl = [Line2D([0], [0], marker="s", color="none", markerfacecolor=_tier_color(t), markersize=6, label=t)
           for t in ("Exceptional", "High", "Medium", "Low", "Inventory")]
    ax.legend(handles=_tl, title="lead tier (right gutter)", loc="upper right", bbox_to_anchor=(1.0, -0.06),
              ncol=4, fontsize=6.0, title_fontsize=6.5, frameon=False, handletextpad=0.2, columnspacing=0.8)
    foot = f"Data-only figure \u00b7 {SCORE_NOTE} \u00b7 {KCB_NOTE} \u00b7 capacity-level \u00b7 pure-saccharide regions omitted (retained in _data.csv)"
    if n_more > 0:
        foot += f" \u00b7 +{n_more} more non-saccharide BGC(s) by rank not shown (all in _data.csv)"
    fig.text(0.01, 0.014, foot, fontsize=6.0, color=CL["muted"])  # LS-2: ≥6pt; LS-3: y≥0.012
    fig.tight_layout(rect=(0, 0.02, 0.97, 1))
    fig.savefig(png_path, bbox_inches="tight")
    # W3/W4: ALL-rows data CSV (evidence-conserving) — every BGC, with shown_in_figure + suppressed flags.
    # v9.7.374 fix: was a direct-to-final-path write. render_brief runs inside a hard-killed
    # subprocess (cli.py::_render_brief_nonblocking, subprocess.run(..., timeout=...)), so a
    # timeout mid-write left a truncated _data.csv sitting under its real filename in package_dir
    # -- silently picked up by the subsequent checksum/seal step as a "valid" corrupt file. Same
    # tmp-sibling + os.replace pattern already used by timing.py.write() / packaging.py's
    # _atomic_write_text for exactly this reason.
    shown_keys = {(r["bgc_id"], r["region"]) for r in ordered}
    _data_csv_path = png_path.replace(".png", "_data.csv")
    _data_csv_tmp = _data_csv_path + ".tmp"
    with open(_data_csv_tmp, "w", newline="") as f:
        w = _SafeWriter(f)
        w.writerow(["# provenance",
                    "Mamey deterministic Sapote figure; capacity-level; KCB=similarity not identity"])
        w.writerow(["rank", "bgc_id", "contig", "region", "boundary", "arch",
                    "ab_auto", "af_auto", "novelty_auto", "lead_tier_auto", "kcb_score", "cctt_triggers",
                    "shown_in_figure", "suppressed_saccharide_only"])
        for r in rows:
            sacc = is_pure_saccharide(r.get("products"))
            shown = (r["bgc_id"], r["region"]) in shown_keys
            w.writerow([r["rank"], r["bgc_id"], r["contig"], r["region"], r["boundary"], r["arch"],
                        r["ab"], r["af"], r["novelty"], r["lead_tier"], r["kcb_score"], r["cctt"],
                        shown, sacc])
    os.replace(_data_csv_tmp, _data_csv_path)
    return fig

def fig_composition(rows, png_path, plt):
    prod = Counter()
    for r in rows:
        for p in [x.strip() for x in r["products"].replace(";", ",").split(",") if x.strip()]:
            prod[p] += 1
    top = prod.most_common(8)
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(7.2, 3.2), gridspec_kw={"width_ratios": [1.1, 1]})
    if top:
        labs = [t[0] for t in top][::-1]; vals = [t[1] for t in top][::-1]
        axL.barh(labs, vals, color=CL["accent"], alpha=0.85)
    axL.set_title("Product-label token frequency (antiSMASH labels, all tokens; saccharide incl.)", fontsize=9, loc="left")
    axL.tick_params(length=0, labelsize=7)
    for s in ("top", "right"): axL.spines[s].set_visible(False)
    axL.grid(axis="x", color=CL["rule"], linewidth=0.6)
    bc = Counter(r["boundary"] for r in rows)
    left = 0
    for k, c in zip(["Interior", "Edge", "Full-contig"], [CL["interior"], CL["edge"], CL["fc"]]):
        v = bc.get(k, 0)
        axR.barh(0, v, left=left, color=c, label=f"{k} ({v})")
        if v: axR.text(left + v / 2, 0, str(v), ha="center", va="center", color="white", fontsize=8, fontweight="bold")
        left += v
    axR.set_xlim(0, max(sum(bc.values()), 1)); axR.set_ylim(-1, 1); axR.set_yticks([])
    axR.set_title("Assembly boundary mix", fontsize=9, loc="left")
    for s in ("top", "right", "left"): axR.spines[s].set_visible(False)
    axR.legend(fontsize=6.4, loc="lower center", bbox_to_anchor=(0.5, -0.55), ncol=3, frameon=False)
    fig.text(0.01, 0.014, f"Data-only \u00b7 {len(rows)} BGCs \u00b7 antiSMASH product-label occurrences", fontsize=6.0, color=CL["muted"])  # LS-2: ≥6pt; LS-3: y≥0.012
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    # B-3: companion data-only CSV (the figure shows the top 8 product classes; the CSV carries ALL of them
    # plus the full boundary mix, mirroring the figure-data-CSV discipline used by the landscape figure).
    # v9.7.374 fix: same non-atomic-write-inside-a-hard-killed-subprocess hazard as
    # fig_landscape's sidecar CSV above; tmp-sibling + os.replace.
    import csv as _csv3
    _comp_csv_path = png_path.replace(".png", "_data.csv")
    _comp_csv_tmp = _comp_csv_path + ".tmp"
    with open(_comp_csv_tmp, "w", newline="") as _f3:
        _w3 = _SafeWriter(_f3)
        _w3.writerow(["# provenance",
                      "Mamey deterministic extraction-layer figure; capacity-level; KCB=similarity not identity"])
        _w3.writerow(["panel", "category", "count"])
        for _cls, _n in prod.most_common():
            _w3.writerow(["product_class", _cls, _n])
        for _k in ("Interior", "Edge", "Full-contig"):
            _w3.writerow(["boundary", _k, bc.get(_k, 0)])
    os.replace(_comp_csv_tmp, _comp_csv_path)
    fig.savefig(png_path, bbox_inches="tight")
    return fig


# ------------------------------------------------------------------------ pdf
def _tier_color(tier: str) -> str:
    """Map lead tier to a readable color for the summary table."""
    return {"High": "#1a6b3a", "Exceptional": "#003366", "Medium": "#8b5500",
            "Low": "#4a6b7a", "Inventory": "#666666"}.get(tier, CL["muted"])


def _text_page(pdf, plt, facts, tier, has_lay=False, has_ferm=False):
    """Page 1: executive summary.

    PDF-001/PDF-018/PDF-020: progressive disclosure structure:
      Section 1  Strain identity + assembly quality + corrected count
      Section 2  Top-10 lead table (rank, BGC, node, tier, AB/AF/Nov, class, KCB anchor)
      Section 3  Source scan summary (two-column) + bioactivity + resistance
      Footer     Reading guards + judgment-pending banner
    """
    m = facts["manifest"]; a = m.get("assembly", {}); bc = m.get("bgc_counts", {})
    fig = plt.figure(figsize=(8.27, 11.69))  # A4

    # Section 1: strain identity
    fig.text(0.07, 0.96, facts["strain_label"], fontsize=16, fontweight="bold", color=CL["ink"])
    fig.text(0.07, 0.940,
             f'{m.get("taxonomy","")} \u00b7 {m.get("source","")} \u00b7 release: {facts["release"]}',
             fontsize=8.0, color=CL["muted"])
    fig.text(0.07, 0.924,
             f'Mamey {m.get("workflow_version","")} \u00b7 {m.get("analysis_date","")}',
             fontsize=7.0, color=CL["muted"])
    # AMBER-03-1: `assembly_tier` is derived from interior_pct (BGC boundary status), not from
    # contigs/N50 \u2014 but it was printed as bare "tier X" directly after the contig count, so a
    # 7,296-contig assembly (AS-XXX) read as "tier GOOD". Label it BOUNDARY tier and print the
    # contiguity tier from assembly.quality next to it. Falls back cleanly on older packages.
    _q = (a.get("quality") or {})
    _frag = _q.get("fragmentation_tier")
    asm_text = (
        f'Assembly: {a.get("genome_bp","?")} bp \u00b7 {a.get("contigs","?")} contigs \u00b7 '
        f'N50 {a.get("n50","?")} \u00b7 GC {a.get("gc_pct","?")}% \u00b7 '
        f'contiguity {_frag or "not recorded"} \u00b7 '
        f'BGC-boundary tier {bc.get("assembly_tier","?")} '
        f'({_TIER_BAND.get(bc.get("assembly_tier",""), "")})  \u00b7  '
        f'Corrected BGC count: {bc.get("corrected","?")} ({CORRECTED_FORMULA})'
    )
    fig.text(0.07, 0.906, asm_text, fontsize=7.5, color=CL["ink"])

    # W10/W30: judgment-pending banner
    fig.text(0.5, 0.888,
             "DETERMINISTIC EXTRACTION COMPLETE  \u00b7  JUDGMENT LAYER PENDING",
             ha="center", fontsize=9, fontweight="bold", color=CL["exc"],
             bbox=dict(boxstyle="round,pad=0.35", facecolor="#FBF0D8",
                       edgecolor=CL["accent"], linewidth=1.0))

    # ── LS-4: VERY_POOR assembly warning box ─────────────────────────────
    if facts.get("manifest", {}).get("bgc_counts", {}).get("assembly_tier") == "VERY_POOR":
        _ip = facts.get("manifest", {}).get("bgc_counts", {}).get("interior_pct", "?")
        _warn = (
            f"ASSEMBLY QUALITY: VERY_POOR (interior {_ip}% < 20%\u2009threshold). "
            "BGC counts are a rough capacity floor only. "
            "Reassembly or long-read sequencing recommended before finalizing BGC inventory."
        )
        fig.text(0.5, 0.874, _warn, fontsize=6.5, color="#b03a3a",
                 fontweight="bold", va="center", ha="center", wrap=True,
                 bbox=dict(boxstyle="round,pad=0.35", facecolor="#fff1f2",
                           edgecolor="#b03a3a", linewidth=1.2))
        # y is reset to 0.866 at start of Section 2; no y adjustment needed here
    elif _q.get("caveat_required") and _q.get("caveat"):
        # AMBER-03-1: a highly fragmented assembly whose BGCs happen to sit interior gets a
        # non-VERY_POOR boundary tier and therefore no box at all (AS-XXX: 7,296 contigs,
        # boundary tier GOOD). Print the generated contiguity caveat in the same slot — the
        # branches are mutually exclusive, so there is no layout collision.
        fig.text(0.5, 0.874, f"ASSEMBLY CONTIGUITY: {_q.get('caveat')}", fontsize=6.5,
                 color="#b03a3a", fontweight="bold", va="center", ha="center", wrap=True,
                 bbox=dict(boxstyle="round,pad=0.35", facecolor="#fff1f2",
                           edgecolor="#b03a3a", linewidth=1.2))

    if tier == "standard":
        # Section 2: top-10 lead table
        y = 0.866
        fig.text(0.07, y,
                 "Top auto-priority leads (priority score, not activity \u2014 judgment layer pending):",
                 fontsize=8.5, fontweight="bold", color=CL["ink"])
        y -= 0.018

        hdrs = ["Node / contig", "BGC", "Tier", "AB", "AF", "Nov", "Class", "KCB anchor"]
        xs   = [0.07, 0.205, 0.260, 0.325, 0.370, 0.415, 0.460, 0.665]
        for hx, hd in zip(xs, hdrs):
            fig.text(hx, y, hd, fontsize=6.5, fontweight="bold", color=CL["ink"])
        y -= 0.002
        ax_div = fig.add_axes([0.07, y, 0.86, 0.001])
        ax_div.set_facecolor(CL["muted"]); ax_div.axis("off")
        y -= 0.015

        from .figure_policy import is_pure_saccharide as _ips
        from .render_safe import shorten_label as _sl, locus_label as _locus
        import re as _re
        shown = [r for r in facts["rows"] if not _ips(r.get("products"))][:10]
        for i, r in enumerate(shown):
            row_bg = "#F8F8F8" if i % 2 == 0 else "white"
            ax_row = fig.add_axes([0.07, y - 0.001, 0.86, 0.016])
            ax_row.set_facecolor(row_bg); ax_row.axis("off")
            tc = _tier_color(str(r.get("lead_tier", "")))
            fig.text(xs[0], y + 0.002, _locus(r, max_chars=30), fontsize=6.0, color=CL["ink"])
            fig.text(xs[1], y + 0.002, str(r.get("bgc_id", "")),
                     fontsize=6.0, color=CL["muted"])
            fig.text(xs[2], y + 0.002, str(r.get("lead_tier", "")),
                     fontsize=6.2, fontweight="bold", color=tc)
            try:
                fig.text(xs[3], y + 0.002, f'{float(r.get("ab", 0)):.0f}',
                         fontsize=6.5, color=CL["ink"])
                fig.text(xs[4], y + 0.002, f'{float(r.get("af", 0)):.0f}',
                         fontsize=6.5, color=CL["ink"])
                fig.text(xs[5], y + 0.002, f'{float(r.get("novelty", 0)):.0f}',
                         fontsize=6.5, color=CL["ink"])
            except (ValueError, TypeError):
                pass
            prod_short = _sl(str(r.get("products", ""))[:38], max_chars=38)
            fig.text(xs[6], y + 0.002, prod_short, fontsize=6.0, color=CL["ink"])
            kcb_short = _sl(_safe_kcb(r), max_chars=28)
            fig.text(xs[7], y + 0.002, kcb_short, fontsize=6.0, color=CL["muted"])
            y -= 0.018

        # v9.7.335: this attributed the WHOLE gap between the total and the 10 shown rows to the
        # saccharide filter, when most of it is rank truncation. AS-XXX printed "36 pure-saccharide
        # suppressed" with a true pure-saccharide count of ZERO (AS-XXX: 20 printed / 0 true) — a
        # reader concluded 78% of the strain was sugar chemistry. Count the two exclusions apart.
        _n_total = len(facts["rows"])
        _n_sacch = sum(1 for r in facts["rows"] if _ips(r.get("products")))
        _n_rank = _n_total - _n_sacch - len(shown)
        _parts = [f'{_n_total} total BGCs']
        if _n_sacch:
            _parts.append(f'{_n_sacch} pure-saccharide excluded')
        if _n_rank > 0:
            _parts.append(f'{_n_rank} more not shown (rank)')
        _parts.append('all retained in data')
        fig.text(0.07, y - 0.003, ' \u00b7 '.join(_parts),
                 fontsize=6.5, color=CL["muted"])
        y -= 0.022

        # Section 3: scan summary (two-column)
        y -= 0.008
        fig.text(0.07, y, "Source scans:", fontsize=8.0, fontweight="bold", color=CL["ink"])
        y -= 0.017
        scans = m.get("scan_status", {}).get("scans", [])
        col_xs = [0.07, 0.49]
        col_i = 0; col_y = [y, y]
        for s in scans[:10]:
            name, status, detail = (
                (list(s) + ["", "", ""])[:3] if isinstance(s, (list, tuple)) else (str(s), "", "")
            )
            col = col_i % 2
            fig.text(col_xs[col], col_y[col],
                     f'{name}: {status} \u2014 {str(detail)[:34]}',
                     fontsize=6.2, color=CL["muted"])
            col_y[col] -= 0.0145; col_i += 1
        y = min(col_y) - 0.005

        bio = m.get("bioactivity")
        fig.text(0.07, y,
                 _bioactivity_text(bio),
                 fontsize=7.0, color=CL["ink"])
        y -= 0.018
        rgs = m.get("resistance_gene_summary", {}).get("counts", {})
        if rgs:
            fig.text(0.07, y,
                     "Self-resistance: " + ", ".join(f"{k} {v}" for k, v in rgs.items() if v),
                     fontsize=6.8, color=CL["ink"])

    # Footer
    # ── Special class review (AF-Class-Priority-and-Other-Section-1) ────────
    # Always emitted even when counts are zero. Arylpolyene guard mandatory.
    if tier == "standard":
        _all_rows = facts.get("rows", [])
        # Nucleoside BGCs
        _nuc_bgcs = [r for r in _all_rows if "nucleoside" in (r.get("products","") or "").lower()]
        # Polyene/PTM/HSAF: T1PKS with polyene/HSAF in KCB context
        def _is_polyene_cand(r):
            p = (r.get("products","") or "").lower()
            k = (r.get("kcb_top","") or "").lower()
            return ("hsaf" in k or "polyene" in k or "ptm" in k or
                    ("t1pks" in p and any(x in k for x in ("polyene","macrolide","cyphomycin","desertomycin"))))
        def _is_arylp(r):
            return "arylpolyene" in (r.get("products","") or "").lower()
        _poly_bgcs = [r for r in _all_rows if _is_polyene_cand(r) and not _is_arylp(r)]
        _arylp_bgcs = [r for r in _all_rows if _is_arylp(r)]
        # Other-token rows: products are ONLY 'other'
        def _is_other_only(r):
            prods = [p.strip().lower() for p in (r.get("products","") or "").split(";") if p.strip()]
            return bool(prods) and all(p in ("other","") for p in prods)
        _other_bgcs = [r for r in _all_rows if _is_other_only(r)]

        if y > 0.24:  # only emit if space remains on page
            y -= 0.01
            fig.text(0.07, y, "Special class review:", fontsize=7.5, fontweight="bold",
                     color=CL["ink"]); y -= 0.015
            nuc_ids = ", ".join(r.get("bgc_id","") for r in _nuc_bgcs[:4]) or "none"
            fig.text(0.09, y, f"Nucleoside BGCs: {len(_nuc_bgcs)}  ({nuc_ids}{'\u2026' if len(_nuc_bgcs)>4 else ''})",
                     fontsize=6.5, color=CL["ink"]); y -= 0.013
            poly_ids = ", ".join(r.get("bgc_id","") for r in _poly_bgcs[:4]) or "none"
            fig.text(0.09, y, f"Polyene/PTM/HSAF candidates: {len(_poly_bgcs)}  ({poly_ids}{'\u2026' if len(_poly_bgcs)>4 else ''})",
                     fontsize=6.5, color=CL["ink"]); y -= 0.013
            if _arylp_bgcs:
                fig.text(0.09, y, f"Arylpolyene BGCs ({len(_arylp_bgcs)}) \u2014 arylpolyene \u2260 antifungal polyene macrolide evidence.",
                         fontsize=6.0, color=CL["exc"]); y -= 0.013
            oth_ids = ", ".join(r.get("bgc_id","") for r in _other_bgcs[:4]) or "none"
            fig.text(0.09, y, f"antiSMASH 'other'-class BGCs: {len(_other_bgcs)}  ({oth_ids}{'\u2026' if len(_other_bgcs)>4 else ''}) \u2014 manual inspection required.",
                     fontsize=6.5, color=CL["muted"]); y -= 0.013

    fig.text(0.07, 0.11, "Reading guards:", fontsize=8.0, fontweight="bold", color=CL["ink"])
    for i, line in enumerate([
        SCORE_NOTE,
        KCB_NOTE + "; product strings are antiSMASH labels (capacity-level, not 'produces')",
        "Bioactivity metadata is optional strain-level context; no strain is called antifungal/antibacterial-negative",
        _gap_note(has_lay, has_ferm),
    ]):
        fig.text(0.07, 0.096 - i * 0.015, "\u2022 " + line, fontsize=6.5, color=CL["muted"])
    fig.text(0.07, 0.025,
             f"Judgment-layer slots ({', '.join(JUDGMENT_SLOTS)}) are pending a Sapote pass and are not rendered here.",
             fontsize=6.0, color=CL["muted"])
    pdf.savefig(fig); plt.close(fig)


def render_brief(pkg, tier="standard", logger=None):
    """Non-blocking. Returns a status dict; never raises into the build."""
    log = logger or (lambda msg: None)
    if tier == "none":
        return {"status": "DISABLED", "files": []}
    try:
        from matplotlib.backends.backend_pdf import PdfPages
        plt = _setup_mpl()
        facts = load_facts(pkg)
        stem = os.path.join(pkg, os.path.basename(pkg.rstrip("/")).split("_")[0])
        # fall back to manifest strain_id for the file stem if pkg dir name is generic
        stem = os.path.join(pkg, str(facts["manifest"].get("strain_id", "strain")))
        land = stem + "_8a_fig_landscape.png"
        comp = stem + "_8b_fig_composition.png"
        pdf_path = stem + "_8_strain_brief.pdf"
        land_fig = fig_landscape(facts["rows"], land, facts["strain_label"], plt)
        produced = [pdf_path, land, land.replace(".png", "_data.csv")]
        # Sapote-layer deterministic figures (DAPR scatter, AB/AF ranked, claim-safety funnel)
        # v9.7.371 fix: was unguarded, unlike every other figure family below (RESCUE_FIG_SKIPPED,
        # EXTRA_FIGS_SKIPPED, SPLIT_FIGS_SKIPPED, CNBU_SKIPPED, PRINT_PACK_SKIPPED all wrap their
        # call). render_sapote_figures() has no internal per-figure guard, so any single exception
        # inside it (matplotlib hiccup, unexpected data shape) propagated out of THIS whole
        # function's outer try and skipped every remaining figure family plus the strain-brief PDF
        # itself -- contradicting this function's own docstring ("Non-blocking. Returns a status
        # dict; never raises into the build.").
        try:
            from .figures_sapote import render_sapote_figures
            produced += render_sapote_figures(facts, stem, plt)
        except Exception as e:
            log(f"SAPOTE_FIGS_SKIPPED: {type(e).__name__}: {e}")
        # Extended figure pack (class distribution, CCTT map, length hist, edge composition,
        # novelty ranking, KCB anchors, genome atlas). Pure extraction-layer; best-effort per
        # figure so one failure never blocks the rest or the package seal.
        # PDF-013: fragment rescue figure — reads ranked pairs CSV from the package.
        try:
            _pairs_csv = stem + "_4A_RGGMCI_ranked_pairs.csv"
            import os as _os
            if _os.path.exists(_pairs_csv):
                _rescue_png = stem + "_8n_fig_rggmci_rescue.png"
                _rescue_fig = fig_rggmci_rescue(_pairs_csv, _rescue_png, facts["strain_label"], plt)
                if _rescue_fig is not None:
                    produced += [_rescue_png, _rescue_png.replace(".png", "_data.csv")]
                    plt.close(_rescue_fig)
        except Exception as e:
            log(f"RESCUE_FIG_SKIPPED: {type(e).__name__}: {e}")
        try:
            from .figures_extra import render_extra_figures
            produced += render_extra_figures(facts, stem, plt, pkg)
        except Exception as e:
            log(f"EXTRA_FIGS_SKIPPED: {type(e).__name__}: {e}")
        # Split-pathway / high-KCB visualisations (topology + reference alignment), best-effort.
        # Non-blocking: emits nothing if a co-located raw antiSMASH run isn't available.
        try:
            from .figures_split import render_split_figures
            produced += render_split_figures(facts, stem, pkg, plt, log)
        except Exception as e:
            log(f"SPLIT_FIGS_SKIPPED: {type(e).__name__}: {e}")
        # v9.7.72: compute CNBU from inventory and write sidecar JSON (non-blocking).
        try:
            from .cnbu import compute_cnbu
            _inv_bgcs = []
            for _b in facts.get("manifest", {}).get("bgcs", []):
                _inv_bgcs.append({
                    "bgc_id": _b.get("bgc_id", ""),
                    "length_kb": _b.get("length_kb", 0),
                    "products": _b.get("products", []),
                })
            if _inv_bgcs:
                _cnbu_result = compute_cnbu(_inv_bgcs)
                import json as _json
                _cnbu_path = stem + "_cnbu.json"
                # v9.7.374 fix: same hard-killed-subprocess truncation hazard as the sidecar
                # CSVs above; tmp-sibling + os.replace.
                _cnbu_tmp = _cnbu_path + ".tmp"
                with open(_cnbu_tmp, "w", encoding="utf-8") as _cnbu_fh:
                    _cnbu_fh.write(_json.dumps(_cnbu_result, indent=2))
                os.replace(_cnbu_tmp, _cnbu_path)
                produced.append(_cnbu_path)
        except Exception as _cnbu_err:
            log(f"CNBU_SKIPPED: {_cnbu_err}")

        # v9.7.72: write print-ready figure pack (PRINT_FIGURE_PACK.md + PDF + manifest).
        try:
            from .figures_sapote import write_print_figure_pack as _wpp
            _pp = _wpp(produced, pkg, facts["strain_label"], plt)
            if _pp.get("pdf"):
                produced.append(_pp["pdf"])
            if _pp.get("md"):
                produced.append(_pp["md"])
            if _pp.get("manifest"):
                produced.append(_pp["manifest"])
        except Exception as _ppe:
            log(f"PRINT_PACK_SKIPPED: {_ppe}")

        # v9.7.67: read judgment store for PDF-003 (layperson) + PDF-004 (fermentation) pages.
        # Non-blocking: if no judgment output exists yet, these pages are skipped entirely.
        _lay_text = ""
        _ferm_text = ""
        _reg = {}
        try:
            from .judgment_store import read_laypersons, read_fermentation, read_register
            _lay_text = read_laypersons(pkg)
            _ferm_text = read_fermentation(pkg)
            _reg = read_register(pkg)
        except Exception as e:
            # v9.7.371 fix: was a silent `pass`, unlike every sibling try/except in this
            # function (which all log via `log(f"...SKIPPED: ...")`). A real judgment_store
            # failure (e.g. a corrupted register file, not a genuinely-absent one) was
            # indistinguishable from "no judgment pass has run yet" -- judgment_complete/
            # judgment_pct silently read False/0 either way.
            from . import degradation as _degradation
            _degradation.record("render_brief.render_brief.judgment_store_read", e, package=str(pkg))
            log(f"JUDGMENT_STORE_READ_SKIPPED: {type(e).__name__}: {e}")

        with PdfPages(pdf_path) as pdf:
            _text_page(pdf, plt, facts, tier,
                       has_lay=bool(_lay_text.strip()), has_ferm=bool(_ferm_text.strip()))
            pdf.savefig(land_fig); plt.close(land_fig)        # landscape page (both tiers)
            if tier == "standard":
                comp_fig = fig_composition(facts["rows"], comp, plt)
                pdf.savefig(comp_fig); plt.close(comp_fig)     # composition page (standard)
                produced.append(comp)
                produced.append(comp.replace(".png", "_data.csv"))  # B-3: companion data-only CSV
            # Bind every emitted figure PNG into the PDF as its own page, so the brief is a
            # single self-contained document (the loose PNGs remain for slide/figure reuse).
            if tier == "standard":
                import matplotlib.image as _mpimg
                _seen = set()
                for _p in produced:
                    if not _p.endswith(".png") or _p in _seen or not os.path.exists(_p):
                        continue
                    _seen.add(_p)
                    try:
                        _img = _mpimg.imread(_p)
                        _h, _w = _img.shape[0], _img.shape[1]
                        _pf = plt.figure(figsize=(min(11, _w / 100.0), min(8.5, _h / 100.0)))
                        _ax = _pf.add_axes([0, 0, 1, 1]); _ax.axis("off")
                        _ax.imshow(_img)
                        pdf.savefig(_pf); plt.close(_pf)
                    except Exception:
                        continue
            # PDF-003: layperson sections (one page per batch of paragraphs).
            # Only emitted when Sapote has written at least one layperson paragraph.
            if _lay_text.strip() and tier == "standard":
                _lpf = plt.figure(figsize=(8.27, 11.69))
                _lpf.text(0.07, 0.95, "Layperson’s Overview — Top leads",
                          fontsize=14, fontweight="bold", color=CL["ink"])
                _lpf.text(0.07, 0.93, "Plain-language summaries from the Sapote judgment layer.",
                          fontsize=8, color=CL["muted"])
                _lpf.text(0.07, 0.905, "Biosynthetic capacity only — compound identity claims require experimental confirmation.",
                          fontsize=7, color=CL["exc"],
                          bbox=dict(boxstyle="round,pad=0.3", facecolor="#FBF0D8",
                                    edgecolor=CL["accent"], linewidth=0.8))
                _ly = 0.87
                for _para in _lay_text.strip().split('\n\n'):
                    _para = _para.strip()
                    if not _para or _para.startswith("#"):
                        if _para.startswith("## "):
                            _lpf.text(0.07, _ly, _para[3:], fontsize=9,
                                      fontweight="bold", color=CL["ink"])
                            _ly -= 0.018
                        continue
                    import textwrap as _tw
                    for _line in _tw.wrap(_para, width=105)[:6]:
                        _lpf.text(0.07, _ly, _line, fontsize=7.5, color=CL["ink"])
                        _ly -= 0.016
                    _ly -= 0.006
                    if _ly < 0.12:
                        break
                pdf.savefig(_lpf); plt.close(_lpf)

            # PDF-004: fermentation sections (one page).
            if _ferm_text.strip() and tier == "standard":
                _ff = plt.figure(figsize=(8.27, 11.69))
                _ff.text(0.07, 0.95, "Fermentation & Isolation Notes",
                         fontsize=14, fontweight="bold", color=CL["ink"])
                _ff.text(0.07, 0.93,
                         "Isolation strategy and detection handles from the Sapote judgment layer.",
                         fontsize=8, color=CL["muted"])
                _fy = 0.89
                for _para in _ferm_text.strip().split('\n\n'):
                    _para = _para.strip()
                    if not _para:
                        continue
                    if _para.startswith("## "):
                        _ff.text(0.07, _fy, _para[3:], fontsize=9,
                                 fontweight="bold", color=CL["ink"])
                        _fy -= 0.018
                        continue
                    import textwrap as _tw2
                    for _line in _tw2.wrap(_para, width=105)[:6]:
                        _ff.text(0.07, _fy, _line, fontsize=7.5, color=CL["ink"])
                        _fy -= 0.016
                    _fy -= 0.006
                    if _fy < 0.12:
                        break
                pdf.savefig(_ff); plt.close(_ff)
        # v9.7.371 doc-currency fix: this comment previously claimed "we never read judgment
        # slots", but _lay_text/_ferm_text/_reg ARE read above (via judgment_store) and _lay_text/
        # _ferm_text ARE rendered as PDF pages when present (PDF-003/PDF-004). What this function
        # does NOT do is render any of the 7 JUDGMENT_SLOTS (top_bgc_targets, split_pathway_
        # candidates, etc.) as populated -- those remain unread/unrendered here, per the trailing
        # "Judgment-layer slots (...) are pending... not rendered here" footer line above.
        return {"status": "COMPLETE", "tier": tier,
                "judgment_complete": _reg.get("judgment_status") == "COMPLETE",
                "judgment_pct": _reg.get("completion_pct", 0),
                "files": [os.path.basename(p) for p in produced if os.path.exists(p)]}
    except Exception as e:  # non-blocking (spec §5)
        log(f"BRIEF_RENDER_SKIPPED: {type(e).__name__}: {e}")
        return {"status": "SKIPPED", "reason": f"{type(e).__name__}: {e}", "files": []}


if __name__ == "__main__":
    import sys
    pkg = sys.argv[1] if len(sys.argv) > 1 else "."
    tier = sys.argv[2] if len(sys.argv) > 2 else "standard"
    emit(render_brief(pkg, tier, logger=emit))

def fig_rggmci_rescue(pairs_csv, png_path, strain_label, plt):
    """PDF-013: Fragment rescue summary figure.

    Reads the *_4A_RGGMCI_ranked_pairs.csv from the sealed package and renders
    a horizontal bar chart of the top shared-reference rescue pairs, color-coded
    by confidence tier (HIGH = green, MODERATE = amber).
    Claim-safety: all pairs labelled as homology-guided linkage, not confirmed joins.
    """
    import csv as _csv
    rows = []
    try:
        with open(pairs_csv, newline="") as f:
            for r in _csv.DictReader(f):
                rows.append(r)
    except Exception:
        return None
    if not rows:
        return None

    # Take top 12 by rggmci_score, split HIGH / MODERATE
    def _score(r):
        try: return float(r.get("rggmci_score", 0) or 0)
        except (ValueError, TypeError): return 0.0

    rows = sorted(rows, key=_score, reverse=True)[:12]
    labels = [f'{r["bgc_a"]}+{r["bgc_b"]}' for r in rows]
    scores = [_score(r) for r in rows]
    colors = [
        "#1a6b3a" if r.get("rggmci_confidence") == "HIGH_RG_GMCI_RESCUE"
        else "#d98a2b"
        for r in rows
    ]

    h = max(2.5, 0.35 * len(rows) + 1.0) + 0.7   # v9.7.87 Defect 2: +0.7 for the above-plot legend band
    fig, ax = plt.subplots(figsize=(8.4, h))
    y_pos = range(len(labels))
    ax.barh(list(y_pos), scores, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.invert_yaxis()
    # v9.7.87 Defect 2: legend was loc="lower right" (inside the data area, exactly where the
    # longest low-rank horizontal bars sit -> masked them) and the caption at y=-0.08 collided
    # with the x-axis title. Move the legend above the plot (horizontal), add right headroom so
    # no bar reaches the frame, and push the caption below the x-label with a reserved margin.
    ax.set_xlim(0, (max(scores) if scores else 1) * 1.12)            # right headroom
    ax.set_xlabel("RG-GMCI shared-reference score", fontsize=8, labelpad=6)
    ax.set_title(f"Fragment rescue candidates \u2014 {strain_label}", fontsize=9.5, pad=22)

    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor="#1a6b3a", label="HIGH_RG_GMCI_RESCUE"),
                       Patch(facecolor="#d98a2b", label="MODERATE_RG_GMCI_CANDIDATE")],
              fontsize=6.5, loc="lower center", bbox_to_anchor=(0.5, 1.01),
              ncol=2, framealpha=0.9, borderaxespad=0)
    fig.subplots_adjust(bottom=0.16, top=0.86)
    # caption below the x-label (LS-2 >=6pt, LS-3 y>=0.012 both satisfied); no tight_layout
    # (subplots_adjust + explicit figsize already reserve the margins; tight_layout fights them)
    fig.text(0.5, 0.03,
             "Homology-guided shared-reference linkage; not nucleotide-level joining.",
             ha="center", fontsize=6.0, color="grey", style="italic")

    fig.savefig(png_path, bbox_inches="tight")

    # Sidecar CSV (provenance row + headers + data)
    # v9.7.374 fix: same hard-killed-subprocess truncation hazard as the other sidecar CSVs
    # in this module; tmp-sibling + os.replace.
    import csv as _csv2
    _rescue_csv_path = png_path.replace(".png", "_data.csv")
    _rescue_csv_tmp = _rescue_csv_path + ".tmp"
    with open(_rescue_csv_tmp, "w", newline="") as f:
        w = _SafeWriter(f)
        w.writerow(["# provenance",
                     "Mamey deterministic Sapote figure; capacity-level; KCB=similarity not identity"])
        w.writerow(["pair", "bgc_a", "bgc_b", "rggmci_score", "rggmci_confidence",
                    "supporting_references", "good_geometry_references", "products_a", "products_b"])
        for r in rows:
            w.writerow([r.get("pair",""), r.get("bgc_a",""), r.get("bgc_b",""),
                        r.get("rggmci_score",""), r.get("rggmci_confidence",""),
                        r.get("supporting_references",""), r.get("good_geometry_references",""),
                        r.get("products_a",""), r.get("products_b","")])
    os.replace(_rescue_csv_tmp, _rescue_csv_path)
    return fig
