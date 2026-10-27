#!/usr/bin/env python3
"""Within-genus pairwise 16S rRNA gene identity (figure type T02): compute the pair table, then draw it.

Two steps, each with explicit inputs:

  pairs   --fasta (one 16S per isolate) and --genera (strain, genus) -> a pair table.
          Global alignment with free end gaps (match 2, mismatch -3, gap open -5, extend -2).
          Identity = identical columns / compared columns inside the overlap (first to last column
          where both sequences have a base). Internal gaps count as differences. Columns with a
          non-ACGT base in either sequence are left out of both counts. Pairs with fewer than
          --min-overlap compared columns are kept and flagged short_overlap = 1.
  render  --pairs (that table) -> PNG + PDF + numbers table + run record.
          Same-genus pairs with short_overlap = 0 only. --layout facets draws one histogram per
          genus; --layout overlay draws every genus in one panel on a square-root count axis, so
          a genus with one pair stays visible beside one with thousands. Bins are 0.25 points,
          closed on the right, anchored at 100%. The x-axis starts at the lowest plotted value.

Genus names are used as given in --genera (as deposited). Colours come from
mamey/data/genus_palette.json (--palette-set). Text is held to the 8 pt floor at the print width.
"""
from __future__ import annotations

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import argparse
import csv
import hashlib
import itertools
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.figure_stamp import stamp_file
from tools._min_text_check import add_args as _mt_args, enforce as _mt_enforce
TOOL = "taxonomy_T02_within_genus"
PAIR_COLUMNS = ["a", "b", "genus_a", "genus_b", "len_a", "len_b", "overlap_columns", "compared",
                "identical", "percent_identity", "short_overlap"]
ACGT = set("ACGT")
R_SCRIPT = r'''suppressPackageStartupMessages({library(ggplot2); library(ggtext)})
a <- commandArgs(TRUE)
source(a[1]); d <- read.delim(a[2], stringsAsFactors=FALSE, check.names=FALSE)
paldata <- read.delim(a[3], stringsAsFactors=FALSE); pal <- setNames(paldata$colour, paldata$genus)
layout <- a[4]; out <- a[5]; dpi <- as.numeric(a[6]); xmin <- as.numeric(a[9])
d$genus <- factor(d$genus, levels = paldata$genus)
iso <- read.delim(a[10], stringsAsFactors=FALSE)
lab <- setNames(paste0(ifelse(grepl("aceae( bacterium)?$", iso$genus), iso$genus, paste0("<i>", iso$genus, "</i>")), " (", iso$isolates, " isolates, ", format(iso$pairs, big.mark = ","), " pairs)"), iso$genus)
br <- function(l) { s <- seq(ceiling(xmin), 100, by = if (100 - xmin > 5) 2 else 1); s }
AX <- theme(axis.title = element_text(colour = PUB_INK), panel.grid.major.x = element_blank(),
            axis.title.y = element_text(margin = margin(r = 4)), axis.title.x = element_text(margin = margin(t = 4)),
            plot.margin = margin(3, 6, 3, 3))
if (layout == "facets") {
  strip <- setNames(paste0(ifelse(grepl("aceae( bacterium)?$", iso$genus), iso$genus, paste0("<i>", iso$genus, "</i>")), "<br>", iso$isolates, " isolates, ", format(iso$pairs, big.mark = ","), " pairs"), iso$genus)
  p <- ggplot(d, aes(x = percent_identity, fill = genus)) +
    geom_histogram(binwidth = 0.25, boundary = 100, closed = "right", colour = "white", linewidth = 0.1) +
    facet_wrap(~ genus, ncol = 2, scales = "free_y", labeller = labeller(genus = strip)) +
    scale_fill_manual(values = pal, guide = "none") +
    scale_x_continuous(breaks = br, labels = function(x) paste0(x, "%")) + coord_cartesian(xlim = c(xmin, 100)) +
    scale_y_continuous(breaks = function(l) unique(floor(scales::pretty_breaks(3)(l))), expand = expansion(mult = c(0, 0.05))) +
    labs(x = "Pairwise 16S rRNA gene identity", y = "Isolate pairs") +
    theme_pub(base = 8) + AX + theme(strip.text = element_markdown(face = "bold", hjust = 0, lineheight = 1.05, margin = margin(b = 3)),
                                    panel.spacing.x = unit(0.35, "cm"), panel.spacing.y = unit(0.3, "cm"))
  w <- 3.5; h <- 3.6
} else {
  # Overlay: largest genus drawn first so the smaller genera sit on top.
  ord <- names(sort(table(d$genus), decreasing = TRUE)); d$draw <- match(as.character(d$genus), ord); d <- d[order(d$draw), ]
  p <- ggplot(d, aes(x = percent_identity, fill = genus)) +
    geom_histogram(binwidth = 0.25, boundary = 100, closed = "right", position = "identity", colour = "white", linewidth = 0.1) +
    scale_fill_manual(values = pal, breaks = paldata$genus, labels = lab[paldata$genus], name = NULL) +
    scale_x_continuous(breaks = br, labels = function(x) paste0(x, "%")) + coord_cartesian(xlim = c(xmin, 100)) +
    scale_y_sqrt(breaks = function(l) { b <- c(0, 1, 5, 10, 25, 50, 100, 200, 400, 800); b[b <= l[2]] }, expand = expansion(mult = c(0, 0.05))) +
    labs(x = "Pairwise 16S rRNA gene identity", y = "Isolate pairs (square-root scale)") +
    guides(fill = guide_legend(ncol = 1)) +
    theme_pub(base = 8) + AX + theme(legend.position = "bottom", legend.text = element_markdown(), legend.key.size = unit(8, "pt"))
  w <- 3.5; h <- 3.6
}
source(a[11]); mt_save(p, out, w, h, list(min_text_pt = as.numeric(a[7]), print_width = if (a[8] == "auto") NULL else as.numeric(a[8]), dpi = dpi))
'''


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_fasta(path: Path) -> dict[str, str]:
    seqs: dict[str, list[str]] = {}
    cur = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(">"):
            cur = line[1:].split()[0]
            if cur in seqs:
                raise ValueError(f"{path}: duplicate record {cur!r}")
            seqs[cur] = []
        elif line and cur is not None:
            seqs[cur].append(line.upper())
    return {k: "".join(v) for k, v in seqs.items()}


def read_genera(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if not {"strain", "genus"} <= set(reader.fieldnames or []):
            raise ValueError(f"{path}: needs columns strain, genus")
        out: dict[str, str] = {}
        for row in reader:
            s, g = row["strain"].strip(), row["genus"].strip()
            if not s or not g:
                raise ValueError(f"{path}: empty strain or genus")
            if s in out:
                raise ValueError(f"{path}: duplicate strain {s!r}")
            out[s] = g
    return out


def pair_row(a: str, b: str, sa: str, sb: str, aligner, min_overlap: int) -> dict:
    aln = aligner.align(sa, sb)[0]
    x, y = aln[0], aln[1]
    both = [i for i in range(len(x)) if x[i] != "-" and y[i] != "-"]
    row = {"a": a, "b": b, "len_a": len(sa), "len_b": len(sb)}
    if not both:
        row.update(overlap_columns=0, compared=0, identical=0, percent_identity="NA", short_overlap=1)
        return row
    lo, hi = both[0], both[-1]
    comp = ident = 0
    for i in range(lo, hi + 1):
        p, q = x[i], y[i]
        if (p != "-" and p not in ACGT) or (q != "-" and q not in ACGT):
            continue
        comp += 1
        ident += p == q
    row.update(overlap_columns=hi - lo + 1, compared=comp, identical=ident,
               percent_identity=f"{100 * ident / comp:.3f}" if comp else "NA", short_overlap=int(comp < min_overlap))
    return row


def cmd_pairs(args) -> None:
    from Bio import Align
    seqs = read_fasta(args.fasta)
    genera = read_genera(args.genera)
    missing = sorted(set(genera) - set(seqs))
    if missing:
        raise ValueError(f"strains without a sequence in {args.fasta}: {missing}")
    for s in genera:
        if not re.fullmatch(r"[ACGTRYKMSWBDHVN]+", seqs[s]):
            raise ValueError(f"{s}: sequence holds characters outside IUPAC nucleotide codes")
    if args.out.exists():
        raise FileExistsError(f"refusing to overwrite {args.out}")
    if args.same_genus_only:
        combos = [(a, b) for a, b in itertools.combinations(sorted(genera), 2) if genera[a] == genera[b]]
    else:
        combos = list(itertools.combinations(sorted(genera), 2))
    aligner = Align.PairwiseAligner(mode="global", match_score=2, mismatch_score=-3, open_gap_score=-5,
                                    extend_gap_score=-2, end_gap_score=0)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = _SafeDictWriter(fh, PAIR_COLUMNS, delimiter="\t")
        w.writeheader()
        for a, b in combos:
            row = pair_row(a, b, seqs[a], seqs[b], aligner, args.min_overlap)
            row.update(genus_a=genera[a], genus_b=genera[b])
            w.writerow(row)
    Path(str(args.out) + ".run.json").write_text(json.dumps({
        "tool": TOOL, "step": "pairs", "pairs": len(combos), "isolates": len(genera), "min_overlap": args.min_overlap,
        "same_genus_only": args.same_genus_only,
        "inputs": [{"path": str(p.resolve()), "sha256": _sha(p)} for p in (args.fasta, args.genera, Path(__file__))],
        "output_sha256": _sha(args.out)}, indent=2) + "\n")


def load_pairs(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        need = {"a", "b", "genus_a", "genus_b", "percent_identity", "short_overlap"}
        if not need <= set(reader.fieldnames or []):
            raise ValueError(f"{path}: missing columns {sorted(need - set(reader.fieldnames or []))}")
        rows = list(reader)
    seen = set()
    for r in rows:
        k = tuple(sorted((r["a"], r["b"])))
        if r["a"] == r["b"] or k in seen:
            raise ValueError(f"{path}: self or duplicate pair {k}")
        seen.add(k)
    return rows


def cmd_render(args) -> None:
    palette_path = ROOT / "mamey/data/genus_palette.json"
    config = json.loads(palette_path.read_text())
    colours = dict(config["default"])
    colours.update(config["sets"].get(args.palette_set or "", {}))
    rows = load_pairs(args.pairs)
    keep_genera = set(args.genus) if args.genus else None
    plotted, dropped = [], Counter()
    for r in rows:
        if r["genus_a"] != r["genus_b"]:
            dropped["different_genus"] += 1; continue
        if keep_genera is not None and r["genus_a"] not in keep_genera:
            dropped["genus_not_selected"] += 1; continue
        if str(r["short_overlap"]).strip() != "0":
            dropped["short_overlap"] += 1; continue
        if str(r["percent_identity"]).strip() in {"", "NA", "NaN", "nan"}:
            dropped["no_identity"] += 1; continue
        v = float(r["percent_identity"])
        if not math.isfinite(v) or not 0 <= v <= 100:
            raise ValueError(f"{r['a']}/{r['b']}: identity outside 0..100")
        plotted.append({"a": r["a"], "b": r["b"], "genus": r["genus_a"], "percent_identity": v})
    if not plotted:
        raise ValueError("no same-genus pairs to draw")
    present = Counter(p["genus"] for p in plotted)
    order = args.genus_order.split(",") if args.genus_order else sorted(present, key=lambda g: (-present[g], g))
    order = [g for g in order if g in present] + sorted(set(present) - set(order))
    isolates = {g: len({s for p in plotted if p["genus"] == g for s in (p["a"], p["b"])}) for g in order}
    lo = min(p["percent_identity"] for p in plotted)
    xmin = args.x_min if args.x_min is not None else max(0.0, math.floor(lo * 4) / 4 - 0.25)
    if xmin > lo:
        raise ValueError(f"--x-min {xmin} would hide pairs down to {lo:.3f}%")
    out = args.out
    products = [out.with_suffix(".png"), out.with_suffix(".pdf"), out.with_name(out.name + "_numbers.tsv"),
                out.with_name(out.name + "_run.json")]
    if any(p.exists() for p in products):
        raise FileExistsError("refusing to overwrite figure or sidecar")
    rscript = shutil.which("Rscript")
    if not rscript:
        raise RuntimeError("Rscript is required for the bundle ggplot layout")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=TOOL + "_", dir=out.parent) as tmp:
        tmp = Path(tmp)
        (tmp / "render.R").write_text(R_SCRIPT)
        with (tmp / "values.tsv").open("w", newline="") as fh:
            w = _SafeDictWriter(fh, ["a", "b", "genus", "percent_identity"], delimiter="\t"); w.writeheader(); w.writerows(plotted)
        with (tmp / "palette.tsv").open("w", newline="") as fh:
            w = _SafeWriter(fh, delimiter="\t"); w.writerow(["genus", "colour"])
            w.writerows((g, colours.get(g, config["fallback"])) for g in order)
        with (tmp / "counts.tsv").open("w", newline="") as fh:
            w = _SafeWriter(fh, delimiter="\t"); w.writerow(["genus", "isolates", "pairs"])
            w.writerows((g, isolates[g], present[g]) for g in order)
        subprocess.run([rscript, str(tmp / "render.R"), str(ROOT / "tools/sapote_pub_layout.R"), str(tmp / "values.tsv"),
                        str(tmp / "palette.tsv"), args.layout, str(out), str(args.dpi), str(args.min_text_pt),
                        str(args.print_width or "auto"), str(xmin), str(tmp / "counts.tsv"),
                        str(ROOT / "tools/sapote_min_text.R")], check=True)
        _mt_enforce(out.with_suffix(".pdf"), args.min_text_pt)
    for p in products[:2]:
        stamp_file(p, TOOL)
    nums = [("pairs_in_table", len(rows)), ("pairs_plotted", len(plotted))]
    nums += [(f"dropped:{k}", v) for k, v in sorted(dropped.items())]
    for g in order:
        vals = sorted(p["percent_identity"] for p in plotted if p["genus"] == g)
        nums += [(f"genus:{g}:isolates", isolates[g]), (f"genus:{g}:pairs", present[g]),
                 (f"genus:{g}:min", f"{vals[0]:.3f}"), (f"genus:{g}:max", f"{vals[-1]:.3f}")]
    nums.append(("x_min", f"{xmin:.2f}"))
    with products[2].open("w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t"); w.writerow(["metric", "value"]); w.writerows(nums)
    bound = [{"path": str(p.resolve()), "sha256": _sha(p)} for p in
             (args.pairs, palette_path, ROOT / "tools/sapote_pub_layout.R", ROOT / "tools/sapote_min_text.R",
              ROOT / "tools/_min_text_check.py", Path(__file__))]
    products[3].write_text(json.dumps({"renderer": TOOL, "layout": args.layout, "palette_set": args.palette_set,
                                       "x_min": xmin, "genus_order": order, "inputs": bound}, indent=2) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="step", required=True)
    p1 = sub.add_parser("pairs", help="compute the pairwise identity table")
    p1.add_argument("--fasta", type=Path, required=True, help="one 16S record per isolate; record ID = strain")
    p1.add_argument("--genera", type=Path, required=True, help="TSV with strain, genus (as deposited)")
    p1.add_argument("--out", type=Path, required=True)
    p1.add_argument("--min-overlap", type=int, default=500)
    p1.add_argument("--same-genus-only", action="store_true", help="align only pairs within a genus")
    p2 = sub.add_parser("render", help="draw the within-genus histogram")
    p2.add_argument("--pairs", type=Path, required=True)
    p2.add_argument("--out", type=Path, required=True, help="output stem, without suffix")
    p2.add_argument("--layout", choices=["facets", "overlay"], default="facets")
    p2.add_argument("--genus", action="append", help="draw only this genus (repeatable)")
    p2.add_argument("--genus-order", help="comma-separated order; default largest first")
    p2.add_argument("--palette-set", choices=["moss", "attine"])
    p2.add_argument("--x-min", type=float, help="axis start; default the lowest plotted bin")
    p2.add_argument("--dpi", type=int, default=600)
    _mt_args(p2)
    args = ap.parse_args()
    try:
        cmd_pairs(args) if args.step == "pairs" else cmd_render(args)
    except (ValueError, FileExistsError, RuntimeError, subprocess.CalledProcessError) as exc:
        ap.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
