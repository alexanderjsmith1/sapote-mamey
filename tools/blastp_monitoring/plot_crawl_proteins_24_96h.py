#!/usr/bin/env python3
"""Plot BLASTp crawl cumulative throughput in ACTUAL PROTEINS QUERIED (not
panels/files) over trailing 24h / 96h windows, across all 4 live ledgers.

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
import hashlib
import csv, datetime as dt
from pathlib import Path, PurePosixPath
import matplotlib
if __name__ == "__main__":
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    ROOT = Path(os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())) / "Blastp RESULTS"
    NOW = dt.datetime.now()

    # ---------------------------------------------------------------------------
    # AUTO-DISCOVER active lanes (no hardcoded lane map — that map went stale every
    # wave and drew the current run as empty; this was the recurring "you just made
    # this plot" failure). A lane = one direct-child _ledger.csv with submit OR fetch
    # activity inside ACTIVE_WINDOW_H; historical/idle lanes drop off on their own.
    # Query files are resolved by their strain-qualified ledger path, relative
    # to each _QUERIES* root. A basename alone is not unique across strains.
    # ---------------------------------------------------------------------------
    import argparse as _argparse
    import fnmatch as _fnmatch
    _ap = _argparse.ArgumentParser(description="Per-lane BLASTp throughput (auto-discovers active lanes).")
    _ap.add_argument("--lanes", default="*", help="fnmatch on RID_BASE dir, e.g. '*CODEX100*', '*GAP*', '*' (default: all active)")
    _ap.add_argument("--active-hours", type=float, default=96,
                     help="a lane counts as active if it has any submit/fetch within this many hours (default 96)")
    _ARGS, _ = _ap.parse_known_args()
    ACTIVE_WINDOW_H = _ARGS.active_hours

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
        cutoff = NOW - dt.timedelta(hours=window_h)
        found = []
        for led in sorted(ROOT.glob("*/_ledger.csv")):
            if not _fnmatch.fnmatch(led.parent.name, _ARGS.lanes):
                continue
            active = False
            try:
                for row in csv.DictReader(led.open()):
                    for col in ("fetch_iso", "submit_iso"):
                        t = _parse_iso(row.get(col))
                        if t and t >= cutoff:
                            active = True
                            break
                    if active:
                        break
            except OSError:
                continue
            if active:
                found.append(led.parent.name)  # RID_BASE dir name
        # nr lanes first, then clustered; stable by name within group
        found.sort(key=lambda b: (any(x in b.upper() for x in ("CLUSTER", "CLNR")), b))
        import matplotlib.colors as mcolors
        n = max(len(found), 1)
        cmap = matplotlib.colormaps["tab20"].resampled(n)
        LEDGERS = {}
        for i, base in enumerate(found):
            LEDGERS[_lane_display_name(base)] = (f"{base}/_ledger.csv", None,
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
                        n = 0
                    else:
                        try:
                            if len({digest(path) for path in candidates}) != 1:
                                ambiguous_files += 1
                                n = 0
                            else:
                                n = count_seqs(candidates[0])
                        except OSError:
                            missing_files += 1
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

    fig, axes = plt.subplots(2, 2, figsize=(15, 9),
                              gridspec_kw={"height_ratios": [3, 1]})

    for col, (title, hours) in enumerate(WINDOWS):
        since = NOW - dt.timedelta(hours=hours)
        ax = axes[0][col]
        axb = axes[1][col]
        for name, (comps, color) in data.items():
            xs, ys = cumulative_proteins(comps, since)
            total = ys[-1] if ys else 0
            if xs:
                ax.step(xs, ys, where="post", color=color, lw=2.0,
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
                axb.bar(bx, [binned[b] for b in bx], width=(1/24.0)*0.9,
                        color=color, alpha=0.55, align="edge")
        ax.set_title(f"{title}  (as of {NOW:%Y-%m-%d %H:%M} PDT)",
                     fontsize=11, fontweight="bold")
        ax.set_ylabel("cumulative proteins queried & fetched", fontsize=9)
        ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(since, NOW)
        axb.set_ylabel("proteins/hr", fontsize=8)
        axb.set_xlim(since, NOW)
        axb.grid(True, alpha=0.3)
        for a in (ax, axb):
            a.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d\n%H:%M"))
            a.tick_params(axis="both", labelsize=8)
        axb.set_xlabel("time (PDT)", fontsize=9)

    fig.suptitle("Sapote-Mamey BLASTp crawl cumulative throughput — actual proteins queried  "
                 "(completion = results fetched; unmixed channels)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    out_svg = os.path.join(os.environ.get("SAPOTE_BLASTP_PLOT_DIR", "."), "blastp_throughput_proteins_24_96h.svg")
    out_png = os.path.join(os.environ.get("SAPOTE_BLASTP_PLOT_DIR", "."), "blastp_throughput_proteins_24_96h.png")
    fig.savefig(out_svg)
    fig.savefig(out_png, dpi=220)

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
