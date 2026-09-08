"""Reusable cumulative-plus-interval progress dashboard.

The renderer knows nothing about BLASTp, file layouts, or task discovery. A
domain adapter supplies timestamped events weighted in the actual work unit;
this module provides the shared Figure Factory visual grammar and A10 receipt.
"""
from __future__ import annotations

import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from mamey.figure_save import save_figure


class ProgressDashboardRefusal(RuntimeError):
    """Typed refusal for invalid progress data or unsafe layout."""


@dataclass(frozen=True)
class ProgressEvent:
    series: str
    completed_at: datetime
    units: float


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate(events: Sequence[ProgressEvent], windows_hours: Sequence[float], now: datetime) -> None:
    if not windows_hours or any(not math.isfinite(value) or value <= 0 for value in windows_hours):
        raise ProgressDashboardRefusal("PROGRESS_WINDOWS_INVALID")
    if len(set(windows_hours)) != len(windows_hours):
        raise ProgressDashboardRefusal("PROGRESS_WINDOWS_DUPLICATED")
    for event in events:
        if not event.series.strip():
            raise ProgressDashboardRefusal("PROGRESS_SERIES_EMPTY")
        if not math.isfinite(event.units) or event.units < 0:
            raise ProgressDashboardRefusal("PROGRESS_UNITS_INVALID")
        if (event.completed_at.tzinfo is None) != (now.tzinfo is None):
            raise ProgressDashboardRefusal("PROGRESS_TIMEZONE_MISMATCH")
        if event.completed_at > now:
            raise ProgressDashboardRefusal("PROGRESS_EVENT_IN_FUTURE")


def _bin_start(value: datetime, bin_hours: int) -> datetime:
    hour = value.hour - value.hour % bin_hours
    return value.replace(hour=hour, minute=0, second=0, microsecond=0)


def _layout_qa(fig: Any, legend: Any) -> dict[str, Any]:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    legend_box = legend.get_window_extent(renderer)
    failures = []
    if legend_box.x0 < canvas.x0 - 4 or legend_box.y0 < canvas.y0 - 4 or legend_box.x1 > canvas.x1 + 4:
        failures.append("SHARED_LEGEND_OUT_OF_BOUNDS")
    if legend_box.y0 < canvas.y0 + 0.055 * canvas.height:
        failures.append("SHARED_LEGEND_INVADES_FOOTER_RESERVE")
    axes_bottom = min(axis.get_window_extent(renderer).y0 for axis in fig.axes)
    if legend_box.y1 > axes_bottom:
        failures.append("SHARED_LEGEND_OVERLAPS_PANELS")
    for index, axis in enumerate(fig.axes):
        boxes = [label.get_window_extent(renderer) for label in axis.get_xticklabels() if label.get_visible() and label.get_text()]
        if any(left.overlaps(right) for left, right in zip(boxes, boxes[1:])):
            failures.append(f"AXIS_{index}_X_TICK_COLLISION")
    return {"status": "PASS" if not failures else "FAIL", "failures": failures}


def render_progress_dashboard(
    events: Sequence[ProgressEvent],
    *,
    now: datetime,
    windows_hours: Sequence[float],
    title: str,
    unit_label: str,
    out_stem: str | Path,
    package_dir: str | Path,
    provenance: str,
    figure_id: str = "PROGRESS_DASHBOARD",
    bin_hours: int = 1,
    colors: Mapping[str, str] | None = None,
    binding_state: str = "BOUND",
) -> dict[str, Any]:
    """Render cumulative completion above interval throughput for each window."""
    _validate(events, windows_hours, now)
    if not title.strip() or not unit_label.strip() or bin_hours <= 0 or 24 % bin_hours:
        raise ProgressDashboardRefusal("PROGRESS_SPEC_INVALID")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    series = sorted({event.series for event in events})
    if not series:
        raise ProgressDashboardRefusal("PROGRESS_EVENTS_EMPTY")
    palette = plt.get_cmap("tab20").resampled(max(1, len(series)))
    color_map = {name: (colors or {}).get(name, palette(index)) for index, name in enumerate(series)}
    window_values = sorted(windows_hours)
    figure_width = max(7.2, 5.4 * len(window_values))
    fig, axes = plt.subplots(2, len(window_values), figsize=(figure_width, 7.2),
                             squeeze=False, gridspec_kw={"height_ratios": [3, 1]})
    totals: dict[str, dict[str, float]] = {name: {} for name in series}
    data_rows: list[dict[str, Any]] = []
    for column, hours in enumerate(window_values):
        cutoff = now - timedelta(hours=hours)
        cumulative_axis, interval_axis = axes[0][column], axes[1][column]
        for name in series:
            selected = sorted((event for event in events if event.series == name and event.completed_at >= cutoff), key=lambda event: event.completed_at)
            cumulative = 0.0
            xs = [cutoff]
            ys = [0.0]
            bins: dict[datetime, float] = {}
            for event in selected:
                cumulative += event.units
                xs.append(event.completed_at)
                ys.append(cumulative)
                bucket = _bin_start(event.completed_at, bin_hours)
                bins[bucket] = bins.get(bucket, 0.0) + event.units
                data_rows.append({"series": name, "window_hours": hours,
                                  "completed_at": event.completed_at.isoformat(),
                                  "units": event.units, "cumulative_units": cumulative,
                                  "interval_start": bucket.isoformat(), "bin_hours": bin_hours})
            xs.append(now)
            ys.append(cumulative)
            cumulative_axis.step(xs, ys, where="post", color=color_map[name], linewidth=2.0)
            if bins:
                bx = sorted(bins)
                interval_axis.bar(bx, [bins[key] for key in bx], width=(bin_hours / 24) * 0.88,
                                  color=color_map[name], alpha=0.55, align="edge")
            totals[name][str(hours)] = cumulative
        cumulative_axis.set_title(f"Trailing {hours:g} h (as of {now:%Y-%m-%d %H:%M})", fontsize=10, fontweight="bold")
        cumulative_axis.set_ylabel(f"Cumulative {unit_label} completed")
        interval_axis.set_ylabel(f"{unit_label}/{bin_hours:g} h")
        interval_axis.set_xlabel("Completion time")
        for axis in (cumulative_axis, interval_axis):
            axis.set_xlim(cutoff, now)
            axis.grid(True, alpha=0.25)
            axis.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=7))
            axis.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M", tz=now.tzinfo))
            axis.tick_params(labelsize=7)
    handles = [Line2D([0], [0], color=color_map[name], linewidth=2.5) for name in series]
    labels = [name + " — " + " · ".join(f"{hours:g}h {totals[name][str(hours)]:g}" for hours in window_values) for name in series]
    columns = min(4, max(1, len(labels)))
    legend_rows = math.ceil(len(labels) / columns)
    bottom = min(0.38, 0.12 + 0.035 * legend_rows)
    legend = fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.065),
                        ncol=columns, fontsize=7.5, framealpha=0.95)
    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0.02, bottom, 0.99, 0.94))
    qa = _layout_qa(fig, legend)
    if qa["status"] != "PASS":
        plt.close(fig)
        raise ProgressDashboardRefusal("PROGRESS_LAYOUT_QA_FAILED: " + ";".join(qa["failures"]))

    root = Path(package_dir).resolve()
    stem = Path(out_stem).resolve()
    data_path = stem.with_suffix(".csv")
    data_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["series", "window_hours", "completed_at", "units", "cumulative_units", "interval_start", "bin_hours"]
    with data_path.open("w", newline="", encoding="utf-8") as stream:
        writer = _SafeDictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data_rows)
    figure_receipt = save_figure(
        fig, figure_id=figure_id, out_stem=stem, renderer=__name__, package_dir=root,
        provenance=provenance, binding_state=binding_state,
    )
    plt.close(fig)
    result = {
        "schema_version": "sapote-mamey.progress-dashboard.v1",
        "status": "CANDIDATE_RENDERED",
        "figure_id": figure_id,
        "unit_label": unit_label,
        "windows_hours": window_values,
        "bin_hours": bin_hours,
        "totals": totals,
        "layout_qa": qa,
        "data": {"logical_locator": data_path.relative_to(root).as_posix(),
                 "sha256": _sha(data_path), "bytes": data_path.stat().st_size},
        "figure_receipt": figure_receipt,
    }
    receipt_path = stem.with_name(stem.name + "_receipt.json")
    receipt_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
