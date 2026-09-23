#!/usr/bin/env python3
"""Plot BLASTp crawl cumulative throughput in ACTUAL PROTEINS QUERIED (not
panels/files) over trailing 24h / 96h windows, with explicit lane selection receipts.

A "panel" (.faa file) batches a variable number of query protein sequences
(commonly a handful up to ~10s per file) -- counting panels understates/
distorts true throughput when panel size varies. This counts the actual
FASTA ">" headers in each FETCHED panel's query file and sums those,
cumulative by fetch_iso.

Per-channel query roots (from each runner's launchd plist RID_QUERIES,
default _QUERIES when unset):
  nr                -> _QUERIES
  ClusteredNR main   -> _QUERIES
  ClusteredNR bulk   -> _QUERIES_BULK_CL
  nr priority3       -> _QUERIES_PRIORITY3

Built 2026-08-18 per request: "plot actual
proteins" instead of panels.

Usage:
  python3 "tools/blastp_monitoring/plot_crawl_proteins_24_96h.py"
"""
import os
import json
import textwrap
import hashlib
import csv, datetime as dt
from pathlib import Path, PurePosixPath
import matplotlib
if __name__ == "__main__":
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    ROOT = Path(os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())) / "Blastp RESULTS"
    _LOCAL_NOW = dt.datetime.now().astimezone()
    NOW = _LOCAL_NOW.replace(tzinfo=None)
    TIMEZONE_LABEL = _LOCAL_NOW.tzname() or "local time"

    # ---------------------------------------------------------------------------
    # A lane is one direct-child _ledger.csv. Quiet lanes remain visible by default;
    # an optional recency filter and explicit archived/completed exclusions are receipted.
    # Query files are resolved by their strain-qualified ledger path, relative
    # to each _QUERIES* root. A basename alone is not unique across strains.
    # ---------------------------------------------------------------------------
    import argparse as _argparse
    import fnmatch as _fnmatch
    _ap = _argparse.ArgumentParser(description="Per-lane BLASTp throughput (auto-discovers active lanes).")
    _ap.add_argument("--lanes", default="*", help="fnmatch on RID_BASE dir, e.g. '*CODEX100*', '*GAP*', '*' (default: matching non-superseded lanes)")
    _ap.add_argument("--active-hours", type=float, default=None,
                     help="optional submit/fetch recency filter in hours; omitted keeps quiet lanes")
    _ap.add_argument("--all", action="store_true", help="include archived bases and fetched SINGLE_CLNR sets")
    _ARGS, _ = _ap.parse_known_args()
    ACTIVE_WINDOW_H = _ARGS.active_hours
    if ACTIVE_WINDOW_H is not None and (not __import__("math").isfinite(ACTIVE_WINDOW_H) or ACTIVE_WINDOW_H <= 0):
        _ap.error("--active-hours must be a finite positive number")
    selection_receipt = []

    def _parse_iso(iso):
        iso = (iso or "").strip()
        if not iso:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return dt.datetime.strptime(iso, fmt)
            except ValueError:
                continue
        return None

    def _lane_display_name(base: str) -> str:
        # _NR_CLUSTER_RID_CODEX100_s1 -> "ClusteredNR CODEX100 s1"; _NR_RID_CODEX100_s1 -> "nr CODEX100 s1"
        b = base.lstrip("_")
        kind = "ClusteredNR" if any(x in b.upper() for x in ("CLUSTER", "CLNR")) else "nr"
        tail = b.replace("NR_CLUSTER_RID", "").replace("NR_RID", "").strip("_").replace("_", " ")
        return f"{kind} {tail}".strip()

    def discover_active_ledgers(window_h=ACTIVE_WINDOW_H):
        import matplotlib
        cutoff = NOW - dt.timedelta(hours=window_h) if window_h is not None else None
        found = []
        for led in sorted(ROOT.glob("*/_ledger.csv")):
            base = led.parent.name
            reason = "included"
            try:
                with led.open() as handle:
                    rows = list(csv.DictReader(handle))
            except (OSError, UnicodeError, csv.Error) as exc:
                selection_receipt.append({"base": base, "included": False,
                    "reason": "unreadable ledger", "error": type(exc).__name__})
                continue
            if not _fnmatch.fnmatch(base, _ARGS.lanes):
                reason = "lane pattern"
            elif not _ARGS.all and any(marker in base.upper() for marker in
                                      ("_ARCHIVE_SUPERSEDED_", "_BATCHED_SUPERSEDED_")):
                reason = "explicit superseded path marker"
            elif (not _ARGS.all and "SINGLE_CLNR_" in base.upper() and "GAP" not in base.upper()
                  and rows and all((row.get("status") or "").lower() == "fetched"
                                   and _parse_iso(row.get("fetch_iso")) for row in rows)):
                reason = "all ledger rows fetched in SINGLE_CLNR set"
            elif cutoff is not None and not any(
                    stamp is not None and stamp >= cutoff
                    for row in rows for stamp in
                    (_parse_iso(row.get("fetch_iso")), _parse_iso(row.get("submit_iso")))):
                reason = "explicit recency filter"
            included = reason == "included"
            selection_receipt.append({"base": base, "included": included, "reason": reason,
                                      "ledger_rows": len(rows)})
            if included:
                found.append(base)
        # nr lanes first, then clustered; stable by name within group
        found.sort(key=lambda b: (any(x in b.upper() for x in ("CLUSTER", "CLNR")), b))
        import matplotlib.colors as mcolors
        n = max(len(found), 1)
        # Listed tab20 repeats colours when resampled above its 20 entries.
        # Keep the familiar palette for smaller runs and use a continuous map
        # for larger lane sets so every legend entry remains distinguishable.
        cmap = matplotlib.colormaps["tab20" if n <= 20 else "turbo"].resampled(n)
        LEDGERS = {}
        labels = [_lane_display_name(base) for base in found]
        for i, base in enumerate(found):
            label = labels[i] if labels.count(labels[i]) == 1 else f"{labels[i]} [{base}]"
            LEDGERS[label] = (f"{base}/_ledger.csv", None,
                                                 mcolors.to_hex(cmap(i)))
        return LEDGERS

    def build_query_index():
        # ledger-relative path -> all copies across _QUERIES* roots.
        idx = {}
        for query_root in sorted(ROOT.glob("_QUERIES*")):
            for faa in query_root.rglob("*.faa"):
                idx.setdefault(faa.relative_to(query_root).as_posix(), []).append(faa)
        return idx

    def panel_key(raw):
        key = (raw or "").replace("\\", "/")
        parts = PurePosixPath(key).parts
        return "/".join(parts) if parts and not key.startswith("/") and ".." not in parts else ""

    def digest(path):
        with path.open("rb") as fh:
            return hashlib.file_digest(fh, "sha256").digest()

    LEDGERS = discover_active_ledgers()
    _QUERY_INDEX = build_query_index()

    def parse(iso):
        iso = (iso or "").strip()
        if not iso:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return dt.datetime.strptime(iso, fmt)
            except ValueError:
                continue
        return None

    _seq_count_cache: dict[Path, int] = {}
    def count_seqs(path: Path) -> int:
        if path in _seq_count_cache:
            return _seq_count_cache[path]
        n = 0
        try:
            with path.open(errors="replace") as fh:
                for line in fh:
                    if line.startswith(">"):
                        n += 1
        except OSError:
            n = 0
        _seq_count_cache[path] = n
        return n

    data = {}
    missing_files = 0
    ambiguous_files = 0
    unknown_lanes = set()
    for name, (rel, _qroot, color) in LEDGERS.items():
        f = ROOT / rel
        comps = []  # (fetch_time, n_proteins)
        if f.exists():
            with f.open() as fh:
                r = csv.DictReader(fh)
                for row in r:
                    c = parse(row.get("fetch_iso"))
                    if not c:
                        continue
                    # Full ledger-relative identity prevents cross-strain basename collisions.
                    candidates = _QUERY_INDEX.get(panel_key(row.get("file", "")), [])
                    if not candidates:
                        missing_files += 1
                        unknown_lanes.add(name)
                        n = 0
                    else:
                        try:
                            if len({digest(path) for path in candidates}) != 1:
                                ambiguous_files += 1
                                unknown_lanes.add(name)
                                n = 0
                            else:
                                n = count_seqs(candidates[0])
                        except OSError:
                            missing_files += 1
                            unknown_lanes.add(name)
                            n = 0
                    comps.append((c, n))
        comps.sort()
        data[name] = (comps, color)

    def cumulative_proteins(comps, since):
        pts = sorted(c for c in comps if c[0] >= since)
        xs, ys = [], []
        total = 0
        for t, n in pts:
            total += n
            xs.append(t); ys.append(total)
        return xs, ys

    WINDOWS = [("Trailing 24 h", 24), ("Trailing 96 h", 96)]

    legend_labels = [textwrap.fill(f"{name} — " + " / ".join(
        ("≥" if name in unknown_lanes else "") + str(sum(n for t, n in comps if t >= NOW - dt.timedelta(hours=hours)))
        for _, hours in WINDOWS), width=48) for name, (comps, _) in data.items()]
    legend_lines = sum(label.count("\n") + 1 for label in legend_labels)
    fig, axes = plt.subplots(2, 2, figsize=(20, max(9, 0.22 * legend_lines + 2)),
                              gridspec_kw={"height_ratios": [3, 1]})

    for col, (title, hours) in enumerate(WINDOWS):
        since = NOW - dt.timedelta(hours=hours)
        ax = axes[0][col]
        axb = axes[1][col]
        lane_count = max(len(data), 1)
        hour_group_width = (1 / 24.0) * 0.9
        lane_slot_width = hour_group_width / lane_count
        lane_bar_width = lane_slot_width * 0.88
        for lane_index, (name, (comps, color)) in enumerate(data.items()):
            xs, ys = cumulative_proteins(comps, since)
            total = ys[-1] if ys else 0
            if xs:
                ax.step([since, *xs, NOW], [0, *ys, total], where="post", color=color, lw=2.0,
                        label=f"{name} — {total} proteins")
            else:
                ax.plot([], [], color=color, label=f"{name} — 0 proteins")
            binned = {}
            for t, n in comps:
                if t >= since:
                    b = t.replace(minute=0, second=0, microsecond=0)
                    binned[b] = binned.get(b, 0) + n
            if binned:
                bx = sorted(binned)
                grouped_bx = [
                    b + dt.timedelta(days=lane_slot_width * lane_index)
                    for b in bx
                ]
                axb.bar(grouped_bx, [binned[b] for b in bx], width=lane_bar_width,
                        color=color, alpha=0.55, align="edge")
        ax.set_title(f"{title}  (as of {NOW:%Y-%m-%d %H:%M} {TIMEZONE_LABEL})",
                     fontsize=11, fontweight="bold")
        ax.set_ylabel("cumulative proteins queried & fetched", fontsize=9)
        # One figure-level legend has reserved space outside both data columns.
        ax.grid(True, alpha=0.3)
        ax.set_xlim(since, NOW)
        axb.set_ylabel("proteins/hr", fontsize=8)
        axb.set_xlim(since, NOW)
        axb.grid(True, alpha=0.3)
        for a in (ax, axb):
            a.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M"))
            a.tick_params(axis="both", labelsize=8)
        axb.set_xlabel(f"time ({TIMEZONE_LABEL})", fontsize=9)

    fig.suptitle("Sapote-Mamey BLASTp crawl cumulative throughput — actual proteins queried  "
                 "(completion = results fetched; unmixed channels)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0.07, 0.68, 0.95])
    handles, _ = axes[0][0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, legend_labels, loc="upper left", bbox_to_anchor=(0.69, 0.92),
                   fontsize=8, framealpha=0.9, title="Lane — fetched proteins (24 h / 96 h)")
    excluded = sum(not row["included"] for row in selection_receipt)
    note = f"Lanes shown: {len(data)}; excluded: {excluded}. Selection details accompany this figure."
    if missing_files or ambiguous_files:
        note += f" Protein totals are LOWER BOUNDS: {missing_files} missing and {ambiguous_files} ambiguous query bindings."
    fig.text(0.04, 0.025, textwrap.fill(note, 155), fontsize=9, va="bottom")

    out_svg = os.path.join(os.environ.get("SAPOTE_BLASTP_PLOT_DIR", "."), "blastp_throughput_proteins_24_96h.svg")
    out_png = os.path.join(os.environ.get("SAPOTE_BLASTP_PLOT_DIR", "."), "blastp_throughput_proteins_24_96h.png")
    fig.savefig(out_svg, bbox_inches="tight")
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    receipt_path = Path(out_svg).with_suffix(".selection.json")
    receipt_path.write_text(json.dumps({"active_hours": ACTIVE_WINDOW_H, "all": _ARGS.all,
        "lane_pattern": _ARGS.lanes, "lanes": selection_receipt,
        "timezone": TIMEZONE_LABEL, "hourly_bar_layout": "grouped_by_lane",
        "missing_query_bindings": missing_files, "ambiguous_query_bindings": ambiguous_files}, indent=2) + "\n")

    print("=== crawl completions in ACTUAL PROTEINS (fetch_iso) ===")
    for name, (comps, color) in data.items():
        row = []
        for label, hours in WINDOWS:
            since = NOW - dt.timedelta(hours=hours)
            total = sum(n for t, n in comps if t >= since)
            panels = sum(1 for t, n in comps if t >= since)
            row.append(f"{label}: {total} proteins ({panels} panels)")
        print(f"  {name:32s} " + "   ".join(row))
    if missing_files or ambiguous_files:
        print(f"WARNING: {missing_files} fetched ledger rows lack a readable strain-qualified query path; "
              f"{ambiguous_files} have conflicting copies across query roots. "
              "Affected protein counts are unknown; plotted totals are lower bounds.")
    print(f'saved: {out_svg}', f'saved: {out_png}', sep="\n")
