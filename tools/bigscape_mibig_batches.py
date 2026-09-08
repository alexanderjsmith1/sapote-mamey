#!/usr/bin/env python3
"""bigscape_mibig_batches.py — split the MIBiG reference set into small, prokaryote-filtered
batches for INCREMENTAL loading into a BiG-SCAPE 2 run.

Why: `--mibig-version 4.0` loads all ~2,600 MIBiG BGCs in one scan. On a small machine
(1 core / ~4 GB) that single scan is the piece that fails — too much memory and wall-clock
at once. BiG-SCAPE caches each GBK's domain scan in the SQLite DB, so the reference set can
instead be loaded a few hundred at a time, each batch saving as it goes. This tool prepares
those batches.

Prokaryote-only by default: keeps only MIBiG entries whose domain_of_life is Bacteria, using
the bundle's own authoritative split `mamey/data/mibig/mibig_reference_index.bacterial.json`
(2,091 bacterial accessions in MIBiG 4.0). Fungal MIBiG entries are excluded by default. The
same machinery works for fungi with `--include-fungi` (adds mibig_reference_index.fungal.json)
— left off here because the AS-series cohort is bacterial; a mycologist could switch it on.

Usage:
  python bigscape_mibig_batches.py \
      --mibig-gbk-dir <extracted mibig_antismash_4.0_gbk_as8b1/> \
      --index-dir <bundle>/mamey/data/mibig \
      --out mibig_batches/ [--batch-size 300] [--include-fungi]

Then load each batch as a reference dir against your cohort DB (see the emitted RUN_ORDER.md):
  bigscape cluster -i <cohort_input>/ -o out/ --db-path cohort.db -p Pfam-A.hmm \
      -r mibig_batches/batch_01/ --gcf-cutoffs 0.3,0.5,0.7 --include-singletons
  # ...repeat -r batch_02, batch_03, ... reusing the same --db-path; each caches its scan.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, json, os, shutil, sys, math


def load_accessions(index_dir, include_fungi):
    keep = set()
    with open(os.path.join(index_dir, "mibig_reference_index.bacterial.json")) as fh:
        for e in json.load(fh).get("entries", []):
            keep.add(e["accession"])
    n_bact = len(keep)
    n_fung = 0
    if include_fungi:
        f = os.path.join(index_dir, "mibig_reference_index.fungal.json")
        if os.path.exists(f):
            with open(f) as fh:
                for e in json.load(fh).get("entries", []):
                    keep.add(e["accession"]); n_fung += 1
    return keep, n_bact, n_fung


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mibig-gbk-dir", required=True, help="dir of extracted MIBiG antiSMASH GBKs")
    ap.add_argument("--index-dir", required=True, help="<bundle>/mamey/data/mibig")
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-size", type=int, default=300)
    ap.add_argument("--include-fungi", action="store_true",
                    help="also include fungal MIBiG entries (default: prokaryote-only)")
    a = ap.parse_args()

    keep, n_bact, n_fung = load_accessions(a.index_dir, a.include_fungi)
    all_gbks = sorted(glob.glob(os.path.join(a.mibig_gbk_dir, "**", "*.gbk"), recursive=True))
    kept = [g for g in all_gbks if os.path.splitext(os.path.basename(g))[0] in keep]
    dropped = len(all_gbks) - len(kept)

    os.makedirs(a.out, exist_ok=True)
    nbatches = max(1, math.ceil(len(kept) / a.batch_size)) if kept else 0
    order = []
    for i in range(nbatches):
        bdir = os.path.join(a.out, f"batch_{i+1:02d}")
        os.makedirs(bdir, exist_ok=True)
        chunk = kept[i * a.batch_size:(i + 1) * a.batch_size]
        for g in chunk:
            shutil.copy(g, os.path.join(bdir, os.path.basename(g)))
        order.append((os.path.basename(bdir), len(chunk)))

    scope = "bacterial + fungal" if a.include_fungi else "bacterial (prokaryote-only)"
    with open(os.path.join(a.out, "RUN_ORDER.md"), "w") as fh:
        fh.write(f"# MIBiG reference batches ({scope})\n\n")
        fh.write(f"- MIBiG GBKs seen: {len(all_gbks)}\n- kept: {len(kept)} "
                 f"(bacterial {n_bact}" + (f" + fungal {n_fung}" if a.include_fungi else "") +
                 f")\n- excluded (out of scope, e.g. fungal): {dropped}\n"
                 f"- batches: {nbatches} (size {a.batch_size})\n\n")
        fh.write("Load each batch as a REFERENCE dir (`-r`) against the SAME --db-path, in order.\n"
                 "`--include-gbk '*'` is REQUIRED: MIBiG files are named `BGC0000001.gbk`, and\n"
                 "BiG-SCAPE's default `--include-gbk cluster,region` would otherwise skip every one\n"
                 "of them (they contain neither string). `-r` loads them as references, so the HTML\n"
                 "'Families with MIBiG Reference BGCs' stat and the known-vs-novel split populate.\n"
                 "Each batch caches its domain scan in the DB, so a failed batch is safe to re-run\n"
                 "and the next resumes from the saved DB. Copy the DB to durable storage between\n"
                 "batches.\n\n```\n")
        for name, n in order:
            fh.write(f"bigscape cluster -i <cohort_input>/ -o out_{name}/ --db-path cohort.db \\\n"
                     f"    -p Pfam-A.hmm -r mibig_batches/{name}/ --include-gbk '*' \\\n"
                     f"    --gcf-cutoffs 0.3,0.5,0.7 --include-singletons   # {n} refs\n")
        fh.write("```\n")
    emit(f"MIBiG seen {len(all_gbks)} | kept {len(kept)} ({scope}) | excluded {dropped} | "
          f"{nbatches} batches of {a.batch_size} -> {a.out}")
    return 0 if kept else 1


if __name__ == "__main__":
    sys.exit(main())
