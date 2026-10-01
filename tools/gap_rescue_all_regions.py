#!/usr/bin/env python3
"""gap_rescue_all_regions.py — run tools/gap_directed_rescue.py on every antiSMASH region of one genome.

Reader-side and NON-SCORING. The genome is read once. Each region gets its reference from the region's
KnownClusterBlast rank-1 MIBiG hit; every region without one is searched in a single DIAMOND call against the MIBiG
protein database, and takes the MIBiG cluster with the most region proteins at >= 35% identity over >= 50% of the
protein (at least 2, one of them biosynthetic; reference <= 250 kb; a tie with the runner-up is flagged). Regions with
neither are listed, not run. Each run searches the whole genome, checks split genes and partner contigs, and draws the
clinker-style map (see gap_directed_rescue.py).

Outputs in --out: one folder per region (<BGC>_vs_<accession>), SUMMARY.tsv (+ SUMMARY.xlsx with openpyxl),
<label>_all_locus_maps.pdf (with pypdf), gap_rescue_proteins.faa (the protein ids every hit table uses) and
run_receipt.json.

CLI:
  python tools/gap_rescue_all_regions.py --zip <antiSMASH.zip> --label <strain> --out <dir> \
         --mibig-dir <MIBiG gbk folder> --mibig-db <MIBiG proteins .dmnd> [--mibig-names <index.json|tsv>] \
         [--pfam <Pfam-A.hmm>] [--edge-only] [--sensitivity ultra-sensitive] [--threads 4] [--no-figure]

Claim-safety: homology is similarity, not product identity; a chosen reference is the closest characterised cluster
by protein homology, not the product; no contigs are joined.
"""
from __future__ import annotations

import os as _os, sys as _sys  # resolve the tools-local modules from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import gap_directed_rescue as gdr  # noqa: E402

import argparse
import csv
import json
import logging
from pathlib import Path

_LOG = logging.getLogger(__name__)

SUMMARY_COLS = ["bgc", "contig_edge", "check", "reference", "reference_name", "reference_source", "reference_genes",
                "in_core", "found_clearly_elsewhere", "partner_verdicts", "clear_splits", "split_genes", "folder"]


def run_all(zip_path, label, out, mibig_dir, mibig_db=None, names=None, pfam=None, edge_only=False,
            sensitivity=gdr.SENSITIVITY_DEFAULT, threads=4, figure=True, discovery_hits=None) -> list[dict]:
    prots, regions = gdr.load_genome(zip_path, label)
    out.mkdir(parents=True, exist_ok=True)
    (out / "gap_rescue_proteins.faa").write_text("".join(f">{k}\n{v['aa']}\n" for k, v in prots.items()))
    names = names or {}
    sens = None if sensitivity == "default" else sensitivity
    rows, todo, chosen = [], {}, {}
    for core in regions:
        ident = core["identity"]
        if ident.endswith("IDENTITY_HOLD"):
            rows.append({"bgc": ident, "check": "identity hold: region not bound to a BGC id"}); continue
        if edge_only and core.get("edge") not in ("True", "true"):
            rows.append({"bgc": ident, "contig_edge": core.get("edge"), "check": "interior region (--edge-only)"}); continue
        k = gdr.kcb_reference(zip_path, core, mibig_dir)
        if k:
            chosen[ident] = (k[0], names.get(k[0].stem) or k[1], "KnownClusterBlast rank 1")
        else:
            todo[ident] = [pid for pid, p in prots.items() if p["contig"] == core["contig"]
                           and p["start"] < core["end"] and p["end"] > core["start"]]
    if todo and (mibig_db or discovery_hits is not None):
        found = gdr.discover_references(todo, prots, mibig_db, mibig_dir, threads, sens, hits=discovery_hits)
        for ident, d in found.items():
            chosen[ident] = (d["reference"], names.get(d["reference"].stem, ""),
                             f"DIAMOND >= 35% identity: {d['proteins']} region proteins (bitscore {d['bitscore']})"
                             + (f"; runner-up {d['runner_up']}" if d["runner_up"] else "")
                             + ("; tied: ambiguous reference" if d["tied"] else ""))
    pdfs = []
    for core in regions:
        ident = core["identity"]
        if any(r["bgc"] == ident for r in rows):
            continue
        if ident not in chosen:
            rows.append({"bgc": ident, "contig_edge": core.get("edge"),
                         "check": "no reference: no KnownClusterBlast hit and no MIBiG cluster with >= 2 region "
                                  "proteins at >= 35% identity" if mibig_db else "no KnownClusterBlast hit; no --mibig-db"})
            continue
        ref, name, source = chosen[ident]
        folder = out / f"{ident.split(' / ')[3]}_vs_{Path(ref).stem}"
        rc = gdr.analyse_region(label, prots, regions, core, ref, name, source, folder, None, threads, sensitivity,
                                mibig_db, pfam, figure, write_proteins=False)
        splits = rc["split_genes"]
        rows.append({"bgc": ident, "contig_edge": core.get("edge"), "check": "run", "reference": Path(ref).stem,
                     "reference_name": name, "reference_source": source, "reference_genes": rc["reference_genes"],
                     "in_core": rc["present_in_core"], "found_clearly_elsewhere": rc["missing_found_clear"],
                     "partner_verdicts": "; ".join(f"{k} {v}" for k, v in sorted(rc["partner_checks"]["verdicts"].items())),
                     "clear_splits": sum(s["split_call"] == "CLEAR" for s in splits),
                     "split_genes": "; ".join(f"{s['name']} [{s['split_call']}]" for s in splits), "folder": folder.name})
        if (folder / "gap_rescue.pdf").exists():
            pdfs.append(folder / "gap_rescue.pdf")
        _LOG.info("[gap_rescue_all_regions] %s", gdr.summary_line(rc, folder))
    with open(out / "SUMMARY.tsv", "w", newline="") as fh:
        w = gdr.SafeWriter(fh, delimiter="\t")
        w.writerow(SUMMARY_COLS)
        for r in rows:
            w.writerow([r.get(c, "") for c in SUMMARY_COLS])
    try:
        import openpyxl
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "gap rescue"; ws.append(SUMMARY_COLS)
        for r in rows:
            ws.append([r.get(c, "") for c in SUMMARY_COLS])
        wb.save(out / "SUMMARY.xlsx")
    except ImportError:
        _LOG.info("[gap_rescue_all_regions] SUMMARY.xlsx not written: openpyxl is not installed (SUMMARY.tsv has the same rows)")
    if pdfs:
        try:
            from pypdf import PdfWriter
            wr = PdfWriter()
            for f in pdfs:
                wr.append(str(f))
            wr.write(str(out / f"{label}_all_locus_maps.pdf"))
        except ImportError:
            _LOG.info("[gap_rescue_all_regions] combined PDF not written: pypdf is not installed (each region folder has its own map)")
    run = sum(r["check"] == "run" for r in rows)
    (out / "run_receipt.json").write_text(json.dumps({
        "tool": "gap_rescue_all_regions", "label": label, "zip": Path(zip_path).name, "regions": len(rows), "run": run,
        "by_kcb": sum(1 for r in rows if r.get("reference_source") == "KnownClusterBlast rank 1"),
        "by_discovery": sum(1 for r in rows if str(r.get("reference_source", "")).startswith("DIAMOND")),
        "sensitivity": sensitivity, "mibig_db": str(mibig_db or ""), "pfam": str(pfam or "")}, indent=2) + "\n")
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--zip", required=True, type=Path)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--mibig-dir", type=Path, default=_os.environ.get("SAPOTE_MIBIG_GBK_DIR"), required=False)
    ap.add_argument("--mibig-db", type=Path, default=_os.environ.get("SAPOTE_MIBIG_DMND"))
    ap.add_argument("--mibig-names", type=Path, default=_os.environ.get("SAPOTE_MIBIG_NAMES"))
    ap.add_argument("--pfam", type=Path, default=_os.environ.get("SAPOTE_PFAM_HMM"))
    ap.add_argument("--edge-only", action="store_true", help="skip regions antiSMASH does not mark as on a contig edge")
    ap.add_argument("--sensitivity", default=gdr.SENSITIVITY_DEFAULT)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--no-figure", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not a.mibig_dir:
        raise SystemExit("--mibig-dir (or SAPOTE_MIBIG_GBK_DIR) is required: the folder of MIBiG <accession>.gbk files")
    gdr.assert_output_outside_bundle(a.out, __file__)
    rows = run_all(a.zip, a.label, a.out, a.mibig_dir, a.mibig_db, gdr.load_mibig_names(a.mibig_names), a.pfam,
                   a.edge_only, a.sensitivity, a.threads, not a.no_figure)
    _LOG.info("[gap_rescue_all_regions] %s: %d regions, %d run -> %s", a.label, len(rows),
              sum(r["check"] == "run" for r in rows), a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
