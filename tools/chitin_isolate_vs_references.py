#!/usr/bin/env python3
"""chitin_isolate_vs_references — chitin-active gene content of each sequenced isolate against the reference genomes of
its genus, one row per isolate (catalog figure type K01).

The bee paper's Fig. 6 drew this from a paper script with fixed paths and colours. This tool takes its inputs as
arguments and prints at the house floor (every text run at least 8 pt at the print width). It draws counts; it runs no
search. Counts come from an existing chitin census table, where each genome's proteins were searched with the same
profiles (columns Glyco_hydro_18, Glyco_hydro_19, LPMO_10, CBM_5_12, ..., cds_searched).

Inputs
  --genomes     TSV: strain, genus, and optional row_note (shown in brackets after the strain, e.g. a host as recorded).
                Row order is drawing order. Consecutive rows of one genus share that genus's reference band.
                Optional column section: rows are grouped into sections (e.g. by host type); a new section starts
                after a wider gap and a thin rule, with the section name printed above its first row.
  --isolates    census TSV with strain_id and the family columns (one row per isolate; extra rows are ignored).
  --references  census TSV with genus, strain_id and the family columns: exactly the reference genomes to draw (choose
                and de-replicate them before this tool; it does not choose).
  --palette-set a colour set from mamey/data/genus_palette.json.
Outputs in --out (new or empty): K01_chitin_isolate_vs_references.png (600 dpi) / .pdf, _numbers.tsv (one row per isolate
and family: count, reference n / min / median / max, share of references below), RUN_INFO.json with input SHA-256.

Reference-only mode (--references-only; M5_452_k01_references_only, 14 Oct 2026): no isolates. One row per genus of
--references: the reference range, middle half and median of each family, the median printed beside it. Rows are ordered by
--genomes (a TSV with a genus column) when given, else by median GH18 + GH19, highest first. Output stem
K01_chitin_references_by_genus. Without the flag the tool and its output are unchanged.

Left margin: sized from the widest genus band label plus the widest row label (strain and row_note), never below the
former fixed 0.30 of the width, so figures whose labels already fit keep their layout. If the narrower panels would then
make a panel title touch its neighbour, that title wraps onto more lines and the figure grows to keep the plot area.
Labels too long for the print width are refused with the width they need.

A count of zero is drawn, never dropped. "Above the reference range" compares counts only; capacity is not activity.
"""
from __future__ import annotations


def _gname(gn):
    """Genus in italics (mathtext); a family name (ending in -aceae) stays roman."""
    return gn if gn.endswith(("aceae", "aceae bacterium")) else f"$\\it{{{gn}}}$"

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

import argparse
import csv
import hashlib
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.figure_stamp import savefig_metadata  # noqa: E402

TOOL = "chitin_isolate_vs_references"
STEM = "K01_chitin_isolate_vs_references"
PALETTE = ROOT / "mamey" / "data" / "genus_palette.json"
MIN_PT = 8.0
# (column, panel title); "chitinases" is GH18 + GH19
FAMILIES = [("chitinases", "GH18 + GH19\nchitinases"), ("Glyco_hydro_18", "GH18\nchitinase"),
            ("Glyco_hydro_19", "GH19\nchitinase"), ("LPMO_10", "AA10\nLPMO"), ("CBM_5_12", "CBM5/12\nchitin-binding")]
BAND, IQR, MED = "#EFEFEF", "#D0D0D0", "#555555"


def read_tsv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def colours(palette_set):
    d = json.loads(PALETTE.read_text())
    if palette_set and palette_set not in d["sets"]:
        raise SystemExit(f"--palette-set {palette_set!r} not in {PALETTE.name}: {sorted(d['sets'])}")
    out = defaultdict(lambda: d["fallback"], d["default"])
    out.update(d["sets"].get(palette_set or "", {}))
    return out


def value(row, family):
    if family == "chitinases":
        return int(row["Glyco_hydro_18"]) + int(row["Glyco_hydro_19"])
    return int(row[family])


def percentile(v, q):
    s = sorted(v)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def groups(genomes):
    """Consecutive rows of one genus and one section -> (genus, [strains], section)."""
    out = []
    for g in genomes:
        sec = (g.get("section") or "").strip()
        if out and out[-1][0] == g["genus"] and out[-1][2] == sec:
            out[-1][1].append(g["strain"])
        else:
            out.append((g["genus"], [g["strain"]], sec))
    return out


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_width(fig, width_in, text, **kw):
    """Width of one text run at MIN_PT, as a share of the figure width."""
    tx = fig.text(0, 0, text, fontsize=MIN_PT, **kw)
    out = tx.get_window_extent(fig.canvas.get_renderer()).width / (width_in * fig.dpi)
    tx.remove()
    return out


def left_margin(fig, width_in, band_labels, row_labels, floor=0.30, ceiling=0.50):
    """Left edge of the panels, as a share of the figure width: the widest genus band label (drawn from the left edge)
    plus the widest row label (strain and row note, drawn right-aligned against the panels), measured at MIN_PT.
    Never below the former fixed 0.30, so figures whose labels already fit keep their layout."""
    band = max(text_width(fig, width_in, t, linespacing=1.15) for t in band_labels)
    row = max(text_width(fig, width_in, t) for t in row_labels)
    need = 0.005 + band + 0.06 / width_in + row + 0.008
    if need > ceiling:
        raise SystemExit(f"row and genus labels need {need * width_in:.2f} in of the {width_in:g} in print width; "
                         "shorten the row notes or widen --print-width")
    return max(floor, need)


def wrap_line(fig, width_in, line, room):
    """Greedy wrap of one title line at spaces and after hyphens, each piece at most `room` wide where possible."""
    words = re.findall(r"[^\s-]+-?|-", line)
    out = []
    for wd in words:
        if out:
            cand = out[-1] + ("" if out[-1].endswith("-") else " ") + wd
            if text_width(fig, width_in, cand) <= room:
                out[-1] = cand
                continue
        out.append(wd)
    return "\n".join(out)


def fit_titles(fig, width_in, titles, w, gap, right_room):
    """Panel titles are centred over panels w wide, gap apart; the column to the right starts right_room past the last
    panel. A title whose widest line would touch a neighbour is wrapped onto more lines (widest of the pair first).
    Titles that already fit are returned unchanged."""
    pad = 0.03 / width_in
    titles = list(titles)

    def widest(t):
        return max(text_width(fig, width_in, ln) for ln in t.split("\n"))

    for _ in range(4 * len(titles)):
        hw = [widest(t) / 2 for t in titles]
        clash = [(k, k + 1, w + gap - pad) for k in range(len(titles) - 1) if hw[k] + hw[k + 1] > w + gap - pad]
        if hw[-1] > w / 2 + right_room - pad:
            clash.append((len(titles) - 1, None, w / 2 + right_room - pad))
        if not clash:
            return titles
        k, j, room = clash[0]
        order = [k] if j is None else sorted((k, j), key=lambda i: -hw[i])
        for i in order:
            other = 0.0 if j is None else hw[j if i == k else k]
            limit = 2 * (room - other) if j is not None else 2 * room
            new = "\n".join(wrap_line(fig, width_in, ln, limit) for ln in titles[i].split("\n"))
            if new != titles[i]:
                titles[i] = new
                break
        else:
            raise SystemExit(f"panel titles do not fit the {width_in:g} in print width beside the row labels; "
                             "shorten the row notes or widen --print-width")
    raise SystemExit("panel titles could not be fitted")


def _report(info):
    """One terminal summary line, shared by both modes."""
    print(json.dumps({k: info[k] for k in ("figures", "references_per_genus")}))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--genomes", type=Path, help="required unless --references-only (then optional: a genus column sets row order)")
    ap.add_argument("--isolates", type=Path, help="required unless --references-only")
    ap.add_argument("--references-only", action="store_true", help="draw the references by genus, no isolates (M5_452_k01_references_only)")
    ap.add_argument("--references", required=True, type=Path)
    ap.add_argument("--palette-set")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--print-width", type=float, default=7.2, help="inches (7.2 = double column)")
    ap.add_argument("--dpi", type=int, default=600)
    a = ap.parse_args(argv)
    if a.out.exists() and any(a.out.iterdir()):
        raise SystemExit(f"{a.out} holds earlier outputs; use a new folder")
    if a.references_only:
        return references_only(a)
    if a.genomes is None or a.isolates is None:
        raise SystemExit("--genomes and --isolates are required unless --references-only")

    genomes = read_tsv(a.genomes)
    seen = set()
    for g in genomes:
        if g["strain"] in seen:
            raise SystemExit(f"{g['strain']} is listed twice in --genomes")
        seen.add(g["strain"])
    census = {r["strain_id"]: r for r in read_tsv(a.isolates)}
    missing = [g["strain"] for g in genomes if g["strain"] not in census]
    if missing:
        raise SystemExit(f"no census row for: {', '.join(missing)}")
    refs = defaultdict(list)
    for r in read_tsv(a.references):
        if r.get("error"):
            continue
        refs[r["genus"]].append(r)
    no_ref = sorted({g["genus"] for g in genomes if not refs.get(g["genus"])})
    if no_ref:
        raise SystemExit(f"no reference genomes for genus: {', '.join(no_ref)}")
    refv = {(gn, f): [value(r, f) for r in refs[gn]] for gn in refs for f, _ in FAMILIES}
    col = colours(a.palette_set)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    from matplotlib.ticker import MaxNLocator
    from matplotlib.transforms import blended_transform_factory
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
                         "pdf.fonttype": 42, "font.size": MIN_PT})

    y, pos, blocks, sections, last = 0.0, {}, [], [], None
    for gn, ss, sec in groups(genomes):
        if sec and sec != last:
            if blocks:
                y += 0.5
            sections.append((sec, y - 0.85, bool(blocks)))
            y += 0.55
        last = sec
        y0 = y
        for s in ss:
            pos[s] = y
            y += 1
        blocks.append((gn, y0, y - 1))
        y += 0.7
    H = y
    note = {g["strain"]: (g.get("row_note") or "").strip() for g in genomes}
    label = {s: f"{s} ({note[s]})" if note[s] else s for s in pos}
    W = a.print_width
    fig = plt.figure(figsize=(W, 0.24 * H + 1.9))
    band = {gn: f"{_gname(gn)}\n(n = {len(refs[gn])})" for gn, _, _ in blocks}
    L, R, B, T = left_margin(fig, W, band.values(), label.values()), 0.89, 0.17, 0.88
    gap = 0.014
    w = (R - L - gap * (len(FAMILIES) - 1)) / len(FAMILIES)
    titles = fit_titles(fig, W, [t for _, t in FAMILIES], w, gap, 0.008)
    extra = (max(t.count("\n") for t in titles) - 1) * MIN_PT * 1.2 / 72     # inches for title lines past two
    sc = 1.0
    if extra > 0:                                                              # grow the figure; keep the plot area
        h0 = fig.get_figheight()
        fig.set_size_inches(W, h0 + extra)
        sc = h0 / (h0 + extra)
        B, T = B * sc, T * sc
    table = []
    for k, ((f, _), title) in enumerate(zip(FAMILIES, titles)):
        ax = fig.add_axes([L + k * (w + gap), B, w, T - B])
        xmax = max([value(census[s], f) for s in pos] + [max(refv[(gn, f)]) for gn, _, _ in blocks])
        for gn, y0, y1 in blocks:
            v = refv[(gn, f)]
            lo, q1, md, q3, hi = min(v), percentile(v, .25), statistics.median(v), percentile(v, .75), max(v)
            ax.add_patch(Rectangle((lo - 0.25, y0 - 0.42), hi - lo + 0.5, y1 - y0 + 0.84, fc=BAND, ec="none", zorder=1))
            ax.add_patch(Rectangle((q1 - 0.25, y0 - 0.42), q3 - q1 + 0.5, y1 - y0 + 0.84, fc=IQR, ec="none", zorder=2))
            ax.plot([md, md], [y0 - 0.42, y1 + 0.42], color=MED, lw=1.1, zorder=3)
        for g in genomes:
            s, gn = g["strain"], g["genus"]
            v, rv = value(census[s], f), refv[(gn, f)]
            above = v > max(rv)
            ax.scatter([v], [pos[s]], s=26, color=col[gn], edgecolor="black", linewidth=0.5, zorder=5)
            ax.text(v + 0.06 * (xmax + 1) + 0.25, pos[s], f"{v}", va="center", ha="left", fontsize=MIN_PT,
                    fontweight="bold" if above else "normal", color="black" if above else "#444444", zorder=6)
            table.append(dict(isolate=s, genus=gn, family=f, count=v, n_references=len(rv), ref_min=min(rv),
                              ref_median=statistics.median(rv), ref_max=max(rv),
                              share_of_refs_below=round(sum(x < v for x in rv) / len(rv), 2),
                              share_of_refs_at_or_below=round(sum(x <= v for x in rv) / len(rv), 2), above_ref_max=above,
                              cds_searched=census[s].get("cds_searched", "")))
        for sec, ys, rule in sections:
            if rule:
                ax.axhline(ys - 0.15, color="#9A9A9A", lw=0.5, zorder=0)
        ax.set_xlim(-0.8, xmax + 0.26 * (xmax + 1) + 0.8)
        ax.set_ylim(H - 0.3, -0.8)
        ax.set_yticks([])
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=3))
        ax.tick_params(axis="x", labelsize=MIN_PT, length=2)
        ax.set_title(title, fontsize=MIN_PT, pad=4)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        if k == 0:
            tr = blended_transform_factory(fig.transFigure, ax.transData)
            for s in pos:
                ax.text(L - 0.008, pos[s], label[s], transform=tr, ha="right", va="center", fontsize=MIN_PT)
            for sec, ys, rule in sections:
                ax.text(0.005, ys + 0.35, sec, transform=tr, ha="left", va="center", fontsize=MIN_PT,
                        fontweight="bold", color="#333333")
            for gn, y0, y1 in blocks:
                ax.text(0.005, (y0 + y1) / 2, band[gn], transform=tr, ha="left",
                        va="center", fontsize=MIN_PT, color=col[gn], linespacing=1.15)
    axr = fig.add_axes([R + 0.008, B, 1 - R - 0.01, T - B])
    axr.set_ylim(H - 0.3, -0.8)
    axr.axis("off")
    axr.text(0.0, -1.2, "proteins\nsearched", fontsize=MIN_PT, ha="left", va="bottom", color="#444444")
    for s in pos:
        cds = census[s].get("cds_searched", "")
        axr.text(0.0, pos[s], f"{int(cds):,}" if str(cds).isdigit() else "", fontsize=MIN_PT, ha="left", va="center",
                 color="#666666")
    fig.text(0.5 * (L + R), B - 0.075 * sc, "Proteins per genome with a Pfam hit", ha="center", fontsize=MIN_PT)
    handles = [Rectangle((0, 0), 1, 1, fc=BAND, ec="#BBBBBB", lw=0.4), Rectangle((0, 0), 1, 1, fc=IQR, ec="none"),
               Line2D([0], [0], color=MED, lw=1.1),
               Line2D([0], [0], marker="o", ls="", markerfacecolor="#999999", markeredgecolor="black",
                      markeredgewidth=0.5, ms=5)]
    fig.legend(handles, ["range of reference genomes", "middle half of reference genomes", "reference median",
                         "isolate (count; bold above the reference range)"], loc="lower center",
               bbox_to_anchor=(0.5, 0.0), ncol=2, fontsize=MIN_PT, frameon=False, handlelength=1.4, columnspacing=1.2)

    a.out.mkdir(parents=True, exist_ok=True)
    made = []
    for ext in (".png", ".pdf"):
        p = a.out / f"{STEM}{ext}"
        fig.savefig(p, dpi=a.dpi, metadata=savefig_metadata(p, TOOL))
        made.append(p.name)
    plt.close(fig)
    with open(a.out / f"{STEM}_numbers.tsv", "w", newline="") as fh:
        wr = _SafeDictWriter(fh, fieldnames=list(table[0]), delimiter="\t", lineterminator="\n")
        wr.writeheader()
        wr.writerows(table)
    info = dict(tool=TOOL, print_width_in=W, sections=[sec for sec, _, _ in sections], palette_set=a.palette_set or "default", figures=made,
                isolates=list(pos), references_per_genus={gn: len(refs[gn]) for gn, _, _ in blocks},
                inputs={k: dict(path=str(p), sha256=sha(p)) for k, p in
                        (("genomes", a.genomes), ("isolates", a.isolates), ("references", a.references))})
    (a.out / "RUN_INFO.json").write_text(json.dumps(info, indent=1) + "\n")
    _report(info)
    return 0


REF_STEM = "K01_chitin_references_by_genus"


def references_only(a):
    """M5_452_k01_references_only: one row per genus of --references (range, middle half, median per family); no isolates."""
    refs = defaultdict(list)
    for r in read_tsv(a.references):
        if r.get("error"):
            continue
        refs[r["genus"]].append(r)
    if not refs:
        raise SystemExit("no reference rows")
    if a.genomes:
        order = []
        for g in read_tsv(a.genomes):
            if g["genus"] not in order:
                order.append(g["genus"])
        missing = [g for g in order if g not in refs]
        if missing:
            raise SystemExit(f"no reference genomes for genus: {', '.join(missing)}")
    else:
        order = sorted(refs, key=lambda gn: (-statistics.median(value(r, "chitinases") for r in refs[gn]), gn))
    col = colours(a.palette_set)
    refv = {(gn, f): [value(r, f) for r in refs[gn]] for gn in order for f, _ in FAMILIES}

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    from matplotlib.ticker import MaxNLocator
    from matplotlib.transforms import blended_transform_factory
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
                         "pdf.fonttype": 42, "font.size": MIN_PT})
    pos = {gn: i for i, gn in enumerate(order)}
    H = len(order)
    W = a.print_width
    fig = plt.figure(figsize=(W, 0.26 * H + 1.7))
    labels = {gn: f"{_gname(gn)} (n = {len(refs[gn])})" for gn in order}
    rend = fig.canvas.get_renderer()                                            # left margin from the measured widest label
    widest = max(fig.text(0, 0, t, fontsize=MIN_PT).get_window_extent(rend).width for t in labels.values()) / (W * fig.dpi)
    for t in list(fig.texts): t.remove()
    L, R, B, T = min(0.45, widest + 0.025), 0.98, 0.16, 0.88
    gap = 0.014
    w = (R - L - gap * (len(FAMILIES) - 1)) / len(FAMILIES)
    table = []
    for k, (f, title) in enumerate(FAMILIES):
        ax = fig.add_axes([L + k * (w + gap), B, w, T - B])
        xmax = max(max(refv[(gn, f)]) for gn in order)
        for gn in order:
            v, y = refv[(gn, f)], pos[gn]
            lo, q1, md, q3, hi = min(v), percentile(v, .25), statistics.median(v), percentile(v, .75), max(v)
            ax.add_patch(Rectangle((lo - 0.25, y - 0.38), hi - lo + 0.5, 0.76, fc=BAND, ec="none", zorder=1))
            ax.add_patch(Rectangle((q1 - 0.25, y - 0.38), q3 - q1 + 0.5, 0.76, fc=IQR, ec="none", zorder=2))
            ax.plot([md, md], [y - 0.38, y + 0.38], color=MED, lw=1.1, zorder=3)
            ax.text(hi + 0.25 + 0.04 * (xmax + 1), y, f"{md:g}", va="center", ha="left", fontsize=MIN_PT, color="#444444", zorder=6)
            table.append(dict(genus=gn, family=f, n_references=len(v), ref_min=lo, ref_q1=q1, ref_median=md, ref_q3=q3, ref_max=hi))
        ax.set_xlim(-0.8, xmax + 0.22 * (xmax + 1) + 0.8)
        ax.set_ylim(H - 0.4, -0.6)
        ax.set_yticks([])
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=3))
        ax.tick_params(axis="x", labelsize=MIN_PT, length=2)
        ax.set_title(title, fontsize=MIN_PT, pad=4)
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        if k == 0:
            tr = blended_transform_factory(fig.transFigure, ax.transData)
            for gn in order:
                ax.text(L - 0.008, pos[gn], labels[gn], transform=tr, ha="right", va="center",
                        fontsize=MIN_PT, color="black")
    fig.text(0.5 * (L + R), B - 0.07, "Proteins per genome with a Pfam hit (number: median)", ha="center", fontsize=MIN_PT)
    handles = [Rectangle((0, 0), 1, 1, fc=BAND, ec="#BBBBBB", lw=0.4), Rectangle((0, 0), 1, 1, fc=IQR, ec="none"),
               Line2D([0], [0], color=MED, lw=1.1)]
    fig.legend(handles, ["range of reference genomes", "middle half of reference genomes", "median"], loc="lower center",
               bbox_to_anchor=(0.5, 0.0), ncol=3, fontsize=MIN_PT, frameon=False, handlelength=1.4, columnspacing=1.2)
    a.out.mkdir(parents=True, exist_ok=True)
    made = []
    for ext in (".png", ".pdf"):
        p = a.out / f"{REF_STEM}{ext}"
        fig.savefig(p, dpi=a.dpi, metadata=savefig_metadata(p, TOOL))
        made.append(p.name)
    plt.close(fig)
    with open(a.out / f"{REF_STEM}_numbers.tsv", "w", newline="") as fh:
        wr = _SafeDictWriter(fh, fieldnames=list(table[0]), delimiter="\t", lineterminator="\n")
        wr.writeheader()
        wr.writerows(table)
    ins = [("references", a.references)] + ([("genomes", a.genomes)] if a.genomes else [])
    info = dict(tool=TOOL, mode="references_only", print_width_in=W, palette_set=a.palette_set or "default", figures=made,
                genera=order, references_per_genus={gn: len(refs[gn]) for gn in order},
                inputs={k: dict(path=str(p), sha256=sha(p)) for k, p in ins})
    (a.out / "RUN_INFO.json").write_text(json.dumps(info, indent=1) + "\n")
    _report(info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
