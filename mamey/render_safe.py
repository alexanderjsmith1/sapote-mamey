"""render_safe.py — layout-safe rendering helpers for boss-ready Sapote-Mamey outputs.

This module is intentionally small and dependency-light.  It provides the shared
contract that was missing from the figure/PDF layer: values must be normalized
before prose/table rendering, long labels must be shortened for figures, and
Matplotlib figures can be smoke-tested for obvious overlapping text before they
are called boss-ready.
"""
from __future__ import annotations

import math
import re
import textwrap
from typing import Any, Iterable

_FORBIDDEN_VALUE_RE = re.compile(r"\bnp\.(?:int|float|bool|str|array|generic)|numpy\.")


def clean_scalar(value: Any) -> Any:
    """Return a plain Python scalar/string suitable for Markdown/PDF output.

    Prevents user-facing leaks such as ``np.int64(48)``, ``nan``, or raw dicts in
    prose.  Numpy is intentionally optional: we duck-type ``.item()`` instead of
    importing numpy.
    """
    if value is None:
        return ""
    # numpy scalar, pandas scalar, etc.
    item = getattr(value, "item", None)
    if callable(item):
        try:
            value = item()
        except Exception:
            pass
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        return round(value, 4) if not value.is_integer() else int(value)
    if isinstance(value, (int, bool)):
        return value
    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(clean_scalar(v)) for v in value if clean_scalar(v) != "")
    if isinstance(value, dict):
        # Do not dump raw dicts into boss-facing prose.
        parts = []
        for k, v in list(value.items())[:6]:
            cv = clean_scalar(v)
            if cv != "":
                parts.append(f"{k}: {cv}")
        return "; ".join(parts)
    s = str(value)
    # Convert numpy reprs if they already leaked into strings.
    s = re.sub(r"np\.int\d+\(([-+]?\d+)\)", r"\1", s)
    s = re.sub(r"np\.float\d+\(([-+]?\d+(?:\.\d+)?)\)", r"\1", s)
    s = s.replace("nan", "") if s.strip().lower() == "nan" else s
    return s.strip()


def has_forbidden_render_string(text: str) -> bool:
    """True when text contains raw computational reprs that must not ship."""
    if _FORBIDDEN_VALUE_RE.search(text or ""):
        return True
    if re.search(r"\b(?:nan|NaN|None)\b", text or ""):
        return True
    return False


def shorten_label(value: Any, *, max_chars: int = 34, keep: int = 10) -> str:
    """Single-line label for plots: short, deterministic, non-lossy via CSV sidecar."""
    s = str(clean_scalar(value))
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= max_chars:
        return s
    if keep * 2 + 1 >= max_chars:
        return s[: max_chars - 1].rstrip() + "…"
    return s[:keep].rstrip() + "…" + s[-keep:].lstrip()


def wrap_label(value: Any, *, width: int = 28, max_lines: int = 2) -> str:
    """Multi-line label capped for Matplotlib tick labels / callouts."""
    s = str(clean_scalar(value))
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return ""
    lines = textwrap.wrap(s, width=width, break_long_words=False, replace_whitespace=True)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = shorten_label(lines[-1], max_chars=width)
        if not lines[-1].endswith("…"):
            lines[-1] = lines[-1].rstrip(" .;,") + "…"
    return "\n".join(lines)


def figure_text_overlap_report(fig, *, renderer=None, min_pixels: float = 2.0) -> list[str]:
    """Return simple overlap warnings for visible text artists in a Matplotlib figure.

    This is a CI smoke test, not a typography proof. It catches the common
    regression where labels/tick labels are drawn directly on top of one another.
    """
    if renderer is None:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
    texts = []
    for ax_i, ax in enumerate(fig.axes):
        for t in ax.texts + ax.get_xticklabels() + ax.get_yticklabels():
            if not t.get_visible() or not str(t.get_text()).strip():
                continue
            try:
                bb = t.get_window_extent(renderer=renderer).expanded(1.0, 1.0)
            except Exception:
                continue
            if bb.width <= 0 or bb.height <= 0:
                continue
            texts.append((ax_i, str(t.get_text()), bb))
    warnings: list[str] = []
    for i in range(len(texts)):
        ax_i, ti, bi = texts[i]
        for ax_j, tj, bj in texts[i + 1:]:
            if ax_i != ax_j:
                continue
            if bi.overlaps(bj):
                # Ignore tiny incidental overlap; real failures have a clear intersection.
                x0, y0 = max(bi.x0, bj.x0), max(bi.y0, bj.y0)
                x1, y1 = min(bi.x1, bj.x1), min(bi.y1, bj.y1)
                if (x1 - x0) > min_pixels and (y1 - y0) > min_pixels:
                    warnings.append(f"text overlap: {ti!r} vs {tj!r}")
                    if len(warnings) >= 20:
                        return warnings
    return warnings


def assert_no_figure_text_overlap(fig) -> None:
    warnings = figure_text_overlap_report(fig)
    if warnings:
        raise AssertionError("; ".join(warnings[:5]))


# v9.7.409 (DEEP_AUDIT2_resource_dos #5): publication figure renderers size their canvas from the
# input count (figsize_inches proportional to strains/BGCs/genes) at a fixed publication DPI. A large
# or crafted cohort/region drives figsize_inches x dpi past matplotlib-Agg's hard 65,536 px limit —
# which raises ValueError deep in savefig — and, just below that limit, allocates a multi-GB RGBA
# buffer that OOMs the process. The only existing pixel guard (cohort_class_heatmap's 14,000 px
# SCREEN companion) fires AFTER the unconditional publication savefig, so it does not prevent the
# OOM/crash. These helpers cap the canvas BEFORE savefig: clamp the DPI so the longest edge stays
# under a browser/print-safe ceiling, and refuse cleanly (typed error) when even a floor DPI cannot.
import os as _os

# Agg refuses any single dimension above 2**16 px. Stay a safety margin below it.
_AGG_HARD_MAX_EDGE_PX = 65_500
_DEFAULT_MAX_FIGURE_EDGE_PX = 30_000   # browser/print-safe ceiling; ~100 MB RGBA at square worst case
_DPI_FLOOR = 100                        # below this, publication labels are unreadable


class FigureCanvasTooLargeError(RuntimeError):
    """Typed refusal: a figure's canvas cannot be rendered within safe pixel bounds.

    code is stable for issue-log matching; the renderer should refuse the single figure
    (skip/HOLD) rather than let matplotlib OOM or raise ValueError deep inside savefig.
    """

    code = "FIGURE_CANVAS_TOO_LARGE"


def max_figure_edge_px() -> int:
    """Longest safe raster edge in pixels (env-overridable via MAMEY_MAX_FIGURE_EDGE_PX)."""
    try:
        val = int(_os.environ.get("MAMEY_MAX_FIGURE_EDGE_PX", str(_DEFAULT_MAX_FIGURE_EDGE_PX)))
    except (TypeError, ValueError):
        return _DEFAULT_MAX_FIGURE_EDGE_PX
    # Never allow a value that Agg itself would reject.
    return max(1000, min(val, _AGG_HARD_MAX_EDGE_PX))


def safe_savefig_dpi(fig, requested_dpi: int, *, dpi_floor: int = _DPI_FLOOR) -> int:
    """Return a DPI at which ``fig.savefig`` stays within the safe pixel ceiling.

    Clamps ``requested_dpi`` down so ``max(width_in, height_in) * dpi <= max_figure_edge_px()``.
    Raises :class:`FigureCanvasTooLargeError` when even ``dpi_floor`` would exceed the ceiling —
    such a figure must be panelled/split by the caller, never rendered blind. The figure size is
    read from the live figure, so this reflects any tight-bbox growth already applied.
    """
    try:
        w_in, h_in = (float(x) for x in fig.get_size_inches())
    except Exception:
        # If we cannot measure the canvas, do not silently pass a possibly-huge figure through.
        return int(requested_dpi)
    longest_in = max(w_in, h_in, 0.01)
    ceiling = max_figure_edge_px()
    max_dpi = int(ceiling // longest_in)
    if max_dpi < dpi_floor:
        raise FigureCanvasTooLargeError(
            f"{FigureCanvasTooLargeError.code}: figure is {w_in:.1f}x{h_in:.1f} in; even {dpi_floor} "
            f"dpi needs {int(longest_in * dpi_floor):,} px on the longest edge, over the "
            f"{ceiling:,} px ceiling (MAMEY_MAX_FIGURE_EDGE_PX). Panel/split this figure instead of "
            f"rendering it — a larger raster would exceed matplotlib's limit or OOM the process.")
    return max(dpi_floor, min(int(requested_dpi), max_dpi))


def safe_table_cell(value: Any, *, max_chars: int = 80) -> str:
    """Cell text for boss PDFs: plain scalar and bounded length."""
    return shorten_label(clean_scalar(value), max_chars=max_chars, keep=max(8, max_chars // 3))

def safe_kcb_display(record, *, max_chars: int = 80) -> str:
    """Claim-safe rendering of a record's KCB anchor for human-facing output (Workstream A).

    Provenance-aware (per antismash_evidence.apply_evidence_to_bgcs):
      * provenance == MIBIG_REFERENCE_LINE -> kcb_top already holds the resolved 'accession | product |
        knownclusterblast #rank' identity line; show it with a '(similarity)' qualifier.
      * provenance == KCB_TOP_FIELD (or unknown) -> kcb_top is the raw rank-1 / genome self-hit line;
        prefer the safe closest_candidate_kcb_product surface, and qualify as 'similarity anchor only'.
      * nothing resolved -> 'unresolved'.

    Accepts a dict-like (workbook row) or an object with .get/getattr access. Never emits a bare raw
    kcb_top as if it were product identity.
    """
    def _get(k):
        if hasattr(record, "get"):
            return record.get(k)
        return getattr(record, k, None)

    prov = str(_get("closest_product_provenance") or _get("kcb_provenance") or "").strip()
    raw = str(_get("kcb_top") or _get("KCB_top") or "").strip()
    safe = str(_get("closest_candidate_kcb_product") or _get("closest_kcb_product") or "").strip()

    if prov == "MIBIG_REFERENCE_LINE" and raw:
        out = f"{raw} (similarity)"
    elif safe and safe.upper() != "UNRESOLVED":
        out = f"~{safe} (similarity anchor only)"
    elif raw and prov in ("KCB_TOP_FIELD", "", None):
        out = f"~{raw} (source-derived similarity anchor only; not product identity)"
    elif raw:
        out = f"{raw} (similarity)"
    else:
        return "unresolved"
    return out if len(out) <= max_chars else out[: max_chars - 1] + "\u2026"


def locus_label(value, *, max_chars: int = 42) -> str:
    """Layout-safe node/contig-first label for boss-facing figures/tables.

    The internal BGC id is retained as a parenthetical cross-reference, but the
    label starts with the assembly locator so a reader can find the locus in the
    assembly and antiSMASH HTML.
    """
    if isinstance(value, dict):
        bgc_id = value.get("bgc_id") or value.get("BGC_ID") or ""
        contig = value.get("node_id") or value.get("Node_ID") or value.get("contig") or value.get("Contig") or ""
        region = value.get("region") or value.get("antiSMASH_Region") or value.get("antismash_region") or ""
    else:
        bgc_id = getattr(value, "bgc_id", "")
        contig = getattr(value, "node_id", "") or getattr(value, "contig", "")
        region = getattr(value, "antismash_region", "") or getattr(value, "region", "")
    left = " ".join(str(clean_scalar(x)) for x in (contig, region) if str(clean_scalar(x)).strip()).strip()
    label = f"{left or 'UNKNOWN_LOCUS'} ({clean_scalar(bgc_id)})" if bgc_id else (left or "UNKNOWN_LOCUS")
    return shorten_label(label, max_chars=max_chars, keep=max(10, max_chars // 3))
