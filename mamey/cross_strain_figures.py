"""cross_strain_figures.py — deterministic cross-strain figure emitter for Sapote-Mamey.

This module turns already-emitted RG-GMCI batch CSVs into a complete figure folder.
It is intentionally extraction-only: it never re-runs RG-GMCI, never upgrades product
identity claims, and writes a companion source CSV for every figure.

Typical use:
    python mamey_run.py figures --rg-dir rggmci_v9755_diff_20260616 --out-dir figures
    python tools/build_cross_strain_figures.py --rg-dir rggmci_v9755_diff_20260616 --out-dir figures

Input conventions:
  --rg-dir should contain some or all of:
    * *_priority_summary.csv
    * *_ranked_pairs_all.csv
    * *_global_top150.csv
    * *_summary_diff.csv
  --ab-dir is optional and may contain quick AB/AF triage CSVs.

Figure policy:
  * one plot per file, no multi-panel figures;
  * the governed Sapote-Mamey visual theme controls palette, typography and exports;
  * every PNG has an SVG and editable source CSV next to it;
  * a compact claim-safety footer is retained on each chart, while expanded
    scope and provenance notes remain in FIGURE_INDEX.md.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import math
import os
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Iterable, Sequence

try:
    from .report_theme import theme_variant
except ImportError:  # preserve standalone legacy use
    theme_variant = None

THEME_CHOICES = ("evidence_dossier", "field_notebook", "dark_lab", "minimal_clinical")
_ACTIVE_THEME = "evidence_dossier"


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text crash-safely via a sibling .tmp + Path.replace(). Mirrors the established
    tmp+replace pattern used throughout this codebase (mamey/packaging.py::_atomic_write_text,
    tools/_wbio.py::atomic_write_text) for the manifest JSON / FIGURE_INDEX.md writes below,
    none of which previously had it (v9.7.374)."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding=encoding)
    tmp.replace(path)


def _read_csv(path: Path | None) -> list[dict]:
    if not path or not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [dict(r) for r in csv.DictReader(f)]


def _write_csv(path: Path, rows: Sequence[dict]) -> None:
    # v9.7.374 fix: was a bare open(path, "w") -- an interrupted write (this function runs once
    # per figure, ~15-30 times per call) leaves a truncated companion source CSV next to a PNG
    # that looks complete. Matches the established tmp+replace pattern used throughout this
    # codebase (mamey/packaging.py::_atomic_write_text, tools/_wbio.py) for exactly this failure
    # mode.
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if not rows:
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            f.write("")
        tmp.replace(path)
        return
    fields: list[str] = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                fields.append(k)
                seen.add(k)
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = _SafeDictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    tmp.replace(path)


def _find_first(root: Path, patterns: Sequence[str]) -> Path | None:
    if not root or not root.exists():
        return None
    hits: list[Path] = []
    for pat in patterns:
        hits.extend(sorted(root.glob(pat)))
    # Prefer v9755/current-specific tables, then longest/most specific name.
    def key(p: Path):
        s = p.name.lower()
        return (
            0 if "v9755" in s else 1,
            0 if "priority_summary" in s else 1,
            -len(s),
            s,
        )
    return sorted(set(hits), key=key)[0] if hits else None


def _has_computable_boundary_counts(summary: list[dict]) -> bool:
    """Return true only when every row has measured boundary composition.

    Older summaries lack the status field and retain their established behavior;
    new bridge rows mark unreadable source evidence explicitly so numeric plotting
    cannot coerce their blanks to zero.
    """
    required = {"interior_bgcs", "edge_bgcs", "full_contig_bgcs"}
    return bool(summary) and required.issubset(summary[0]) and all(
        row.get("boundary_counts_status", "COMPUTED") == "COMPUTED"
        for row in summary
    )


def _num(x, default: float = 0.0) -> float:
    if x is None or str(x).strip().lower() in {"", "na", "n/a", "nan", "none", "unbound"}:
        return default
    return float(x)


def _int(x, default: int = 0) -> int:
    return int(round(_num(x, default)))


def _safe_label(s: str, n: int = 58) -> str:
    s = str(s or "")
    return s if len(s) <= n else s[: max(1, n - 1)] + "…"


def _tokens(*vals: str) -> list[str]:
    out: list[str] = []
    for val in vals:
        if val is None:
            continue
        s = str(val).strip()
        if not s or s.lower() in {"nan", "none"}:
            continue
        for tok in re.split(r"[;,/|]+", s):
            tok = tok.strip().lower()
            if not tok or tok in {"nan", "none", "other", ""}:
                continue
            out.append(tok)
    return out


def _set_active_theme(name: str) -> None:
    global _ACTIVE_THEME
    key = str(name or "").strip().lower().replace("-", "_")
    if theme_variant:
        key = str(theme_variant(key)["name"])  # validate before any output is written
    elif key not in THEME_CHOICES:
        raise ValueError(f"unknown Sapote-Mamey report theme variant: {name}")
    _ACTIVE_THEME = key


def _setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # v9.7.405 reconciliation of two theme systems that arrived independently. figure_theme
    # (Aug-29 visual modernization) and report_theme (CODEX_390) both wanted to own this
    # rcParams block. They are LAYERED, not merged, and the order is the contract:
    #   1. figure_theme.apply_theme  -> PROFILE geometry, typography, minimum text size, svg
    #      font handling. It is passed the ACTIVE report_theme variant, so its own colour
    #      resolution defers to report_theme rather than competing with it.
    #   2. the report_theme block below -> the governed, user-selectable COLOUR variant, applied
    #      last so an operator's `--theme dark_lab` always wins on colour.
    # Neither module is now a second source of truth for the other's concern.
    from .figure_theme import apply_theme
    apply_theme(plt, "screen", variant=_ACTIVE_THEME)
    if theme_variant:
        palette = theme_variant(_ACTIVE_THEME)["tokens"]["colors"]
        dark = _ACTIVE_THEME == "dark_lab"
        plt.rcParams.update({
            "axes.prop_cycle": plt.cycler(color=["#" + palette["teal"], "#" + palette["gold"], "#" + palette["navy"]]),
            "axes.facecolor": "#" + (palette["navy"] if dark else palette["cream"]),
            "figure.facecolor": "#" + (palette["navy"] if dark else "FFFFFF"),
            "axes.edgecolor": "#" + palette["muted"],
            "axes.labelcolor": "#" + (palette["cream"] if dark else palette["ink"]),
            "xtick.color": "#" + (palette["cream"] if dark else palette["ink"]),
            "ytick.color": "#" + (palette["cream"] if dark else palette["ink"]),
            "text.color": "#" + (palette["cream"] if dark else palette["ink"]),
            "savefig.facecolor": "#" + (palette["navy"] if dark else "FFFFFF"),
        })
    return plt


def _save(fig, stem: Path) -> tuple[str, str]:
    # v9.7.405: the paired PNG/SVG export and the claim-safety footer move to figure_theme so
    # every governed figure carries the same footer text and the same 300-dpi contract; the
    # previous hand-rolled 220-dpi savefig pair is superseded, not duplicated.
    from .figure_theme import add_claim_safety_footer, save_figure_pair

    fig.tight_layout()
    fig.subplots_adjust(bottom=max(fig.subplotpars.bottom, 0.13))
    add_claim_safety_footer(fig, authority="Design Engineering Candidate")
    png, svg = save_figure_pair(fig, stem, profile="screen")
    return png.name, svg.name


def _barh(rows: list[dict], out: Path, title: str, xlabel: str, label_key: str, value_key: str):
    plt = _setup_mpl()
    fig, ax = plt.subplots(figsize=(10, max(4, 0.34 * len(rows) + 1.5)))
    labels = [_safe_label(r[label_key], 70) for r in rows]
    vals = [_num(r[value_key]) for r in rows]
    y = list(range(len(rows)))
    ax.barh(y, vals)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7 if len(rows) > 24 else 8)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    if vals:
        dx = max(vals) * 0.01 if max(vals) else 0.1
        for yi, v in zip(y, vals):
            ax.text(v + dx, yi, f"{v:g}", va="center", fontsize=7)
    saved = _save(fig, out)
    plt.close(fig)
    return saved


def _bar(rows: list[dict], out: Path, title: str, ylabel: str, label_key: str, value_key: str):
    plt = _setup_mpl()
    fig, ax = plt.subplots(figsize=(max(7, 0.34 * len(rows) + 2), 5.2))
    labels = [_safe_label(r[label_key], 30) for r in rows]
    vals = [_num(r[value_key]) for r in rows]
    x = list(range(len(rows)))
    ax.bar(x, vals)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=80, ha="right", fontsize=7)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    saved = _save(fig, out)
    plt.close(fig)
    return saved


def _stacked_barh(rows: list[dict], out: Path, title: str, xlabel: str, label_key: str, value_keys: Sequence[str]):
    plt = _setup_mpl()
    fig, ax = plt.subplots(figsize=(10, max(4, 0.34 * len(rows) + 1.5)))
    labels = [_safe_label(r[label_key], 70) for r in rows]
    y = list(range(len(rows)))
    left = [0.0] * len(rows)
    for key in value_keys:
        vals = [_num(r.get(key)) for r in rows]
        ax.barh(y, vals, left=left, label=key)
        left = [a + b for a, b in zip(left, vals)]
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7 if len(rows) > 24 else 8)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.legend(fontsize=8)
    saved = _save(fig, out)
    plt.close(fig)
    return saved


def _scatter(rows: list[dict], out: Path, title: str, xlabel: str, ylabel: str, x_key: str, y_key: str, label_key: str | None = None, annotate_top: int = 0):
    plt = _setup_mpl()
    fig, ax = plt.subplots(figsize=(7.5, 6.2))
    xs = [_num(r.get(x_key)) for r in rows]
    ys = [_num(r.get(y_key)) for r in rows]
    ax.scatter(xs, ys, alpha=0.75)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if label_key and annotate_top:
        ranked = sorted(rows, key=lambda r: _num(r.get(y_key)) + _num(r.get(x_key)), reverse=True)[:annotate_top]
        for r in ranked:
            ax.annotate(_safe_label(r.get(label_key, ""), 24), (_num(r.get(x_key)), _num(r.get(y_key))), fontsize=7, xytext=(4, 4), textcoords="offset points")
    saved = _save(fig, out)
    plt.close(fig)
    return saved


def _hist(values: list[float], out: Path, title: str, xlabel: str, bins: int = 24):
    plt = _setup_mpl()
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.hist(values, bins=bins)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    ax.set_title(title)
    saved = _save(fig, out)
    plt.close(fig)
    return saved


def _boxplot(groups: dict[str, list[float]], out: Path, title: str, ylabel: str):
    plt = _setup_mpl()
    fig, ax = plt.subplots(figsize=(max(7, len(groups) * 1.2), 5.6))
    labels = [str(k) for k, v in groups.items() if v]
    data = [groups[k] for k in labels]
    if data:
        # v9.7.374 fix: ax.boxplot(..., labels=labels) -- the `labels` kwarg was renamed to
        # `tick_labels` in matplotlib 3.9 and is fully removed (TypeError, not a warning) by
        # 3.11 -- inside this project's own declared `matplotlib>=3.7,<4.0` support range. This
        # crashed every call to this function (both the assembly-tier and the
        # score-by-confidence boxplots), and because build_cross_strain_figures() has no
        # per-figure exception isolation (unlike figures_smoke.py / collection_figures.py), the
        # exception propagated out of the whole function -- no figures already rendered before
        # this point ever got a manifest, FIGURE_INDEX.md, or zip. Setting the tick labels via
        # set_xticks/set_xticklabels instead is stable across the full 3.7-3.11+ range this
        # project supports (no `tick_labels`-vs-`labels` version split).
        ax.boxplot(data)
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    saved = _save(fig, out)
    plt.close(fig)
    return saved


def _heatmap(matrix: list[list[float]], row_labels: list[str], col_labels: list[str], out: Path, title: str):
    plt = _setup_mpl()
    fig, ax = plt.subplots(figsize=(max(7, 0.42 * len(col_labels) + 2.4), max(5, 0.32 * len(row_labels) + 1.8)))
    if matrix and col_labels and row_labels:
        ax.imshow(matrix, aspect="auto")
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels([_safe_label(c, 20) for c in col_labels], rotation=80, ha="right", fontsize=7)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels([_safe_label(r, 30) for r in row_labels], fontsize=7)
    ax.set_title(title)
    saved = _save(fig, out)
    plt.close(fig)
    return saved


def _count_rows(counter: Counter, key_name="label", value_name="count", top: int | None = None) -> list[dict]:
    rows = [{key_name: k, value_name: v} for k, v in counter.most_common(top)]
    rows.reverse()
    return rows


def _emit(figs: list[dict], out_dir: Path, name: str, rows: list[dict], caption: str, plotter: Callable[[Path], tuple[str, str]]):
    if not rows:
        return
    source = out_dir / f"{name}_data.csv"
    _write_csv(source, rows)
    png, svg = plotter(out_dir / name)
    figs.append({"name": name, "png": png, "svg": svg, "source_csv": source.name, "caption": caption, "rows": len(rows)})


def _load_inputs(rg_dir: Path, ab_dir: Path | None = None) -> dict:
    ab_dir = ab_dir or rg_dir
    paths = {
        "summary": _find_first(rg_dir, ["*v9755*priority_summary.csv", "*priority_summary.csv", "*summary.csv"]),
        "ranked": _find_first(rg_dir, ["*v9755*ranked_pairs_all.csv", "*ranked_pairs_all.csv"]),
        "global_top": _find_first(rg_dir, ["*v9755_global_top150.csv", "*global_top150.csv", "*global_top*.csv"]),
        "diff": _find_first(rg_dir, ["*vs*summary_diff.csv", "*summary_diff.csv"]),
        "ab_top": _find_first(ab_dir, ["*AB_top50*.csv", "*AB_top*.csv"]),
        "af_top": _find_first(ab_dir, ["*AF_top50*.csv", "*AF_top*.csv"]),
        "triage": _find_first(ab_dir, ["*triage_all*.csv"]),
    }
    return {k: _read_csv(v) for k, v in paths.items()} | {"paths": {k: str(v) if v else "" for k, v in paths.items()}}


def build_cross_strain_figures(rg_dir: str | Path, out_dir: str | Path, ab_dir: str | Path | None = None, top_n: int = 30, make_zip: bool = True, theme: str = "evidence_dossier") -> dict:
    rg_dir = Path(rg_dir)
    out_dir = Path(out_dir)
    ab_dir_p = Path(ab_dir) if ab_dir else None
    _set_active_theme(theme)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = _load_inputs(rg_dir, ab_dir_p)
    summary: list[dict] = data["summary"]
    ranked: list[dict] = data["ranked"]
    global_top: list[dict] = data["global_top"] or sorted(ranked, key=lambda r: (_num(r.get("rggmci_score")), _num(r.get("supporting_references"))), reverse=True)[:150]
    # Some comparison tables use compact aliases (score/support_refs/confidence). Normalize those
    # so the same plot functions work on either the raw top150 or the membership-annotated top150.
    for r in global_top:
        if "rggmci_score" not in r and "score" in r:
            r["rggmci_score"] = r.get("score")
        if "supporting_references" not in r and "support_refs" in r:
            r["supporting_references"] = r.get("support_refs")
        if "good_geometry_references" not in r and "good_geom_refs" in r:
            r["good_geometry_references"] = r.get("good_geom_refs")
        if "rggmci_confidence" not in r and "confidence" in r:
            r["rggmci_confidence"] = r.get("confidence")
    diff: list[dict] = data["diff"]
    ab_top: list[dict] = data["ab_top"]
    af_top: list[dict] = data["af_top"]
    triage: list[dict] = data["triage"]
    figs: list[dict] = []

    # Normalize summary row labels.
    for r in summary:
        r.setdefault("fragmentation_loss", round(_num(r.get("raw_bgcs")) - _num(r.get("corrected_bgcs")), 3))
        r.setdefault("display", r.get("strain") or r.get("instance_id") or "unknown")
        r.setdefault("high_plus_moderate", _num(r.get("high_pairs")) + _num(r.get("moderate_pairs")))

    # Summary-level figures.
    for key, title, xlabel, reverse in [
        ("raw_bgcs", "Raw antiSMASH BGC count by strain", "Raw BGC count", False),
        ("corrected_bgcs", "Corrected BGC count by strain", "Corrected BGC count", False),
        ("fragmentation_loss", "Fragmentation loss by strain", "Raw − corrected BGC count", False),
        ("pairs_total", "Total RG-GMCI pairs by strain", "RG-GMCI pairs", False),
        ("high_pairs", "HIGH RG-GMCI rescues by strain", "HIGH rescue count", False),
        ("moderate_pairs", "MODERATE RG-GMCI candidates by strain", "MODERATE candidate count", False),
        ("good_geometry_pairs", "Good-geometry RG-GMCI pairs by strain", "Good-geometry pair count", False),
        ("split_candidate_count", "Split-signature candidate count by strain", "Split candidate count", False),
        ("evidence_rows", "RG-GMCI evidence rows by strain", "Evidence row count", False),
        ("reference_record_count", "Reference records parsed by strain", "Reference record count", False),
        ("priority_score", "Best HIGH-first priority score by strain", "Priority score", False),
        ("priority_supporting_references", "Best-priority pair supporting references by strain", "Supporting references", False),
        ("priority_good_geometry_references", "Best-priority pair good-geometry references by strain", "Good-geometry references", False),
    ]:
        if summary and key in summary[0]:
            rows = sorted([{**r, "display": r.get("strain") or r.get("instance_id")} for r in summary], key=lambda r: _num(r.get(key)), reverse=reverse)
            _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_{key}_by_strain", rows, title,
                  lambda stem, rows=rows, title=title, xlabel=xlabel, key=key: _barh(rows, stem, title, xlabel, "display", key))

    if _has_computable_boundary_counts(summary):
        rows = sorted(summary, key=lambda r: _num(r.get("raw_bgcs")))
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_boundary_composition_by_strain", rows,
              "Interior/Edge/Full-contig BGC composition by strain.",
              lambda stem, rows=rows: _stacked_barh(rows, stem, "BGC boundary composition by strain", "BGC count", "strain", ["interior_bgcs", "edge_bgcs", "full_contig_bgcs"]))

    if summary and {"high_pairs", "moderate_pairs"}.issubset(summary[0].keys()):
        rows = sorted(summary, key=lambda r: _num(r.get("high_pairs")) + _num(r.get("moderate_pairs")))
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_high_moderate_pairs_by_strain", rows,
              "HIGH rescue and MODERATE candidate counts by strain.",
              lambda stem, rows=rows: _stacked_barh(rows, stem, "RG-GMCI HIGH/MODERATE burden by strain", "Pair count", "strain", ["high_pairs", "moderate_pairs"]))

    if summary and "assembly_tier" in summary[0]:
        c = Counter(r.get("assembly_tier") or "unknown" for r in summary)
        rows = _count_rows(c)
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_assembly_tier_counts", rows,
              "Number of strain instances in each assembly tier.",
              lambda stem, rows=rows: _bar(rows, stem, "Assembly tier counts", "Strain instances", "label", "count"))
        groups = defaultdict(list)
        for r in summary:
            groups[r.get("assembly_tier") or "unknown"].append(_num(r.get("pairs_total")))
        rows2 = [{"assembly_tier": k, "pairs_total": v} for k, vals in groups.items() for v in vals]
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_pairs_total_by_assembly_tier", rows2,
              "Distribution of total RG-GMCI pair count by assembly tier.",
              lambda stem, groups=groups: _boxplot(dict(sorted(groups.items())), stem, "RG-GMCI pair burden by assembly tier", "Total RG-GMCI pairs"))

    for xk, yk, title, xlabel, ylabel in [
        ("raw_bgcs", "pairs_total", "Raw BGC count vs total RG-GMCI pairs", "Raw BGC count", "Total RG-GMCI pairs"),
        ("fragmentation_loss", "pairs_total", "Fragmentation loss vs total RG-GMCI pairs", "Raw − corrected BGC count", "Total RG-GMCI pairs"),
        ("corrected_bgcs", "high_pairs", "Corrected BGC count vs HIGH RG-GMCI rescues", "Corrected BGC count", "HIGH rescues"),
        ("high_pairs", "good_geometry_pairs", "HIGH rescues vs good-geometry pairs", "HIGH rescues", "Good-geometry pairs"),
        ("reference_record_count", "pairs_total", "Reference records vs total RG-GMCI pairs", "Reference records", "Total RG-GMCI pairs"),
    ]:
        if summary and {xk, yk}.issubset(summary[0].keys()):
            _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_{xk}_vs_{yk}", summary, title,
                  lambda stem, xk=xk, yk=yk, title=title, xlabel=xlabel, ylabel=ylabel: _scatter(summary, stem, title, xlabel, ylabel, xk, yk, "strain", 8))

    # Ranked-pair figures.
    if ranked:
        conf = Counter(r.get("rggmci_confidence") or "unknown" for r in ranked)
        rows = _count_rows(conf)
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_rggmci_confidence_counts", rows,
              "Counts of RG-GMCI pair confidence classes.",
              lambda stem, rows=rows: _barh(rows, stem, "RG-GMCI confidence class counts", "Pair count", "label", "count"))

        for key, title, xlabel, bins in [
            ("rggmci_score", "RG-GMCI score distribution", "RG-GMCI score", 30),
            ("supporting_references", "Supporting-reference count distribution", "Supporting references", 30),
            ("good_geometry_references", "Good-geometry-reference count distribution", "Good-geometry references", 30),
            ("avg_min_identity", "Average minimum identity distribution", "Average minimum identity", 30),
            ("max_protein_sum", "Maximum protein-sum distribution", "Protein sum", 30),
            ("max_endpoint_hub_degree", "Endpoint hub-degree distribution", "Endpoint hub degree", 20),
        ]:
            vals = [_num(r.get(key), math.nan) for r in ranked]
            vals = [v for v in vals if not math.isnan(v)]
            if vals:
                rows = [{key: v} for v in vals]
                _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_{key}_distribution", rows, title,
                      lambda stem, vals=vals, title=title, xlabel=xlabel, bins=bins: _hist(vals, stem, title, xlabel, bins))

        groups = defaultdict(list)
        for r in ranked:
            groups[r.get("rggmci_confidence") or "unknown"].append(_num(r.get("rggmci_score")))
        rows = [{"confidence": k, "rggmci_score": v} for k, vals in groups.items() for v in vals]
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_score_by_confidence_boxplot", rows,
              "RG-GMCI score distributions grouped by confidence class.",
              lambda stem, groups=groups: _boxplot(dict(sorted(groups.items())), stem, "RG-GMCI score by confidence class", "RG-GMCI score"))

        for xk, yk, title, xlabel, ylabel in [
            ("supporting_references", "rggmci_score", "RG-GMCI score vs supporting references", "Supporting references", "RG-GMCI score"),
            ("good_geometry_references", "rggmci_score", "RG-GMCI score vs good-geometry references", "Good-geometry references", "RG-GMCI score"),
            ("avg_min_identity", "rggmci_score", "RG-GMCI score vs average minimum identity", "Average minimum identity", "RG-GMCI score"),
            ("max_protein_sum", "rggmci_score", "RG-GMCI score vs protein sum", "Protein sum", "RG-GMCI score"),
        ]:
            _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_{xk}_vs_{yk}", ranked, title,
                  lambda stem, xk=xk, yk=yk, title=title, xlabel=xlabel, ylabel=ylabel: _scatter(ranked, stem, title, xlabel, ylabel, xk, yk, "strain", 8))

        c = Counter(str(r.get("split_signature") or "False") for r in ranked)
        rows = _count_rows(c)
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_split_signature_counts", rows,
              "Counts of split_signature True/False across RG-GMCI pairs.",
              lambda stem, rows=rows: _bar(rows, stem, "Split-signature counts", "Pair count", "label", "count"))

        c = Counter((r.get("edge_a") or "unknown") + " + " + (r.get("edge_b") or "unknown") for r in ranked)
        rows = _count_rows(c, top=20)
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_edge_pair_combo_counts", rows,
              "Most common edge-status combinations among RG-GMCI pairs.",
              lambda stem, rows=rows: _barh(rows, stem, "Edge-status pair combinations", "Pair count", "label", "count"))

        c = Counter(r.get("acceptance_gate") or "unknown" for r in ranked)
        rows = _count_rows(c, top=20)
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_acceptance_gate_top20", rows,
              "Top acceptance/demotion gates among RG-GMCI pairs.",
              lambda stem, rows=rows: _barh(rows, stem, "Top RG-GMCI acceptance gates", "Pair count", "label", "count"))

        for col, label in [("shared_product_tokens", "shared product tokens"), ("shared_reference_type_tokens", "shared reference-type tokens")]:
            c = Counter()
            for r in global_top or ranked:
                c.update(_tokens(r.get(col, "")))
            rows = _count_rows(c, top=30)
            _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_{col}_top30", rows,
                  f"Top {label} among priority RG-GMCI pairs.",
                  lambda stem, rows=rows, label=label: _barh(rows, stem, f"Top {label}", "Count", "label", "count"))

    # Global-top figures.
    if global_top:
        top_rows = sorted(global_top, key=lambda r: (_num(r.get("rggmci_score")), _num(r.get("supporting_references"))), reverse=True)[:top_n]
        for r in top_rows:
            r["lead"] = f"{r.get('strain')} {r.get('pair')}"
        rows = list(reversed(top_rows))
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_global_top{top_n}_pairs_by_score", rows,
              f"Top {top_n} global RG-GMCI pairs by score/support.",
              lambda stem, rows=rows: _barh(rows, stem, f"Top {top_n} RG-GMCI pairs", "RG-GMCI score", "lead", "rggmci_score"))

        high_rows = [r for r in global_top if "HIGH" in str(r.get("rggmci_confidence"))]
        high_rows = sorted(high_rows, key=lambda r: (_num(r.get("rggmci_score")), _num(r.get("supporting_references"))), reverse=True)[:top_n]
        for r in high_rows:
            r["lead"] = f"{r.get('strain')} {r.get('pair')}"
        rows = list(reversed(high_rows))
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_global_top{top_n}_high_pairs_by_score", rows,
              f"Top {top_n} HIGH RG-GMCI rescue pairs by score/support.",
              lambda stem, rows=rows: _barh(rows, stem, f"Top {top_n} HIGH RG-GMCI rescue pairs", "RG-GMCI score", "lead", "rggmci_score"))

        # Heatmap: top product-class tokens by strain within top global pairs.
        class_by_strain = defaultdict(Counter)
        for r in global_top:
            strain = r.get("strain") or "unknown"
            for tok in _tokens(r.get("products_a", ""), r.get("products_b", ""), r.get("shared_product_tokens", "")):
                class_by_strain[strain][tok] += 1
        # sorted(): Counter.most_common is a stable sort, so TIED tokens break by dict
        # insertion order — which, from a bare set union, is randomised per process. With a
        # tie straddling the top-16 cut, that changes WHICH tokens the published heatmap
        # shows between identical runs, not merely their order.
        top_classes = [k for k, _ in Counter({k: sum(c[k] for c in class_by_strain.values()) for k in sorted(set().union(*[set(c) for c in class_by_strain.values()] or [set()]))}).most_common(16)]
        top_strains = [s for s, _ in Counter({s: sum(class_by_strain[s].values()) for s in class_by_strain}).most_common(28)]
        if top_classes and top_strains:
            matrix = [[class_by_strain[s][c] for c in top_classes] for s in top_strains]
            rows = [{"strain": s, "product_token": c, "count": class_by_strain[s][c]} for s in top_strains for c in top_classes]
            _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_top_pair_product_token_heatmap", rows,
                  "Product-token heatmap across strains using the global top RG-GMCI pairs.",
                  lambda stem, matrix=matrix, top_strains=top_strains, top_classes=top_classes: _heatmap(matrix, top_strains, top_classes, stem, "Top-pair product-token heatmap"))

        conf_by_strain = defaultdict(Counter)
        for r in ranked:
            conf_by_strain[r.get("strain") or "unknown"][r.get("rggmci_confidence") or "unknown"] += 1
        conf_cols = [k for k, _ in Counter({k: sum(c[k] for c in conf_by_strain.values()) for k in sorted(set().union(*[set(c) for c in conf_by_strain.values()] or [set()]))}).most_common()]  # sorted(): stable-sort tie order, see above
        strain_rows = [s for s, _ in Counter({s: sum(conf_by_strain[s].values()) for s in conf_by_strain}).most_common(30)]
        if conf_cols and strain_rows:
            matrix = [[conf_by_strain[s][c] for c in conf_cols] for s in strain_rows]
            rows = [{"strain": s, "confidence": c, "count": conf_by_strain[s][c]} for s in strain_rows for c in conf_cols]
            _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_confidence_by_strain_heatmap", rows,
                  "Confidence-class count heatmap by strain.",
                  lambda stem, matrix=matrix, strain_rows=strain_rows, conf_cols=conf_cols: _heatmap(matrix, strain_rows, conf_cols, stem, "RG-GMCI confidence classes by strain"))

    # Diff figures when old-vs-new tables are present.
    if diff:
        for key, title, xlabel in [
            ("delta_pairs_total", "v9.7.55 − v9.7.53 total-pair delta by instance", "Delta total RG-GMCI pairs"),
            ("delta_high_pairs", "v9.7.55 − v9.7.53 HIGH-pair delta by instance", "Delta HIGH pairs"),
            ("delta_moderate_pairs", "v9.7.55 − v9.7.53 MODERATE-pair delta by instance", "Delta MODERATE pairs"),
            ("delta_good_geometry_pairs", "v9.7.55 − v9.7.53 good-geometry-pair delta", "Delta good-geometry pairs"),
            ("delta_priority_score", "v9.7.55 − v9.7.53 priority-score delta", "Delta priority score"),
        ]:
            if key in diff[0]:
                rows = sorted(diff, key=lambda r: str(r.get("strain") or r.get("instance_id")))
                _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_{key}_diff", rows, title,
                      lambda stem, rows=rows, key=key, title=title, xlabel=xlabel: _barh(rows, stem, title, xlabel, "instance_id", key))

    # Quick AB/AF triage figures when present.
    def _lead_label(r: dict) -> str:
        return f"{r.get('strain')} {r.get('BGC_ID') or r.get('bgc_id')}"

    if ab_top:
        rows = sorted(ab_top, key=lambda r: _num(r.get("Score")), reverse=True)[:top_n]
        for r in rows:
            r["lead"] = _lead_label(r)
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_quick_ab_top{top_n}", list(reversed(rows)),
              f"Quick antibacterial top {top_n}; first-pass deterministic triage only.",
              lambda stem, rows=list(reversed(rows)): _barh(rows, stem, f"Quick antibacterial top {top_n}", "AB score", "lead", "Score"))
        c = Counter(r.get("strain") or "unknown" for r in ab_top)
        rows2 = _count_rows(c)
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_quick_ab_top50_strain_counts", rows2,
              "How many top-50 quick antibacterial rows each strain contributes.",
              lambda stem, rows=rows2: _barh(rows, stem, "Top-50 quick antibacterial rows per strain", "Count", "label", "count"))

    if af_top:
        rows = sorted(af_top, key=lambda r: _num(r.get("Score")), reverse=True)[:top_n]
        for r in rows:
            r["lead"] = _lead_label(r)
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_quick_af_top{top_n}", list(reversed(rows)),
              f"Quick antifungal top {top_n}; first-pass deterministic triage only.",
              lambda stem, rows=list(reversed(rows)): _barh(rows, stem, f"Quick antifungal top {top_n}", "AF score", "lead", "Score"))
        c = Counter(r.get("strain") or "unknown" for r in af_top)
        rows2 = _count_rows(c)
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_quick_af_top50_strain_counts", rows2,
              "How many top-50 quick antifungal rows each strain contributes.",
              lambda stem, rows=rows2: _barh(rows, stem, "Top-50 quick antifungal rows per strain", "Count", "label", "count"))

    if triage:
        for r in triage:
            r["lead"] = f"{r.get('strain')} {r.get('bgc_id')}"
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_quick_ab_vs_af_scatter", triage,
              "Quick antibacterial score versus quick antifungal score across triaged BGCs.",
              lambda stem: _scatter(triage, stem, "Quick AB vs AF triage", "AB score", "AF score", "ab_score", "af_score", "lead", 12))
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_quick_ab_vs_novelty_scatter", triage,
              "Quick antibacterial score versus novelty score across triaged BGCs.",
              lambda stem: _scatter(triage, stem, "Quick AB vs novelty triage", "AB score", "Novelty score", "ab_score", "novelty_score", "lead", 12))
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_quick_af_vs_novelty_scatter", triage,
              "Quick antifungal score versus novelty score across triaged BGCs.",
              lambda stem: _scatter(triage, stem, "Quick AF vs novelty triage", "AF score", "Novelty score", "af_score", "novelty_score", "lead", 12))
        c = Counter(r.get("lead_tier") or "unknown" for r in triage)
        rows = _count_rows(c)
        _emit(figs, out_dir, f"fig_{len(figs)+1:02d}_quick_triage_lead_tier_counts", rows,
              "Lead-tier counts from quick AB/AF triage rows.",
              lambda stem, rows=rows: _bar(rows, stem, "Quick triage lead-tier counts", "BGC count", "label", "count"))

    # Index and manifest.
    manifest = {
        "status": "PASS" if figs else "NO_FIGURES",
        "rg_dir": str(rg_dir),
        "ab_dir": str(ab_dir_p) if ab_dir_p else "",
        "input_paths": data["paths"],
        "summary_rows": len(summary),
        "ranked_pair_rows": len(ranked),
        "global_top_rows": len(global_top),
        "diff_rows": len(diff),
        "quick_ab_rows": len(ab_top),
        "quick_af_rows": len(af_top),
        "quick_triage_rows": len(triage),
        "figure_count": len(figs),
        "theme": _ACTIVE_THEME,
        "figures": figs,
        "claim_safety": "RG-GMCI figures nominate homology-guided split-fragment candidates; they do not prove physical contig linkage or exact product identity. Quick AB/AF figures are deterministic triage, not assay evidence.",
    }
    _atomic_write_text(out_dir / "cross_strain_figure_manifest.json", json.dumps(manifest, indent=2))

    lines = [
        "# Cross-Strain Figure Pack",
        "",
        f"Figures generated: **{len(figs)}**",
        "",
        "## Inputs",
        "",
    ]
    for k, v in data["paths"].items():
        lines.append(f"- `{k}`: `{v or 'not provided'}`")
    lines += [
        "",
        "## Claim-safety notes",
        "",
        "- RG-GMCI figures nominate homology-guided split-fragment candidates; they do **not** prove physical contig linkage.",
        "- KnownClusterBlast/KCB-style labels are class/context anchors, not exact product identity calls.",
        "- Quick AB/AF figures are deterministic prioritization only; they are not MIC, growth-inhibition, or extract-assay evidence.",
        "- New uploaded strains that have not yet been run are not in these figures unless their result CSVs were already present in the input folder.",
        "",
        "## Figure inventory",
        "",
    ]
    for f in figs:
        lines += [
            f"### {f['name']}",
            "",
            f["caption"],
            "",
            f"- PNG: `{f['png']}`",
            f"- SVG: `{f['svg']}`",
            f"- Source CSV: `{f['source_csv']}`",
            "",
        ]
    _atomic_write_text(out_dir / "FIGURE_INDEX.md", "\n".join(lines))

    if make_zip:
        zip_path = out_dir.parent / f"{out_dir.name}.zip"
        # v9.7.374 fix: was written directly to zip_path -- an interrupted write left a
        # truncated/corrupt zip at the final path (BadZipFile on open), same failure mode as the
        # other writes in this function. Build in a sibling .tmp and replace into place.
        zip_tmp = zip_path.with_name(zip_path.name + ".tmp")
        with zipfile.ZipFile(zip_tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(out_dir.rglob("*")):
                if p.is_file():
                    zf.write(p, arcname=p.relative_to(out_dir.parent))
        zip_tmp.replace(zip_path)
        manifest["zip_path"] = str(zip_path)
        _atomic_write_text(out_dir / "cross_strain_figure_manifest.json", json.dumps(manifest, indent=2))
    return manifest
