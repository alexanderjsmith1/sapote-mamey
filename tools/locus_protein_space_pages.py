#!/usr/bin/env python3
"""Protein-space pages of one gene-cluster locus: its proteins in each protein set, among reference and MIBiG proteins.

One command for what the locus pages and the Chapter 5 supplement did with a dated-folder wrapper. It draws, with
`tools/protein_pcoa_render.py` and saved coordinates only (nothing is refitted):
- one page per layout, t-SNE and TriMap by default (PCoA only when named in --layouts);
- every set that holds a protein of the locus, in a grid;
- the locus as its own cohort: the strain's other regions are dropped, so only the locus proteins are drawn in color, by
  the renderer's identity tiers;
- reference and MIBiG points enlarged (--ref-point-scale, default 2) so they print;
- no point labels by default. --labels names labels each locus protein with its protein-search name (a name, never an
  index number); a protein with no name is drawn and not labeled.

Inputs
  --identity   "strain / full contig / regionNNN / BGC alias" of the locus
  --zip        that strain's antiSMASH zip (its region files name the regions to drop)
  --kits TSV   set, kit: the kit folder of each set (holding out_<SET>/PCOA_<SET>.tsv, RUN and META files)
  --embeddings TSV  set, layout (tsne or trimap), path: saved coordinates for each set
  --cohort-table TSV  strain, cohort: the renderer's cohort table; the locus strain becomes the cohort "locus"
  --set-names TSV  set, title (optional)
  --gene-names TSV  locus_tag, name (with --labels names)
Kit points name their region as <strain>__<contig>.<regionNNN>.gbk in the origin column.

Writes <out>/inputs/ (the derived cohort, drop and label files), <out>/<layout>/ (the renderer's pages and receipts) and
<out>/LOCUS_SPACE_PAGES.json.

usage: locus_protein_space_pages.py --identity ID --zip ZIP --kits TSV --embeddings TSV --cohort-table TSV --out DIR
       [--layouts tsne,trimap] [--labels none|names --gene-names TSV] [--set-names TSV] [--ref-point-scale X]
       [--print-width IN] [--grid RxC]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # bundle root, for a bare-script run from tools/
from mamey.logging_setup import get_logger as _get_logger  # noqa: E402

_OUT = _get_logger(__name__)


TOOLS = Path(__file__).resolve().parent
LAYOUTS = ("tsne", "trimap", "pcoa")


def table(path, need):
    rows = list(csv.DictReader(open(path, newline=""), delimiter="\t"))
    if not rows or any(c not in rows[0] for c in need):
        raise ValueError(f"{path}: needs columns {need}")
    return rows


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def grid_for(n: int) -> str:
    return "1x1" if n == 1 else "2x1" if n == 2 else "2x2" if n <= 4 else "3x2" if n <= 6 else "3x3"


def locus_inputs(a, inp):
    """Derived inputs: cohort table (locus strain -> 'locus'), regions to drop, sets holding the locus, label table."""
    parts = [x.strip() for x in a.identity.split(" / ")]
    if len(parts) != 4 or not all(parts):
        raise ValueError(f"--identity must be 'strain / contig / regionNNN / alias', not {a.identity!r}")
    strain, contig, region, alias = parts
    origin = f"{strain}__{contig}.{region}.gbk"
    with zipfile.ZipFile(a.zip) as zf:
        regions = [f"{strain}__" + re.search(r"([^/]+\.region\d{3}\.gbk)$", n).group(1) for n in zf.namelist()
                   if re.search(r"\.region\d{3}\.gbk$", n) and "__MACOSX" not in n]
    if origin not in regions:
        raise ValueError(f"{origin} is not a region file of {a.zip}")
    inp.mkdir(parents=True, exist_ok=True)
    cohort = table(a.cohort_table, ["strain", "cohort"])
    with open(inp / "COHORT.tsv", "w") as fh:
        fh.write("strain\tcohort\n" + "".join(f"{r['strain']}\t{'locus' if r['strain'] == strain else r.get('cohort', '')}\n" for r in cohort))
    (inp / "DROP_OTHER_REGIONS.txt").write_text("".join(f"{o}\n" for o in regions if o != origin))
    kits = {r["set"]: r["kit"] for r in table(a.kits, ["set", "kit"])}
    emb = {(r["set"], r["layout"]): r["path"] for r in table(a.embeddings, ["set", "layout", "path"])}
    names = {r["locus_tag"]: r["name"] for r in table(a.gene_names, ["locus_tag", "name"])} if a.labels == "names" else {}
    sets, labels, skipped = [], {}, []
    for s, kit in kits.items():
        p = Path(kit) / f"out_{s}" / f"PCOA_{s}.tsv"
        if not p.is_file():
            skipped.append((s, "no PCOA table in kit")); continue
        mine = [r for r in csv.DictReader(open(p, newline=""), delimiter="\t") if r.get("origin") == origin]
        if not mine:
            continue
        missing = [lay for lay in a.layouts if lay != "pcoa" and not Path(emb.get((s, lay), "")).is_file()]
        if missing:
            skipped.append((s, f"no saved {'/'.join(missing)} coordinates")); continue
        sets.append(s)
        for r in mine:
            if names.get(r.get("locus_tag", "")):
                labels[r["id"]] = names[r["locus_tag"]]
    # The label list is always passed: with --labels none it holds one sentinel id that matches no point, so the renderer's
    # distance rule (which would label outliers by strain) is not used and nothing is labeled.
    rows = labels or {"__no_point_has_this_id__": ""}
    (inp / "LABEL_IDS.tsv").write_text("id\ttext\n" + "".join(f"{k}\t{v}\n" for k, v in rows.items()))
    return dict(strain=strain, contig=contig, region=region, alias=alias, origin=origin, sets=sets, kits=kits, emb=emb,
                labels=len(labels), skipped=skipped)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for req in ("--identity", "--zip", "--kits", "--embeddings", "--cohort-table", "--out"):
        ap.add_argument(req, required=True)
    ap.add_argument("--layouts", default="tsne,trimap", help="comma-separated, from tsne, trimap, pcoa (default tsne,trimap)")
    ap.add_argument("--labels", choices=("none", "names"), default="none")
    ap.add_argument("--gene-names", help="TSV locus_tag, name (with --labels names)")
    ap.add_argument("--set-names")
    ap.add_argument("--ref-point-scale", type=float, default=2.0)
    ap.add_argument("--cohort-point-scale", type=float, default=2.5, help="locus protein points X times the default size")
    ap.add_argument("--print-width", type=float, default=6.5)
    ap.add_argument("--grid", help="RxC; default from the number of sets")
    ap.add_argument("--panel-height", type=float, help="panel height in inches (the renderer's default when omitted)")
    ap.add_argument("--legend-in-empty-slot", action="store_true", help="put the legend in an empty grid slot (long legend lines may not fit)")
    ap.add_argument("--min-text-pt", type=float, default=8.0)
    a = ap.parse_args(argv)
    a.layouts = [x.strip() for x in a.layouts.split(",") if x.strip()]
    if not a.layouts or any(x not in LAYOUTS for x in a.layouts):
        ap.error(f"--layouts must name layouts from {LAYOUTS}")
    if a.labels == "names" and not a.gene_names:
        ap.error("--labels names needs --gene-names")
    out = Path(a.out).resolve()
    if out.exists():
        _OUT.error(f"refused: {out} exists; give a new --out")
        return 2
    try:
        info = locus_inputs(a, out / "inputs")
    except (ValueError, OSError, zipfile.BadZipFile) as e:
        _OUT.error(f"refused: {e}")
        return 2
    if not info["sets"]:
        _OUT.error(f"refused: no protein set holds a protein of {a.identity}; skipped: {info['skipped']}")
        return 2
    tag = f"{info['strain']} {info['contig']} {info['region']} {info['alias']}"   # cohort key; the full identity is in the caption
    short = f"{info['strain']}_{info['contig'].split('_length_')[0]} {info['alias']}"   # panel label: the short form used in text
    grid = a.grid or grid_for(len(info["sets"]))
    first_kit = info["kits"][info["sets"][0]]
    runs = {}
    for lay in a.layouts:
        c = [sys.executable, "-B", str(TOOLS / "protein_pcoa_render.py"), "--kit", first_kit]
        for s in info["sets"]:
            c += ["--set", s, "--set-kit", f"{s}={info['kits'][s]}"]
        c += ["--out", str(out / lay), "--cohort-table", str(out / "inputs" / "COHORT.tsv"), "--panel", f"{tag}=locus",
              "--panel-label", f"{tag}={short} proteins", "--drop-origins", str(out / "inputs" / "DROP_OTHER_REGIONS.txt"),
              "--label-below", "70", "--mid-below", "85", "--renderer", "r", "--min-text-pt", str(a.min_text_pt),
              "--print-width", str(a.print_width), "--page", lay, "--page-grid", grid,
              "--ref-point-scale", str(a.ref_point_scale), "--cohort-point-scale", str(a.cohort_point_scale),
              "--caption-note", f"Proteins of {a.identity} only; the strain's other regions are not drawn."]
        if a.set_names:
            c += ["--set-names", a.set_names]
        if a.panel_height:
            c += ["--panel-height", str(a.panel_height)]
        if a.legend_in_empty_slot:
            c += ["--legend-in-empty-slot"]
        c += ["--label-ids", str(out / "inputs" / "LABEL_IDS.tsv")]
        if lay != "pcoa":
            for s in info["sets"]:
                c += ["--embedding-table", f"{s}={info['emb'][(s, lay)]}"]
        p = subprocess.run(c, capture_output=True, text=True)
        (out / f"{lay}.log").write_text(p.stdout + "\n--- stderr ---\n" + p.stderr)
        runs[lay] = dict(exit=p.returncode, pages=sorted(f.name for f in (out / lay).glob("PAGE_GRID_*.pdf")) if (out / lay).exists() else [],
                         command=c)
    receipt = dict(tool="tools/locus_protein_space_pages.py", identity=a.identity, origin=info["origin"], sets=info["sets"],
                   sets_skipped=info["skipped"], labels=a.labels, labeled_points=info["labels"], grid=grid,
                   ref_point_scale=a.ref_point_scale, cohort_point_scale=a.cohort_point_scale, layouts=runs,
                   inputs_sha256={str(Path(p).resolve()): sha256(p) for p in (a.zip, a.kits, a.embeddings, a.cohort_table,
                                                                            a.gene_names, a.set_names) if p})
    (out / "LOCUS_SPACE_PAGES.json").write_text(json.dumps(receipt, indent=1) + "\n")
    bad = [lay for lay, r in runs.items() if r["exit"] or not r["pages"]]
    if bad:
        _OUT.error(f"refused: layouts {bad} did not draw; see {out}/*.log")
        return 2
    _OUT.info(f"{a.identity}: {len(info['sets'])} sets, {len(a.layouts)} layout(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
