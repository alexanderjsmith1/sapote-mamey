"""mamey/cohort_class_heatmap.py — cohort biosynthetic-class capacity heatmap.

Strain x primary-biosynthetic-class matrix, cell = BGC count, viridis, count-annotated.
Reproduces the "Core biosynthetic-class capacity by strain" figure. Reads the cohort
workbook's B2_Product_Class_Matrix sheet. Applies the standing permanent-exclusion rule
and the claim-safe footer.

Deterministic extraction-layer figure; no LLM. Publication PNG + companion CSV.

The default renderer deliberately distinguishes observed zero (white) from
positive capacity counts (viridis) and uses raw count labels.  The optional
Codex heatmap pack can convert the companion CSV into accessible SVG/HTML
panels without changing this core figure or any release/biological gate.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path
from typing import Any

# PC-A5 (v9.7.101): the comparative-exclusion set is centralized in genus_reference
# (registry-sourced SSOT) so every comparative consumer drops the same classes and the
# rule can't be silently skipped or drift per-module. NAPAA is NOT in it (registry-neutral
# since v9.7.22) — it was previously dropped here as a "standing downgrade", which contradicted
# the registry; that drop is removed. Non-class B2 columns (e.g. counts_reliability) are skipped too.
try:
    from .genus_reference import STANDING_EXCLUSIONS as _COMPARATIVE_EXCLUSIONS
except Exception:
    _COMPARATIVE_EXCLUSIONS = frozenset({"saccharide", "fatty_acid"})
# columns in B2 that are metadata, not biosynthetic classes
_NON_CLASS_COLS = {"strain", "label_provenance", "counts_reliability"}
_LABEL_PROVENANCE = frozenset({"RAW_ANTISMASH", "GENE_BACKED"})
_EXCLUDED_CLASSES = set(_COMPARATIVE_EXCLUSIONS)
_FOOTER = ("Data-only figure · capacity-level, not activity · CCTT/score = biosynthetic-capacity "
           "signal, not confirmed product · KCB = similarity, not identity · "
           "gray = missing; white = observed zero · standing comparative exclusions applied "
           "from registry SSOT; NAPAA is registry-neutral")
_BROWSER_SAFE_MAX_EDGE_PX = 14_000
_PUBLICATION_DPI = 300


def _browser_safe_raster_dpi(fig_width: float, fig_height: float,
                             requested_dpi: int = _PUBLICATION_DPI,
                             max_edge_px: int = _BROWSER_SAFE_MAX_EDGE_PX) -> int:
    """Return a browser-safe companion-raster DPI without changing print output.

    Chromium-family renderers can display a large PNG's first tiles while painting
    later tiles blank when an edge exceeds their practical raster limit.  Retain the
    requested publication raster and emit a separately named screen companion whose
    longest estimated edge stays below a conservative limit.  A 72-DPI floor keeps
    labels usable; figures still exceeding the limit at that floor must be panelled by
    the caller rather than silently described as browser-reviewed.
    """
    longest_inches = max(float(fig_width), float(fig_height), 0.01)
    return max(72, min(int(requested_dpi), int(max_edge_px // longest_inches)))


def _read_b2(workbook_path) -> list[dict]:
    """Read B2_Product_Class_Matrix from a cohort workbook. Returns [] if absent."""
    try:
        from .master_figure_atlas import read_xlsx_table
        return read_xlsx_table(workbook_path, "B2_Product_Class_Matrix")
    except Exception:
        return []


def build_class_matrix(rows: list[dict], label_provenance: str = "RAW_ANTISMASH") -> tuple[list[str], list[str], list[list[int | None]]]:
    """From B2 rows build (strain_labels, class_labels, matrix). Excludes the standing
    comparative-exclusion classes and any all-zero class column. Strains in input order."""
    label_provenance = str(label_provenance).upper()
    if label_provenance not in _LABEL_PROVENANCE:
        raise ValueError(f"label_provenance must be one of {sorted(_LABEL_PROVENANCE)}")
    if not rows:
        return [], [], []
    if "label_provenance" in rows[0]:
        rows = [r for r in rows
                if str(r.get("label_provenance", "")).upper() == label_provenance
                or (label_provenance == "RAW_ANTISMASH" and not str(r.get("label_provenance", "")).strip())]
        if not rows:
            return [], [], []
    # class columns = all keys except metadata cols, minus the standing comparative exclusions
    classes = [k for k in rows[0].keys()
               if k not in _NON_CLASS_COLS and k not in _EXCLUDED_CLASSES]
    strains = []
    matrix = []
    for r in rows:
        s = str(r.get("strain", "")).strip()
        if not s:
            continue
        strains.append(s)
        matrix.append([_to_count(r.get(c)) for c in classes])
    # drop all-zero class columns (keep the figure legible)
    # An all-missing column is also not plot-ready, but an observed zero is not
    # interchangeable with missing input.  Only positive-populated columns are
    # retained; the returned cells preserve None versus 0 within them.
    keep = [
        j for j, _ in enumerate(classes)
        if any((matrix[i][j] or 0) > 0 for i in range(len(matrix)))
    ]
    classes = [classes[j] for j in keep]
    matrix = [[row[j] for j in keep] for row in matrix]
    return strains, classes, matrix


def _to_count(v: Any) -> int | None:
    """Parse a BGC count without coercing absent/malformed evidence to zero."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        value = float(v)
    except (TypeError, ValueError):
        return None
    if value < 0 or not value.is_integer():
        return None
    return int(value)


def render_cohort_class_heatmap(workbook_path, out_png, out_csv, title=None,
                                claim_prefix="", label_provenance="RAW_ANTISMASH",
                                rows=None):
    """Render the cohort class-capacity heatmap from a cohort workbook. Never raises; returns
    a status dict. Writes a skip card if the B2 sheet is missing or empty.

    v9.7.410: ``rows`` — optional pre-built B2-shaped rows (``strain`` + class-count columns,
    optionally ``label_provenance``). When given, ``workbook_path`` is not read; this is the
    entry point the multi-strain run uses to auto-emit the figure from its own sealed
    packages without requiring a cohort workbook. Passing ``rows=[]`` yields the normal skip card.
    """
    out_png, out_csv = Path(out_png), Path(out_csv)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows) if rows is not None else _read_b2(workbook_path)
    label_provenance = str(label_provenance).upper()
    strains, classes, matrix = build_class_matrix(rows, label_provenance=label_provenance)
    if not strains or not classes:
        out_png.with_suffix(".SKIPPED.md").write_text(
            "# Cohort class heatmap skipped\n\nB2_Product_Class_Matrix missing or empty in the "
            f"workbook for selected label provenance `{label_provenance}`. "
            "Populate the cohort workbook first.\n", encoding="utf-8")
        return {"status": "SKIPPED", "reason": "no B2 data for selected label provenance",
                "label_provenance": label_provenance, "n_strains": 0}

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:
        out_png.with_suffix(".SKIPPED.md").write_text(
            f"# Cohort class heatmap skipped\n\nmatplotlib unavailable: {e}\n", encoding="utf-8")
        return {"status": "SKIPPED", "reason": f"matplotlib: {e}", "n_strains": len(strains)}

    grid = np.array(
        [[np.nan if value is None else value for value in row] for row in matrix],
        dtype=float,
    )
    # Missing is gray; observed zero is paper-white; positive raw counts use
    # viridis.  The prior implementation converted malformed/absent values to
    # zero and therefore rendered missing evidence as a biological negative.
    display = np.ma.masked_invalid(grid)
    cmap = plt.get_cmap("viridis").with_extremes(
        bad="#d7dce1",
        under="#f7f7f7",
    )
    finite = grid[np.isfinite(grid)]
    vmax = max(1.0, float(finite.max()) if finite.size else 1.0)
    fig_w = max(8.5, 0.50 * len(classes) + 3.8)
    fig_h = max(4.5, 0.42 * len(strains) + 2.5)
    # v9.7.410 (no-label-overlap rule): the claim-safe footer is a figure-level text that
    # constrained_layout does not know about, so on a short (few-strain) cohort it was painted
    # straight across the class tick labels. Wrap the footer to the canvas width and reserve a
    # bottom band for it BEFORE laying out the axes, so the two never share pixels.
    import textwrap as _tw
    _footer_text = ((claim_prefix + " · ") if claim_prefix else "") + _FOOTER
    _footer_lines = _tw.wrap(_footer_text, width=max(40, int(fig_w * 20))) or [_footer_text]
    _footer_band_in = 0.10 + 0.135 * len(_footer_lines)          # 6.6 pt text ≈ 0.135 in / line
    fig, ax = plt.subplots(figsize=(fig_w, fig_h + _footer_band_in),
                           constrained_layout=True)
    _band_frac = _footer_band_in / (fig_h + _footer_band_in)
    fig.get_layout_engine().set(rect=(0.0, _band_frac, 1.0, 1.0 - _band_frac))
    im = ax.imshow(display, cmap=cmap, aspect="auto", vmin=0.5, vmax=vmax,
                   interpolation="nearest")
    ax.set_xticks(range(len(classes)))
    # v9.7.410: vertical class labels. The former 45° labels had axis-aligned bounding boxes that
    # overlapped their neighbours at 0.50 in/column (flagged by render_safe.figure_text_overlap_report);
    # vertical text keeps every label inside its own column, off the cells and off each other.
    ax.set_xticklabels(classes, rotation=90, ha="center", va="top", fontsize=8.5)
    ax.set_yticks(range(len(strains)))
    ax.set_yticklabels([f"strain {s}" for s in strains], fontsize=8.5)
    ax.tick_params(which="both", length=0)
    # Fine white cell boundaries improve tracking across wide matrices without
    # the heavy black boxes used by earlier Figure Factory drafts.
    ax.set_xticks([x - 0.5 for x in range(1, len(classes))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(strains))], minor=True)
    ax.grid(which="minor", color="#ffffff", linewidth=0.75)
    # v9.7.410: wrap the title to the canvas width — the one-line title over-ran the axes and
    # collided with the colorbar label on narrow (few-class) cohorts.
    _title_text = title or ("Core biosynthetic-class capacity by strain — cohort "
                            f"[{label_provenance}] (standing comparative exclusions removed; NAPAA retained)")
    ax.set_title("\n".join(_tw.wrap(_title_text, width=max(30, int(fig_w * 8.5))) or [_title_text]),
                 fontsize=11.5, pad=14)
    # Annotate raw positive counts.  Choose text colour from the rendered
    # colormap luminance rather than a global numeric threshold; this stays
    # legible when a single large count stretches the colour range.
    for i in range(len(strains)):
        for j in range(len(classes)):
            if not np.isfinite(grid[i, j]):
                continue
            v = int(grid[i, j])
            if v:
                rgba = cmap((float(grid[i, j]) - 0.5) / max(vmax - 0.5, 0.5))
                luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
                ax.text(j, i, v, ha="center", va="center", fontsize=7,
                        color="#111820" if luminance > 0.55 else "white",
                        fontweight="semibold")
    colorbar = fig.colorbar(im, ax=ax, shrink=0.78, pad=0.018)
    colorbar.set_label("Raw BGC count (primary class)\ngray = missing · white = observed zero",
                       fontsize=8.5)
    fig.text(0.5, 0.06 / (fig_h + _footer_band_in), "\n".join(_footer_lines),
             ha="center", va="bottom", fontsize=6.6, color="#666", linespacing=1.25)
    # v9.7.410: record the project's own label-overlap smoke check in the receipt (empty list =
    # clean). Diagnostic only — it never blocks the render; the run-level tests assert on it.
    try:
        from .render_safe import figure_text_overlap_report
        _overlap_warnings = list(figure_text_overlap_report(fig))
    except Exception as _ov_exc:  # pragma: no cover - diagnostic must never fail the figure
        _overlap_warnings = [f"overlap check unavailable: {type(_ov_exc).__name__}"]
    # v9.7.409 (DEEP_AUDIT2_resource_dos #5): cap the publication canvas BEFORE savefig. A large
    # cohort makes figsize x 300 dpi exceed matplotlib-Agg's 65,536 px limit (ValueError deep in
    # savefig) or allocate a multi-GB buffer that OOMs. Clamp DPI to a safe ceiling; if even a floor
    # DPI cannot fit, refuse this one figure cleanly (skip card) rather than crash the whole run.
    from .render_safe import safe_savefig_dpi, FigureCanvasTooLargeError
    try:
        _pub_dpi = safe_savefig_dpi(fig, _PUBLICATION_DPI)
    except FigureCanvasTooLargeError as exc:
        plt.close(fig)
        out_png.with_suffix(".SKIPPED.md").write_text(
            f"# Cohort class heatmap skipped\n\n{exc}\n", encoding="utf-8")
        return {"status": "SKIPPED", "reason": str(exc), "n_strains": len(strains),
                "refusal_code": FigureCanvasTooLargeError.code}
    fig.savefig(out_png, dpi=_pub_dpi, bbox_inches="tight")

    # CODEX13B: the 300-DPI publication PNG is unchanged. When its longest estimated edge would exceed
    # a browser's practical raster limit (Chromium paints later tiles blank), ALSO emit a separately
    # named `<stem>_SCREEN.png` at a deterministic lower DPI for the REQUIRED 100%-zoom browser review.
    # Raster eligibility (PASS | HOLD_PANEL_REQUIRED) NEVER promotes the browser-visual-review gate,
    # which stays REQUIRED — a browser-safe raster only makes the review *possible*, not passed.
    fig_w, fig_h = (float(v) for v in fig.get_size_inches())
    est_pub_edge_px = int(max(fig_w, fig_h) * _PUBLICATION_DPI)
    browser_raster = None
    if est_pub_edge_px > _BROWSER_SAFE_MAX_EDGE_PX:
        screen_dpi = _browser_safe_raster_dpi(fig_w, fig_h)
        screen_png = out_png.with_name(out_png.stem + "_SCREEN.png")
        fig.savefig(screen_png, dpi=screen_dpi, bbox_inches="tight")
        browser_raster = {
            "path": screen_png.name, "dpi": screen_dpi, "publication_dpi": _PUBLICATION_DPI,
            "est_publication_edge_px": est_pub_edge_px,
            "est_screen_edge_px": int(max(fig_w, fig_h) * screen_dpi),
        }
    plt.close(fig)

    # eligibility: is there a single browser-safe raster to review? (screen if emitted, else publication)
    review_edge_px = browser_raster["est_screen_edge_px"] if browser_raster else est_pub_edge_px
    raster_eligibility = "PASS" if review_edge_px <= _BROWSER_SAFE_MAX_EDGE_PX else "HOLD_PANEL_REQUIRED"

    # AUDIT_374: build the companion CSV in memory, then write it crash-safely
    # (tmp-sibling + os.replace) instead of a plain open(..., "w"). This CSV is the
    # machine-readable companion to the cohort-level figure (the Codex heatmap pack and
    # other downstream consumers read it directly); a process killed mid-write previously
    # left a truncated file on disk with no error surfaced anywhere.
    import io
    import os as _os
    buf = io.StringIO()
    w = _SafeWriter(buf)
    w.writerow(["strain", "label_provenance"] + classes)
    for s, row in zip(strains, matrix):
        w.writerow([s, label_provenance] + ["" if value is None else value for value in row])
    _tmp_csv = str(out_csv) + ".tmp"
    try:
        with open(_tmp_csv, "w", newline="", encoding="utf-8") as fh:
            fh.write(buf.getvalue())
    except BaseException:
        if _os.path.exists(_tmp_csv):
            _os.remove(_tmp_csv)
        raise
    _os.replace(_tmp_csv, out_csv)

    return {"status": "OK", "n_strains": len(strains), "n_classes": len(classes),
            "png": out_png.name, "csv": out_csv.name,
            "label_provenance": label_provenance,
            "style_profile": "publication-v4-vertical-class-labels-footer-band",
            "text_overlap_warnings": _overlap_warnings,   # v9.7.410: [] = no label/label collisions
            "browser_raster": browser_raster,          # None when the publication PNG is already browser-safe
            "raster_eligibility": raster_eligibility,   # PASS | HOLD_PANEL_REQUIRED (raster only)
            "independent_gates": {
                "render_qa": "NOT_ASSESSED",
                "browser_visual_review": "REQUIRED",    # raster eligibility CANNOT promote this to PASS
                "biological_validation": "NOT_ASSESSED",
                "publication_approval": "NOT_ASSESSED",
            }}
