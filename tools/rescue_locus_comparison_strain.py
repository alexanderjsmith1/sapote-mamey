#!/usr/bin/env python3
"""Render a locus comparison for every gap-rescue folder of one strain (the genome read once).
Usage: python tools/rescue_locus_comparison_strain.py --zip Z --label AS-n --rescue-root DIR --mibig-dir D
         [--gene-labels T.tsv] --out OUTDIR
Writes OUTDIR/<BGC>/ (input.json, VIEW.txt, render/) and OUTDIR/LOCUS_MAPS.tsv (BGC, reference, view or why not)."""
import argparse, csv, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gap_directed_rescue as gdr  # noqa: E402
import rescue_locus_comparison as rlc  # noqa: E402
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ModuleNotFoundError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from _console import emit  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    for a in ("--zip", "--label", "--rescue-root", "--mibig-dir", "--out"):
        ap.add_argument(a, required=True)
    ap.add_argument("--gene-labels")
    ap.add_argument("--mibig-names")
    a = ap.parse_args()
    genome = gdr.load_genome(Path(a.zip), a.label)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in sorted(p for p in Path(a.rescue_root).iterdir() if p.is_dir() and "_vs_" in p.name and (p / "gap_rescue.tsv").exists()):
        bgc = f.name.split("_vs_")[0]
        if (out / bgc / "render" / "comparison.png").exists():
            rows.append((bgc, f.name, "already drawn")); continue
        try:
            spec = rlc.manifest(a.zip, a.label, f, a.mibig_dir, a.gene_labels, genome=genome, mibig_names=a.mibig_names)
            view = rlc.render_with_fallback(spec, out / bgc) if spec else "no reference gene in the region core"
        except Exception as e:  # one region's failure is recorded, not fatal
            view = f"FAILED: {str(e)[:160]}"
        rows.append((bgc, f.name, view or "refused: labels overlap at every view"))
        emit(bgc, view, flush=True)
    with open(out / "LOCUS_MAPS.tsv", "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["bgc", "rescue_folder", "view"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
