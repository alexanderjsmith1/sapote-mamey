"""collection_figures.py — Metadata-gated cross-strain collection figure bundle.

Figure-Bundle-Metadata-1 · v9.7.69

DESIGN
------
A FigureSpec registry declares each figure's required/optional fields and skip
conditions. Before any figure is rendered, normalize_metadata() maps common
column-name variants to canonical internal names. render_collection_figures()
then gates each figure against the normalized frame, renders eligible figures,
skips ineligible ones without error, and writes FIGURE_AVAILABILITY.md +
figure_manifest.csv into the figures/ subdirectory.

Claim-safety rules are enforced in captions and are not negotiable:
- "positive call" / "activity observation" — not "active strain" or "produces"
- KCB = similarity, not identity
- BGC scores = biosynthetic capacity, not production
- 16S < threshold = novelty-prioritization signal, not species description
- "Not tested" remains distinct from negative in all counts and figures

Layout-safety rules FB-1 through FB-9 are enforced:
  FB-1 Label density: min 7pt; top-N + "other" if >MAX_LABEL_ROWS
  FB-2 Top-N cap: 15 bars max; full data in CSV
  FB-3 Long names: word-wrap then truncate
  FB-4 Heatmap height: dynamic
  FB-5 Missing: visually distinct from zero
  FB-6 Provenance footer on every figure
  FB-7 Non-blocking skip
  FB-8 Export pair (PNG + CSV)
  FB-9 Stable lowercase filenames
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import datetime
import io
import math
import os
import textwrap
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi

try:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    _HAVE_MPL = True
except ImportError as _e:  # figure deps are optional; clear message, not a traceback (#35)
    _HAVE_MPL = False
    _MPL_ERR = str(_e)

    def _require_mpl():
        raise RuntimeError(
            "Figure generation needs matplotlib. Install the figures extra: "
            "`pip install -e '.[figures]'` (or `.[all]`). "
            f"(import error: {_MPL_ERR})")

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_BAR_ROWS   = 15       # FB-2: cap bar charts at this many categories
MIN_FONT_PT    = 7.0      # FB-1: never shrink below
MEGA_KB        = 100.0    # not used here but kept for cross-ref
LOW_16S_HARD   = 98.65    # % — species boundary threshold
LOW_16S_SOFT   = 99.0     # % — novelty-prioritization threshold
NOT_TESTED_VALUES = {"", "na", "n/a", "n.t.", "not tested", "nt", "unknown",
                     "not_tested", "none", "nd", "not done", "pending"}

# Colour palette (colour-blind accessible)
PAL = {
    "main":   "#2b7a4b",
    "accent": "#d98a2b",
    "muted":  "#888888",
    "miss":   "#dddddd",   # missing / not-tested cells (FB-5)
    "neg":    "#f0f0f0",   # true negative / zero
    "high":   "#1a6b3a",
    "low":    "#b03a3a",
    "ink":    "#1a1a1a",
}

# ── Metadata alias map ────────────────────────────────────────────────────────

_ALIASES: dict[str, list[str]] = {
    "strain_id":              ["strain", "strain_id", "isolate", "isolate_id",
                               "as_id", "sid", "sample_id", "id"],
    "genus":                  ["genus", "taxon_genus", "16s_genus", "assignment",
                               "genus_16s", "taxonomic_genus"],
    "host":                   ["host", "insect_host", "source_host", "host_category",
                               "insect", "host_organism", "host_species"],
    "source":                 ["source", "dataset", "project", "collection",
                               "source_dataset", "habitat_group", "group"],
    "location":               ["location", "site", "collection_site", "region",
                               "geography", "state", "province", "country"],
    "collection_date":        ["date", "collection_date", "collected",
                               "collection_year", "year", "sample_date"],
    "candida_call":           ["candida", "candida_call", "candida_positive",
                               "ca_inhibition", "candida_hit", "ca_call",
                               "candida_active", "ca_positive"],
    "candida_tested":         ["candida_tested", "ca_tested", "candida_assayed"],
    "mrsa_call":              ["mrsa", "mrsa_call", "mrsa_positive", "mrsa_inhibition",
                               "mrsa_hit", "mrsa_active", "sa_call"],
    "mrsa_tested":            ["mrsa_tested", "sa_tested", "mrsa_assayed"],
    "closest_type_similarity":["closest_type_similarity", "similarity", "pct_identity",
                               "16s_similarity", "type_similarity", "16s_pct",
                               "closest_pct", "identity_pct"],
    "closest_type_strain":    ["closest_type_strain", "nearest_type", "closest_type",
                               "type_strain", "closest_strain", "type_match"],
    "accession":              ["genbank_accession", "accession", "16s_accession",
                               "gb_accession", "ncbi_accession"],
    "genome_mined":           ["genome_mined", "mamey_run", "sapote_run",
                               "antismash_available", "genome_sequenced",
                               "wgs_available"],
    "priority":               ["priority", "followup_priority", "candidate",
                               "lead_status", "follow_up", "followup"],
    "in_vivo":                ["in_vivo", "animal_model", "in_vivo_tested"],
    "chemistry_done":         ["chemistry_done", "chemistry", "fractionated",
                               "chemical_characterization"],
}


# ── FigureSpec registry ───────────────────────────────────────────────────────

@dataclass
class FigureSpec:
    figure_id:   str
    title:       str
    description: str                       # one sentence — shown in availability report
    required:    list[str]                 # canonical field names
    optional:    list[str] = field(default_factory=list)
    min_rows:    int = 2                   # minimum rows after filtering NaN
    multi_source_required: bool = False    # True = skip if <2 distinct source values
    output_stem: str = ""                  # auto-set from figure_id if empty

    def __post_init__(self):
        if not self.output_stem:
            self.output_stem = self.figure_id

    @property
    def output_png(self):
        return self.output_stem + ".png"

    @property
    def output_csv(self):
        return self.output_stem + "_data.csv"

    def example_header(self) -> str:
        cols = ["strain_id"] + [c for c in self.required if c != "strain_id"]
        return "strain_id," + ",".join(c for c in cols if c != "strain_id")


FIGURE_REGISTRY: list[FigureSpec] = [
    FigureSpec("fig_collection_overview",
               "Collection overview",
               "Summary panel: total strains, genera, hosts, locations, active strains, and low-16S candidates.",
               required=["strain_id"],
               optional=["genus","host","location","candida_call","mrsa_call",
                          "closest_type_similarity","source"],
               min_rows=1),
    FigureSpec("fig_top_genera",
               "Top genera",
               "Ranked bar chart of genus counts across the collection.",
               required=["strain_id","genus"],
               optional=["source"]),
    FigureSpec("fig_shared_unique_genera",
               "Shared and unique genera by source",
               "Venn-style count comparison of genus overlap between collection sources.",
               required=["strain_id","genus","source"],
               multi_source_required=True),
    FigureSpec("fig_genus_relative_abundance",
               "Genus relative abundance by source",
               "Stacked proportional bar chart comparing relative genus enrichment per source.",
               required=["strain_id","genus","source"],
               multi_source_required=True),
    FigureSpec("fig_candida_counts",
               "Candida activity — tested and positive counts",
               "Bar chart of strains tested and strains with Candida inhibition calls.",
               required=["strain_id","candida_tested","candida_call"],
               optional=["source","host","genus"]),
    FigureSpec("fig_mrsa_counts",
               "MRSA activity — tested and positive counts",
               "Bar chart of strains tested and strains with MRSA inhibition calls.",
               required=["strain_id","mrsa_tested","mrsa_call"],
               optional=["source","host","genus"]),
    FigureSpec("fig_activity_rate",
               "Activity rate by assay",
               "Proportion positive for Candida and/or MRSA assays; reduced plot if only one assay present.",
               required=["strain_id"],
               optional=["candida_call","mrsa_call","source","host","genus"],
               min_rows=1),
    FigureSpec("fig_activity_pattern",
               "Activity pattern — co-inhibition quadrant",
               "Four-quadrant count: no positive / Candida-only / MRSA-only / both assays positive.",
               required=["strain_id","candida_call","mrsa_call"],
               optional=["source"]),
    FigureSpec("fig_genus_source_matrix",
               "Genus-by-source count matrix",
               "Heatmap of genus × source counts across the collection.",
               required=["strain_id","genus","source"],
               multi_source_required=True),
    FigureSpec("fig_genus_activity_heatmap",
               "Genus activity heatmap",
               "Activity rate (positive calls / tested) per genus and source.",
               required=["strain_id","genus","source"],
               optional=["candida_call","mrsa_call","candida_tested","mrsa_tested"]),
    FigureSpec("fig_16s_similarity_dist",
               "16S similarity distribution",
               "Histogram of closest-type-strain 16S similarity across the collection.",
               required=["strain_id","closest_type_similarity"],
               optional=["source","genus"]),
    FigureSpec("fig_low_16s_rate",
               "Low-16S novelty candidate rate",
               "Proportion of strains below 99% and 98.65% 16S similarity thresholds.",
               required=["strain_id","closest_type_similarity"],
               optional=["source"]),
    FigureSpec("fig_activity_vs_16s",
               "Activity vs 16S similarity prioritization scatter",
               "Scatter plot of 16S similarity vs activity call; high-priority candidates labeled.",
               required=["strain_id","closest_type_similarity"],
               optional=["candida_call","mrsa_call","source","genus","priority"]),
    FigureSpec("fig_top_hosts",
               "Top hosts",
               "Ranked bar chart of host/source-organism counts across the collection.",
               required=["strain_id","host"],
               optional=["source"]),
    FigureSpec("fig_top_locations",
               "Top collection locations",
               "Ranked bar chart of collection site/location counts.",
               required=["strain_id","location"],
               optional=["source"]),
    FigureSpec("fig_accession_coverage",
               "GenBank/accession coverage",
               "Bar chart of strains with and without deposited accession IDs.",
               required=["strain_id","accession"],
               optional=["source","genus"]),
    FigureSpec("fig_collection_timeline",
               "Collection timeline",
               "Strains collected per year or date, coloured by source if available.",
               required=["strain_id","collection_date"],
               optional=["source","location"]),
    FigureSpec("fig_closest_type_strains",
               "Closest type strains",
               "Ranked bar chart of the most-matched type-strain assignments.",
               required=["strain_id","closest_type_strain"],
               optional=["genus","closest_type_similarity"]),
    FigureSpec("fig_followup_candidates",
               "Follow-up candidate summary",
               "Count of strains flagged as active, genome-mined, in-vivo tested, chemistry-done, or priority.",
               required=["strain_id"],
               optional=["candida_call","mrsa_call","genome_mined","in_vivo",
                          "chemistry_done","priority","genus","source","host"],
               min_rows=1),
    FigureSpec("fig_non_streptomyces",
               "Non-Streptomyces genera focus panel",
               "Counts of rare-genus strains with any activity call or biosynthetic capacity.",
               required=["strain_id","genus"],
               optional=["source","host","candida_call","mrsa_call"]),
]


# ── Metadata normalization ─────────────────────────────────────────────────────

def normalize_metadata(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Map column-name variants to canonical names. Returns (normalized_rows, warnings).

    Rules:
    - Canonical name wins if present.
    - First matching alias is used if canonical absent.
    - Ambiguous (multiple aliases for same canonical) → warning, first-seen used.
    - Original column names are preserved as _orig_<canonical> for provenance.
    - Never infers missing values.
    """
    if not rows:
        return [], []
    warns: list[str] = []
    all_cols = set(rows[0].keys())
    col_lower = {c.lower(): c for c in all_cols}

    mapping: dict[str, str] = {}   # canonical → actual_col_in_rows
    for canonical, aliases in _ALIASES.items():
        hits = []
        if canonical in all_cols:
            mapping[canonical] = canonical
            continue
        for alias in aliases:
            if alias.lower() in col_lower:
                hits.append(col_lower[alias.lower()])
        if len(hits) == 1:
            mapping[canonical] = hits[0]
        elif len(hits) > 1:
            warns.append(
                f"Ambiguous alias for '{canonical}': {hits} — using '{hits[0]}'")
            mapping[canonical] = hits[0]
        # else: not present — skip

    normalized = []
    for row in rows:
        nr: dict[str, Any] = {}
        for k, v in row.items():
            nr[k] = v  # preserve original columns
        for canonical, src_col in mapping.items():
            if canonical not in nr:
                nr[canonical] = row.get(src_col, "")
            # Preserve original column name for provenance
            nr[f"_orig_{canonical}"] = src_col if src_col != canonical else canonical
        normalized.append(nr)

    return normalized, warns


def _has_field(rows: list[dict], field: str) -> bool:
    """True if the field is present and at least one row has a non-blank value."""
    return any(_val(r, field) for r in rows)


def _val(row: dict, field: str) -> str:
    """Return stripped string value, empty string for blanks."""
    v = row.get(field, "")
    return "" if v is None else str(v).strip()


def _is_not_tested(v: str) -> bool:
    return v.lower() in NOT_TESTED_VALUES


def _is_positive(v: str) -> bool:
    """True for explicit positive calls only. NOT_TESTED and blank are not positive."""
    if _is_not_tested(v):
        return False
    return v.lower() in {"1", "yes", "true", "positive", "pos", "+", "active", "hit"}


def _is_negative(v: str) -> bool:
    """True for explicit negative calls. NOT_TESTED is NOT negative."""
    if _is_not_tested(v):
        return False
    return v.lower() in {"0", "no", "false", "negative", "neg", "-", "inactive", "miss"}


def _sources_count(rows: list[dict]) -> int:
    return len({_val(r, "source") for r in rows if _val(r, "source")})


# ── Layout helpers ────────────────────────────────────────────────────────────

def _wrap(label: str, width: int = 22) -> str:
    """FB-3: word-wrap then truncate. Never shrink font."""
    lines = textwrap.wrap(str(label), width=width, break_long_words=False)
    if not lines:
        return str(label)[:width]
    result = "\n".join(lines[:2])
    if len(lines) > 2:
        result = result.rsplit("\n", 1)[0] + "…"
    return result


def _dynamic_height(n_rows: int, row_pitch: float = 0.38, base: float = 1.8) -> float:
    """FB-1/FB-4: compute figure height so pitch stays readable."""
    return max(3.0, min(base + row_pitch * n_rows, 14.0))


def _prov_footer(ax, source_name: str, n: int, version: str, date_str: str) -> None:
    """FB-6: small provenance footer on every figure."""
    txt = (f"Source: {source_name or 'supplied metadata'} · n={n} strains · "
           f"Sapote–Mamey {version} · {date_str} · "
           "Claim-safe: activity=observation; capacity≠production; KCB=similarity not identity")
    _fs = max(6.0, MIN_FONT_PT - 0.5)  # LS-8: respect module constant floor
    ax.figure.text(0.01, 0.014, txt, fontsize=_fs, color=PAL["muted"],
                   va="bottom", wrap=True)  # LS-3: y≥0.012


def _write_sidecar(png_path: str, header: list[str], rows: list[list]) -> None:
    """FB-8: write provenance-compliant _data.csv alongside figure."""
    csv_path = png_path.replace(".png", "_data.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = _SafeWriter(f)
        w.writerow(["# provenance",
                    "Mamey collection figure; capacity-level; KCB=similarity not identity"])
        w.writerow(header)
        w.writerows(rows)


def _save(fig, png_path: str) -> None:
    fig.savefig(png_path, bbox_inches="tight", dpi=_safe_dpi(fig, 160))
    plt.close(fig)


# ── Figure generators ─────────────────────────────────────────────────────────

def _gen_collection_overview(rows, out_dir, meta, version, date_str) -> str:
    """Collection overview panel — reduced if optional fields absent."""
    cats: dict[str, Any] = {"Total strains": len(rows)}
    if _has_field(rows, "genus"):
        cats["Genera"] = len({_val(r, "genus") for r in rows if _val(r, "genus")})
    if _has_field(rows, "host"):
        cats["Hosts"] = len({_val(r, "host") for r in rows if _val(r, "host")})
    if _has_field(rows, "location"):
        cats["Locations"] = len({_val(r, "location") for r in rows if _val(r, "location")})
    if _has_field(rows, "candida_call"):
        cats["Candida positive"] = sum(1 for r in rows if _is_positive(_val(r, "candida_call")))
    if _has_field(rows, "mrsa_call"):
        cats["MRSA positive"] = sum(1 for r in rows if _is_positive(_val(r, "mrsa_call")))
    if _has_field(rows, "closest_type_similarity"):
        cats[f"<{LOW_16S_SOFT}% 16S (novel priority)"] = sum(
            1 for r in rows if _val(r, "closest_type_similarity")
            and not _is_not_tested(_val(r, "closest_type_similarity"))
            and float(_val(r, "closest_type_similarity")) < LOW_16S_SOFT)

    n = len(cats)
    fig, ax = plt.subplots(figsize=(7.0, max(2.5, 0.45 * n + 1.2)))
    labels = list(cats.keys()); vals = list(cats.values())
    bars = ax.barh(labels, vals, color=PAL["main"], edgecolor="white", linewidth=0.5)
    ax.bar_label(bars, padding=3, fontsize=8.5, color=PAL["ink"])
    ax.set_xlabel("Count", fontsize=8)
    ax.set_title("Collection overview", fontsize=10, fontweight="bold")
    ax.set_xlim(0, max(vals) * 1.18)
    ax.tick_params(axis="y", labelsize=MIN_FONT_PT + 0.5)
    _prov_footer(ax, meta.get("source_file", ""), len(rows), version, date_str)
    png = os.path.join(out_dir, "fig_collection_overview.png")
    _write_sidecar(png, ["category", "count"], [[k, v] for k, v in cats.items()])
    _save(fig, png); return png


def _gen_top_genera(rows, out_dir, meta, version, date_str) -> str:
    from collections import Counter
    counts = Counter(_val(r, "genus") for r in rows if _val(r, "genus"))
    top = counts.most_common(MAX_BAR_ROWS)
    n_other = sum(v for k, v in counts.items() if k not in dict(top))
    if n_other:
        top.append(("other", n_other))
    labels = [_wrap(k) for k, _ in top]; vals = [v for _, v in top]
    h = _dynamic_height(len(labels))
    fig, ax = plt.subplots(figsize=(7.0, h))
    ax.barh(labels[::-1], vals[::-1], color=PAL["main"], edgecolor="white", linewidth=0.4)
    ax.set_xlabel("Strain count", fontsize=8)
    ax.set_title("Top genera", fontsize=10, fontweight="bold")
    ax.tick_params(axis="y", labelsize=MIN_FONT_PT)
    _prov_footer(ax, meta.get("source_file", ""), len(rows), version, date_str)
    png = os.path.join(out_dir, "fig_top_genera.png")
    _write_sidecar(png, ["genus", "count"], [[k, v] for k, v in top])
    _save(fig, png); return png


def _gen_shared_unique_genera(rows, out_dir, meta, version, date_str) -> str:
    from collections import defaultdict
    src_genera: dict[str, set] = defaultdict(set)
    for r in rows:
        s = _val(r, "source"); g = _val(r, "genus")
        if s and g:
            src_genera[s].add(g)
    sources = sorted(src_genera.keys())[:8]
    all_g = set.union(*[src_genera[s] for s in sources]) if sources else set()
    shared = set.intersection(*[src_genera[s] for s in sources]) if sources else set()
    unique_per = {s: src_genera[s] - set.union(*[src_genera[t] for t in sources if t != s])
                  for s in sources}
    cats = [f"{s} total" for s in sources] + ["Shared all"] + [f"{s} unique" for s in sources]
    vals = ([len(src_genera[s]) for s in sources] + [len(shared)] +
            [len(unique_per[s]) for s in sources])
    colors = ([PAL["main"]] * len(sources) + [PAL["accent"]] +
              [PAL["muted"]] * len(sources))
    h = _dynamic_height(len(cats))
    fig, ax = plt.subplots(figsize=(7.0, h))
    wrapped = [_wrap(c) for c in cats]
    ax.barh(wrapped[::-1], vals[::-1], color=colors[::-1], edgecolor="white", linewidth=0.4)
    ax.set_xlabel("Genus count", fontsize=8)
    ax.set_title("Shared and unique genera by source", fontsize=10, fontweight="bold")
    ax.tick_params(axis="y", labelsize=MIN_FONT_PT)
    _prov_footer(ax, meta.get("source_file", ""), len(rows), version, date_str)
    png = os.path.join(out_dir, "fig_shared_unique_genera.png")
    csv_rows = list(zip(cats, vals))
    _write_sidecar(png, ["category", "count"], csv_rows)
    _save(fig, png); return png


def _gen_genus_relative_abundance(rows, out_dir, meta, version, date_str) -> str:
    from collections import Counter, defaultdict
    src_gen: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        s = _val(r, "source"); g = _val(r, "genus")
        if s and g:
            src_gen[s][g] += 1
    sources = sorted(src_gen.keys())[:8]
    all_genera = sorted({g for s in sources for g in src_gen[s]},
                        key=lambda g: -sum(src_gen[s][g] for s in sources))[:MAX_BAR_ROWS]
    cmap = plt.get_cmap("tab20", len(all_genera))
    fig, ax = plt.subplots(figsize=(8.0, max(3.0, 0.55 * len(sources) + 1.5)))
    bottoms = [0.0] * len(sources)
    patches = []
    for gi, genus in enumerate(all_genera):
        vals = [src_gen[s][genus] / max(sum(src_gen[s].values()), 1) for s in sources]
        ax.barh(sources, vals, left=bottoms, color=cmap(gi), label=_wrap(genus, 18))
        bottoms = [b + v for b, v in zip(bottoms, vals)]
        patches.append(mpatches.Patch(color=cmap(gi), label=genus[:20]))
    ax.set_xlabel("Relative proportion", fontsize=8)
    ax.set_title("Genus relative abundance by source", fontsize=10, fontweight="bold")
    ax.set_xlim(0, 1.05)
    ax.tick_params(axis="y", labelsize=MIN_FONT_PT)
    ax.legend(handles=patches, fontsize=6.5, loc="lower right",
              bbox_to_anchor=(1.22, 0), ncol=1, framealpha=0.8)
    fig.tight_layout(rect=[0, 0, 0.82, 1])
    _prov_footer(ax, meta.get("source_file", ""), len(rows), version, date_str)
    png = os.path.join(out_dir, "fig_genus_relative_abundance.png")
    csv_rows = [[genus] + [src_gen[s][genus] for s in sources]
                for genus in all_genera]
    _write_sidecar(png, ["genus"] + sources, csv_rows)
    _save(fig, png); return png


def _gen_activity_counts(rows, out_dir, meta, version, date_str,
                         assay: str, tested_field: str, fig_id: str, title: str) -> str:
    tested = sum(1 for r in rows if _is_positive(_val(r, tested_field))
                 or _val(r, tested_field).lower() in {"1","yes","true","tested"})
    positive = sum(1 for r in rows if _is_positive(_val(r, assay)))
    not_tested = sum(1 for r in rows if _is_not_tested(_val(r, assay)))
    cats = ["Tested", "Positive calls", "Not tested / unknown"]
    vals = [tested, positive, not_tested]
    colors = [PAL["muted"], PAL["main"], PAL["miss"]]
    fig, ax = plt.subplots(figsize=(5.5, 2.8))
    bars = ax.bar(cats, vals, color=colors, edgecolor="white", linewidth=0.5, width=0.55)
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_ylabel("Strain count", fontsize=8)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.tick_params(axis="x", labelsize=MIN_FONT_PT + 0.5)
    _prov_footer(ax, meta.get("source_file", ""), len(rows), version, date_str)
    png = os.path.join(out_dir, f"{fig_id}.png")
    _write_sidecar(png, ["category", "count"], list(zip(cats, vals)))
    _save(fig, png); return png


def _gen_activity_rate(rows, out_dir, meta, version, date_str) -> str:
    """Reduced if only one assay present."""
    has_ca = _has_field(rows, "candida_call")
    has_mr = _has_field(rows, "mrsa_call")
    assays, rates = [], []
    n_valid = len(rows)
    if has_ca:
        tested = [r for r in rows if not _is_not_tested(_val(r, "candida_call"))]
        pos = sum(1 for r in tested if _is_positive(_val(r, "candida_call")))
        if tested:
            assays.append("Candida activity rate"); rates.append(pos / len(tested))
    if has_mr:
        tested = [r for r in rows if not _is_not_tested(_val(r, "mrsa_call"))]
        pos = sum(1 for r in tested if _is_positive(_val(r, "mrsa_call")))
        if tested:
            assays.append("MRSA activity rate"); rates.append(pos / len(tested))
    if has_ca and has_mr:
        either = [r for r in rows
                  if not _is_not_tested(_val(r, "candida_call"))
                  and not _is_not_tested(_val(r, "mrsa_call"))]
        pos = sum(1 for r in either
                  if _is_positive(_val(r, "candida_call")) or _is_positive(_val(r, "mrsa_call")))
        if either:
            assays.append("Either assay"); rates.append(pos / len(either))
    if not assays:
        return ""
    fig, ax = plt.subplots(figsize=(5.5, 3.0))
    bars = ax.bar(assays, [r * 100 for r in rates],
                  color=PAL["main"], edgecolor="white", linewidth=0.5, width=0.5)
    ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=9)
    ax.set_ylabel("% positive (of tested)", fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_title("Activity rate by assay (positive calls / tested — not-tested excluded)",
                 fontsize=9, fontweight="bold")
    ax.tick_params(axis="x", labelsize=MIN_FONT_PT + 0.5)
    _prov_footer(ax, meta.get("source_file", ""), n_valid, version, date_str)
    png = os.path.join(out_dir, "fig_activity_rate.png")
    _write_sidecar(png, ["assay", "rate_pct"],
                   [[a, round(r * 100, 2)] for a, r in zip(assays, rates)])
    _save(fig, png); return png


def _gen_activity_pattern(rows, out_dir, meta, version, date_str) -> str:
    ca = [_val(r, "candida_call") for r in rows]
    mr = [_val(r, "mrsa_call") for r in rows]
    nn = sum(1 for c, m in zip(ca, mr)
             if not _is_positive(c) and not _is_positive(m)
             and not (_is_not_tested(c) and _is_not_tested(m)))
    co = sum(1 for c, m in zip(ca, mr) if _is_positive(c) and not _is_positive(m))
    mo = sum(1 for c, m in zip(ca, mr) if not _is_positive(c) and _is_positive(m))
    bo = sum(1 for c, m in zip(ca, mr) if _is_positive(c) and _is_positive(m))
    nt = sum(1 for c, m in zip(ca, mr) if _is_not_tested(c) and _is_not_tested(m))
    cats = ["Neither positive", "Candida only", "MRSA only",
            "Both positive", "Not tested / unknown"]
    vals = [nn, co, mo, bo, nt]
    colors = [PAL["neg"], PAL["accent"], PAL["main"], PAL["high"], PAL["miss"]]
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    bars = ax.bar(cats, vals, color=colors, edgecolor="white", linewidth=0.5, width=0.6)
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_ylabel("Strain count", fontsize=8)
    ax.set_title("Activity pattern (positive call observations; not-tested excluded from positive counts)",
                 fontsize=8.5, fontweight="bold")
    ax.tick_params(axis="x", labelsize=MIN_FONT_PT)
    _prov_footer(ax, meta.get("source_file", ""), len(rows), version, date_str)
    png = os.path.join(out_dir, "fig_activity_pattern.png")
    _write_sidecar(png, ["category", "count"], list(zip(cats, vals)))
    _save(fig, png); return png


def _gen_genus_source_matrix(rows, out_dir, meta, version, date_str) -> str:
    import numpy as np
    from collections import Counter
    src_gen: dict[str, Counter] = {}
    for r in rows:
        s = _val(r, "source"); g = _val(r, "genus")
        if s and g:
            src_gen.setdefault(s, Counter())[g] += 1
    sources = sorted(src_gen.keys())[:10]
    all_g = sorted({g for s in sources for g in src_gen[s]},
                   key=lambda g: -sum(src_gen.get(s, {}).get(g, 0) for s in sources))[:MAX_BAR_ROWS]
    mat = np.array([[src_gen.get(s, {}).get(g, 0) for s in sources] for g in all_g])
    h = _dynamic_height(len(all_g), 0.42)  # FB-4
    fig, ax = plt.subplots(figsize=(max(5.0, 1.1 * len(sources)), h))
    im = ax.imshow(mat, aspect="auto", cmap="YlGn", interpolation="nearest")
    ax.set_xticks(range(len(sources))); ax.set_xticklabels([_wrap(s, 16) for s in sources],
                                                            fontsize=MIN_FONT_PT, rotation=30, ha="right")
    ax.set_yticks(range(len(all_g))); ax.set_yticklabels([_wrap(g, 22) for g in all_g],
                                                          fontsize=MIN_FONT_PT)
    for i in range(len(all_g)):
        for j in range(len(sources)):
            v = mat[i, j]
            if v > 0:
                ax.text(j, i, str(v), ha="center", va="center", fontsize=6.5,
                        color="white" if v > mat.max() * 0.6 else PAL["ink"])
    fig.colorbar(im, ax=ax, shrink=0.6, label="Strain count")
    ax.set_title("Genus × source count matrix", fontsize=10, fontweight="bold")
    _prov_footer(ax, meta.get("source_file", ""), len(rows), version, date_str)
    png = os.path.join(out_dir, "fig_genus_source_matrix.png")
    csv_rows = [[g] + [int(src_gen.get(s, {}).get(g, 0)) for s in sources] for g in all_g]
    _write_sidecar(png, ["genus"] + sources, csv_rows)
    _save(fig, png); return png


def _gen_16s_dist(rows, out_dir, meta, version, date_str) -> str:
    vals = []
    for r in rows:
        v = _val(r, "closest_type_similarity")
        if v and not _is_not_tested(v):
            try: vals.append(float(v))
            except ValueError: continue
    if not vals:
        return ""
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    ax.hist(vals, bins=30, color=PAL["main"], edgecolor="white", linewidth=0.5)
    for thresh, col, lab in [(LOW_16S_HARD, PAL["low"], f"{LOW_16S_HARD}%"),
                              (LOW_16S_SOFT, PAL["accent"], f"{LOW_16S_SOFT}%")]:
        ax.axvline(thresh, color=col, lw=1.4, ls="--", label=lab)
    ax.set_xlabel("Closest type-strain 16S similarity (%)", fontsize=8)
    ax.set_ylabel("Strain count", fontsize=8)
    ax.set_title("16S similarity distribution — novelty prioritization signal (similarity ≠ species assignment)",
                 fontsize=8.5, fontweight="bold")
    ax.legend(fontsize=7)
    _prov_footer(ax, meta.get("source_file", ""), len(vals), version, date_str)
    png = os.path.join(out_dir, "fig_16s_similarity_dist.png")
    _write_sidecar(png, ["closest_type_similarity_pct"], [[v] for v in sorted(vals)])
    _save(fig, png); return png


def _gen_low_16s_rate(rows, out_dir, meta, version, date_str) -> str:
    vals = []
    for r in rows:
        v = _val(r, "closest_type_similarity")
        if v and not _is_not_tested(v):
            try: vals.append(float(v))
            except ValueError: continue
    if not vals:
        return ""
    n = len(vals)
    threshs = [LOW_16S_SOFT, LOW_16S_HARD]
    labels = [f"<{t}%" for t in threshs]
    counts = [sum(1 for v in vals if v < t) for t in threshs]
    pcts = [c / n * 100 for c in counts]
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    bars = ax.bar(labels, pcts, color=[PAL["accent"], PAL["low"]],
                  edgecolor="white", linewidth=0.5, width=0.45)
    for bar, c in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + 0.8, f"n={c}", ha="center", fontsize=9)
    ax.bar_label(bars, fmt="%.1f%%", padding=12, fontsize=9)
    ax.set_ylabel("% of strains with 16S data", fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_title("Low-16S novelty candidate rate\n(16S threshold = prioritization signal; not a species boundary)",
                 fontsize=8.5, fontweight="bold")
    _prov_footer(ax, meta.get("source_file", ""), n, version, date_str)
    png = os.path.join(out_dir, "fig_low_16s_rate.png")
    _write_sidecar(png, ["threshold", "count", "pct"],
                   list(zip(labels, counts, [round(p, 2) for p in pcts])))
    _save(fig, png); return png


def _gen_activity_vs_16s(rows, out_dir, meta, version, date_str) -> str:
    pts = []
    for r in rows:
        v = _val(r, "closest_type_similarity")
        if not v or _is_not_tested(v):
            continue
        try:
            sim = float(v)
        except ValueError:
            continue
        ca = _is_positive(_val(r, "candida_call"))
        mr = _is_positive(_val(r, "mrsa_call"))
        act = ca or mr
        pts.append({"strain": _val(r, "strain_id"), "sim": sim, "active": act,
                    "source": _val(r, "source"), "priority": _val(r, "priority")})
    if not pts:
        return ""
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    for act, col, lab in [(True, PAL["main"], "Activity observed"),
                           (False, PAL["muted"], "No activity / not tested")]:
        subset = [p for p in pts if p["active"] == act]
        ax.scatter([p["sim"] for p in subset], range(len(subset)),
                   c=col, s=25, alpha=0.7, label=lab, edgecolors="none")
    ax.set_xlabel("Closest type-strain 16S similarity (%)", fontsize=8)
    ax.set_ylabel("Strains (each point = one strain)", fontsize=8)
    for thresh, col in [(LOW_16S_HARD, PAL["low"]), (LOW_16S_SOFT, PAL["accent"])]:
        ax.axvline(thresh, color=col, lw=1.2, ls="--", alpha=0.7, label=f"{thresh}% threshold")
    ax.set_title("Activity observation vs 16S similarity\n"
                 "(activity = extract-level observation; 16S = novelty-prioritization signal)",
                 fontsize=8.5, fontweight="bold")
    ax.legend(fontsize=7)
    _prov_footer(ax, meta.get("source_file", ""), len(pts), version, date_str)
    png = os.path.join(out_dir, "fig_activity_vs_16s.png")
    _write_sidecar(png, ["strain_id", "closest_type_similarity_pct", "activity_observed", "source"],
                   [[p["strain"], p["sim"], int(p["active"]), p["source"]] for p in pts])
    _save(fig, png); return png


def _gen_simple_bar(rows, out_dir, field_name, fig_id, title, xlabel,
                    meta, version, date_str) -> str:
    from collections import Counter
    counts = Counter(_val(r, field_name) for r in rows if _val(r, field_name))
    top = counts.most_common(MAX_BAR_ROWS)
    n_other = sum(v for k, v in counts.items() if k not in dict(top))
    if n_other:
        top.append(("other", n_other))
    labels = [_wrap(k) for k, _ in top]; vals = [v for _, v in top]
    h = _dynamic_height(len(labels))
    fig, ax = plt.subplots(figsize=(7.0, h))
    ax.barh(labels[::-1], vals[::-1], color=PAL["main"], edgecolor="white", linewidth=0.4)
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.tick_params(axis="y", labelsize=MIN_FONT_PT)
    _prov_footer(ax, meta.get("source_file", ""), len(rows), version, date_str)
    png = os.path.join(out_dir, f"{fig_id}.png")
    _write_sidecar(png, [field_name, "count"], [[k, v] for k, v in top])
    _save(fig, png); return png


def _gen_accession_coverage(rows, out_dir, meta, version, date_str) -> str:
    has_acc = sum(1 for r in rows if _val(r, "accession") and
                  not _is_not_tested(_val(r, "accession")))
    no_acc = len(rows) - has_acc
    cats = ["Has accession ID", "No accession / pending"]
    vals = [has_acc, no_acc]
    colors = [PAL["main"], PAL["miss"]]
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    bars = ax.bar(cats, vals, color=colors, edgecolor="white", linewidth=0.5, width=0.45)
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_ylabel("Strain count", fontsize=8)
    ax.set_title("GenBank / accession coverage", fontsize=10, fontweight="bold")
    ax.tick_params(axis="x", labelsize=MIN_FONT_PT + 0.5)
    _prov_footer(ax, meta.get("source_file", ""), len(rows), version, date_str)
    png = os.path.join(out_dir, "fig_accession_coverage.png")
    _write_sidecar(png, ["category", "count"], list(zip(cats, vals)))
    _save(fig, png); return png


def _gen_collection_timeline(rows, out_dir, meta, version, date_str) -> str:
    from collections import Counter
    years = []
    for r in rows:
        v = _val(r, "collection_date")
        if not v or _is_not_tested(v):
            continue
        for part in str(v).split("-"):
            try:
                yr = int(part.strip())
                if 1950 <= yr <= datetime.date.today().year + 1:
                    years.append(yr); break
            except ValueError:
                continue
    if not years:
        return ""
    counts = Counter(years)
    yr_range = sorted(counts.keys())
    fig, ax = plt.subplots(figsize=(max(6.0, len(yr_range) * 0.5 + 2.0), 3.5))
    ax.bar(yr_range, [counts[y] for y in yr_range],
           color=PAL["main"], edgecolor="white", linewidth=0.4)
    ax.set_xlabel("Collection year", fontsize=8)
    ax.set_ylabel("Strain count", fontsize=8)
    ax.set_title("Collection timeline", fontsize=10, fontweight="bold")
    ax.tick_params(axis="x", labelsize=MIN_FONT_PT, rotation=45)
    _prov_footer(ax, meta.get("source_file", ""), len(years), version, date_str)
    png = os.path.join(out_dir, "fig_collection_timeline.png")
    _write_sidecar(png, ["year", "count"], [[y, counts[y]] for y in yr_range])
    _save(fig, png); return png


def _gen_followup_candidates(rows, out_dir, meta, version, date_str) -> str:
    cats_vals = []
    if _has_field(rows, "candida_call"):
        cats_vals.append(("Candida positive", sum(1 for r in rows if _is_positive(_val(r, "candida_call")))))
    if _has_field(rows, "mrsa_call"):
        cats_vals.append(("MRSA positive", sum(1 for r in rows if _is_positive(_val(r, "mrsa_call")))))
    if _has_field(rows, "genome_mined"):
        cats_vals.append(("Genome mined", sum(1 for r in rows if _is_positive(_val(r, "genome_mined")))))
    if _has_field(rows, "in_vivo"):
        cats_vals.append(("In vivo tested", sum(1 for r in rows if _is_positive(_val(r, "in_vivo")))))
    if _has_field(rows, "chemistry_done"):
        cats_vals.append(("Chemistry done", sum(1 for r in rows if _is_positive(_val(r, "chemistry_done")))))
    if _has_field(rows, "priority"):
        cats_vals.append(("Priority flagged", sum(1 for r in rows if _is_positive(_val(r, "priority")))))
    if not cats_vals:
        return ""
    labels = [c for c, _ in cats_vals]; vals = [v for _, v in cats_vals]
    fig, ax = plt.subplots(figsize=(6.5, max(2.8, 0.45 * len(labels) + 1.2)))
    bars = ax.barh(labels[::-1], vals[::-1], color=PAL["main"], edgecolor="white", linewidth=0.4)
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xlabel("Strain count", fontsize=8)
    ax.set_title("Follow-up candidate summary\n(activity = extract-level observation; flags from supplied metadata)",
                 fontsize=8.5, fontweight="bold")
    ax.tick_params(axis="y", labelsize=MIN_FONT_PT + 0.5)
    _prov_footer(ax, meta.get("source_file", ""), len(rows), version, date_str)
    png = os.path.join(out_dir, "fig_followup_candidates.png")
    _write_sidecar(png, ["category", "count"], cats_vals)
    _save(fig, png); return png


def _gen_non_streptomyces(rows, out_dir, meta, version, date_str) -> str:
    from collections import Counter
    non_strep = [r for r in rows
                 if _val(r, "genus") and "streptomyces" not in _val(r, "genus").lower()]
    if not non_strep:
        return ""
    counts = Counter(_val(r, "genus") for r in non_strep if _val(r, "genus"))
    top = counts.most_common(MAX_BAR_ROWS)
    labels = [_wrap(k) for k, _ in top]; vals = [v for _, v in top]
    h = _dynamic_height(len(labels))
    fig, ax = plt.subplots(figsize=(7.0, h))
    ax.barh(labels[::-1], vals[::-1], color=PAL["accent"], edgecolor="white", linewidth=0.4)
    ax.set_xlabel("Strain count", fontsize=8)
    ax.set_title("Non-Streptomyces genera (rare-genus focus panel)", fontsize=10, fontweight="bold")
    ax.tick_params(axis="y", labelsize=MIN_FONT_PT)
    _prov_footer(ax, meta.get("source_file", ""), len(non_strep), version, date_str)
    png = os.path.join(out_dir, "fig_non_streptomyces.png")
    _write_sidecar(png, ["genus", "count"], [[k, v] for k, v in top])
    _save(fig, png); return png


# ── Dispatch table ────────────────────────────────────────────────────────────

_GENERATORS: dict[str, Any] = {
    "fig_collection_overview":      _gen_collection_overview,
    "fig_top_genera":               _gen_top_genera,
    "fig_shared_unique_genera":     _gen_shared_unique_genera,
    "fig_genus_relative_abundance": _gen_genus_relative_abundance,
    "fig_candida_counts":     lambda rows,od,m,v,d: _gen_activity_counts(
        rows,od,m,v,d,"candida_call","candida_tested","fig_candida_counts",
        "Candida activity — tested and positive (observation, not compound identity)"),
    "fig_mrsa_counts":        lambda rows,od,m,v,d: _gen_activity_counts(
        rows,od,m,v,d,"mrsa_call","mrsa_tested","fig_mrsa_counts",
        "MRSA activity — tested and positive (observation, not compound identity)"),
    "fig_activity_rate":            _gen_activity_rate,
    "fig_activity_pattern":         _gen_activity_pattern,
    "fig_genus_source_matrix":      _gen_genus_source_matrix,
    # v9.7.374: fig_genus_activity_heatmap intentionally has no generator. It used to alias
    # straight to _gen_genus_source_matrix() — a raw genus x source STRAIN-COUNT matrix that
    # never reads candida_call/mrsa_call/candida_tested/mrsa_tested at all — while the
    # FigureSpec above (and FIGURE_AVAILABILITY.md) describes it as "Activity rate (positive
    # calls / tested) per genus and source". Both specs also share the SAME gate, so both fired
    # for real strain-metadata inputs and both calls returned the literal same
    # "fig_genus_source_matrix.png" path: the second GENERATED entry silently overwrote the
    # first's file with byte-identical content and _write_manifest_csv (which keys off
    # Path(p).stem, not spec.figure_id) collapsed both rows to figure_id
    # "fig_genus_source_matrix" in figure_manifest.csv — "fig_genus_activity_heatmap" never
    # appeared under its own name anywhere, so a reader who unlocked it by supplying
    # candida_call/mrsa_call got a mislabeled count matrix with zero activity-rate content and
    # no record it happened (tests/test_collection_figure_manifest.py already special-cases
    # this exact figure_id out of its "every registry figure appears in the manifest"
    # assertion). Leaving no generator here routes it through the existing, honest
    # "generator not implemented" skip path instead of a false GENERATED claim.
    "fig_16s_similarity_dist":      _gen_16s_dist,
    "fig_low_16s_rate":             _gen_low_16s_rate,
    "fig_activity_vs_16s":          _gen_activity_vs_16s,
    "fig_top_hosts":          lambda rows,od,m,v,d: _gen_simple_bar(
        rows,od,"host","fig_top_hosts","Top hosts","Strain count",m,v,d),
    "fig_top_locations":      lambda rows,od,m,v,d: _gen_simple_bar(
        rows,od,"location","fig_top_locations","Top collection locations","Strain count",m,v,d),
    "fig_accession_coverage":       _gen_accession_coverage,
    "fig_collection_timeline":      _gen_collection_timeline,
    "fig_closest_type_strains": lambda rows,od,m,v,d: _gen_simple_bar(
        rows,od,"closest_type_strain","fig_closest_type_strains",
        "Closest type strains","Strain count",m,v,d),
    "fig_followup_candidates":      _gen_followup_candidates,
    "fig_non_streptomyces":         _gen_non_streptomyces,
}


# ── Gate check ────────────────────────────────────────────────────────────────

def _check_gate(spec: FigureSpec, rows: list[dict]) -> tuple[bool, str]:
    """Return (can_generate, skip_reason). FB-7 non-blocking."""
    for f in spec.required:
        if f == "strain_id":
            continue
        if not _has_field(rows, f):
            aliases = _ALIASES.get(f, [f])[:4]
            return False, (f"missing required field '{f}' "
                           f"(aliases: {', '.join(aliases)})")
    if spec.multi_source_required and _sources_count(rows) < 2:
        return False, "requires ≥2 distinct source values"
    valid = [r for r in rows
             if all(_val(r, f) or f == "strain_id" for f in spec.required)]
    if len(valid) < spec.min_rows:
        return False, (f"only {len(valid)} rows have all required fields "
                       f"(minimum {spec.min_rows})")
    return True, ""


# ── Main entry point ──────────────────────────────────────────────────────────

def render_collection_figures(
    metadata_rows: list[dict] | None,
    out_dir: str | Path,
    source_file: str = "",
    version: str = "",
    *,
    skip_on_no_metadata: bool = True,
) -> dict[str, Any]:
    if not _HAVE_MPL:
        _require_mpl()
    """Generate all eligible collection figures. Returns summary dict.

    Args:
        metadata_rows: list of dicts from a strain metadata CSV/workbook.
                       None or empty → write availability report and return.
        out_dir:       directory to write figures into (created if absent).
        source_file:   name of the input file (for provenance footers).
        version:       Sapote–Mamey version string.
        skip_on_no_metadata: if True, writes a "no metadata" note and returns
                              without error when metadata_rows is empty.
    Returns:
        {
          "generated": [list of png paths],
          "skipped": [{figure_id, reason}, ...],
          "warnings": [str, ...],
          "availability_report": str path,
          "figure_manifest": str path,
          "n_generated": int,
          "n_skipped": int,
        }
    """
    from mamey import __version__ as _ver
    version = version or _ver
    date_str = datetime.date.today().isoformat()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []
    skipped: list[dict] = []
    warnings_out: list[str] = []
    meta = {"source_file": source_file}

    if not metadata_rows:
        note = ("Cross-strain figures were skipped because no collection metadata "
                "table was supplied. Provide a strain metadata CSV to unlock "
                "up to 20 comparison figures.")
        (out_dir / "FIGURE_AVAILABILITY.md").write_text(
            f"# Figure availability\n\n{note}\n\n" + _unlock_hint(), encoding="utf-8")
        _write_manifest_csv(out_dir, generated, skipped)
        return {"generated": [], "skipped": [], "warnings": [],
                "availability_report": str(out_dir / "FIGURE_AVAILABILITY.md"),
                "figure_manifest": str(out_dir / "figure_manifest.csv"),
                "n_generated": 0, "n_skipped": len(FIGURE_REGISTRY)}

    rows, norm_warns = normalize_metadata(metadata_rows)
    warnings_out.extend(norm_warns)

    for spec in FIGURE_REGISTRY:
        can_gen, reason = _check_gate(spec, rows)
        if not can_gen:
            skipped.append({"figure_id": spec.figure_id, "title": spec.title,
                             "reason": reason, "spec": spec})
            continue
        gen_fn = _GENERATORS.get(spec.figure_id)
        if gen_fn is None:
            skipped.append({"figure_id": spec.figure_id, "title": spec.title,
                             "reason": "generator not implemented", "spec": spec})
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                png = gen_fn(rows, str(out_dir), meta, version, date_str)
            if png and Path(png).exists():
                generated.append(png)
            else:
                skipped.append({"figure_id": spec.figure_id, "title": spec.title,
                                 "reason": "generator returned empty (data may be all-blank)",
                                 "spec": spec})
        except Exception as exc:  # FB-7: never block
            skipped.append({"figure_id": spec.figure_id, "title": spec.title,
                             "reason": f"render error: {type(exc).__name__}: {exc}",
                             "spec": spec})
            warnings_out.append(f"{spec.figure_id}: {exc}")

    avail_path = _write_availability_report(out_dir, generated, skipped, warnings_out,
                                             metadata_rows, version, date_str)
    manifest_path = _write_manifest_csv(out_dir, generated, skipped)

    return {
        "generated": generated,
        "skipped": skipped,
        "warnings": warnings_out,
        "availability_report": str(avail_path),
        "figure_manifest": str(manifest_path),
        "n_generated": len(generated),
        "n_skipped": len(skipped),
    }


# ── Report writers ────────────────────────────────────────────────────────────

def _unlock_hint() -> str:
    return (
        "More cross-strain figures can be unlocked by providing a strain metadata CSV "
        "or workbook. At minimum, include `strain_id`. Additional figures unlock with: "
        "`genus`, `host`, `location`, `source` / `dataset`, `candida_call`, `mrsa_call`, "
        "`candida_tested`, `mrsa_tested`, `closest_type_similarity`, `closest_type_strain`, "
        "`accession`, `collection_date`, `genome_mined`, and `priority`.\n\n"
        "Missing metadata only skips the affected figures and does not block package generation."
    )


def _write_availability_report(
    out_dir: Path,
    generated: list[str],
    skipped: list[dict],
    warnings: list[str],
    rows: list[dict],
    version: str,
    date_str: str,
) -> Path:
    lines = [
        "# Cross-strain figure availability report",
        f"Generated: {date_str} · Sapote–Mamey {version}",
        f"Input rows: {len(rows)} strains",
        "",
    ]
    if generated:
        lines += ["## Generated figures", ""]
        for p in generated:
            lines.append(f"- {Path(p).name}")
        lines.append("")
    else:
        lines += ["## Generated figures", "", "None.", ""]

    if skipped:
        lines += ["## Skipped figures", ""]
        for s in skipped:
            spec: FigureSpec | None = s.get("spec")
            lines.append(f"### {s['title']} (`{s['figure_id']}`)")
            lines.append(f"**Reason:** {s['reason']}")
            if spec:
                lines.append(f"**What this figure shows:** {spec.description}")
                miss = [f for f in spec.required if f != "strain_id"
                        and not _has_field(rows, f)]
                if miss:
                    lines.append(f"**Missing required fields:** {', '.join(miss)}")
                    for f in miss:
                        aliases = _ALIASES.get(f, [f])
                        lines.append(f"  - `{f}` — acceptable aliases: "
                                     f"{', '.join(f'`{a}`' for a in aliases[:5])}")
                lines.append(f"**Minimal CSV header to unlock:** `{spec.example_header()}`")
            lines.append("")

    if warnings:
        lines += ["## Warnings", ""]
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines += ["---", "", _unlock_hint()]
    path = out_dir / "FIGURE_AVAILABILITY.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_manifest_csv(
    out_dir: Path,
    generated: list[str],
    skipped: list[dict],
) -> Path:
    path = out_dir / "figure_manifest.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = _SafeWriter(f)
        w.writerow(["# provenance",
                    "Mamey collection figure manifest; capacity-level"])
        w.writerow(["figure_id", "status", "output_file", "skip_reason"])
        for p in generated:
            stem = Path(p).stem
            w.writerow([stem, "GENERATED", Path(p).name, ""])
        for s in skipped:
            w.writerow([s["figure_id"], "SKIPPED", "", s["reason"]])
    return path
