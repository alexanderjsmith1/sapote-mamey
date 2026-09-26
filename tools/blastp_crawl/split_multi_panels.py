#!/usr/bin/env python3
"""Split 10-protein ClusteredNR panels into the single-protein layout the runner expects.

Two incompatible staging formats shipped under one name, `_QUERIES_GAP_<AS-S>_K`:

  SINGLE  <S>/<S>_gapK_p0361/<S>__gapK__ctg34_62.faa     1 record, gene-named
  MULTI   <S>/_gap/<S>_gapK_p010.faa                     10 records, panel-numbered

Only SINGLE is the fast path: every gap lane that finished in the 2026-09 crawl was SINGLE.
This converts MULTI lanes to SINGLE in place.

The originals are MOVED to `Blastp RESULTS/_SUPERSEDED_MULTI_PANELS/<strain>/`, outside the
queries tree, so `all_query_files()` cannot pick up both copies and submit each protein twice.
They are moved, not deleted — the split is reversible by moving them back.

Dry-run by default. Pass --execute to write. Set SAPOTE_WORKSPACE_ROOT to the folder holding
`Blastp RESULTS/`; the tool refuses to write inside the code bundle.
"""
import argparse, os, shutil, sys
from pathlib import Path

try:
    from mamey.path_safety import assert_output_outside_bundle
except ImportError:  # bare script: the bundle root is two levels above this file
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from mamey.path_safety import assert_output_outside_bundle

BR = Path(os.environ.get("SAPOTE_WORKSPACE_ROOT", ".")) / "Blastp RESULTS"
ATTIC = BR / "_SUPERSEDED_MULTI_PANELS"


def records(faa: Path):
    name, buf = None, []
    for line in faa.open():
        if line.startswith(">"):
            if name:
                yield name, buf
            name, buf = line[1:].strip().split()[0], []
        elif line.strip():
            buf.append(line.strip())
    if name:
        yield name, buf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    if a.execute:
        assert_output_outside_bundle(BR, __file__, kind="BLASTp query tree")

    lanes = files_in = prots = 0
    for qdir in sorted(BR.glob("_QUERIES_GAP_*_K")):
        gap = next((d for d in qdir.glob("*/_gap") if d.is_dir()), None)
        if gap is None:
            continue                       # already SINGLE
        strain = gap.parent.name
        srcs = sorted(gap.rglob("*.faa"))
        if not srcs:
            continue
        # confirm it really is multi-record before touching anything
        if sum(1 for l in srcs[0].open() if l.startswith(">")) <= 1:
            continue

        # A lane may be DOUBLE-STAGED: the same gene present both as its own single-protein
        # panel and inside a _gap batch (four lanes as of 2026-09-23, overlap ~total).
        # Emit only genes not already staged singly, or the split would manufacture the
        # duplicate submissions that double-staging had so far only threatened.
        have = set()
        for f in gap.parent.rglob("*.faa"):
            if "/_gap/" not in str(f):
                have |= {l[1:].strip().split()[0] for l in f.open() if l.startswith(">")}
        n = dup = 0
        for src in srcs:
            for gene, seq in records(src):
                if gene in have:
                    dup += 1
                    continue
                n += 1
                if a.execute:
                    pdir = gap.parent / f"{strain}_gapK_p{n:04d}"
                    pdir.mkdir(parents=True, exist_ok=True)
                    out = pdir / f"{strain}__gapK__{gene}.faa"
                    out.write_text(f">{gene}\n" + "\n".join(seq) + "\n")
        if a.execute:
            dest = ATTIC / strain
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(gap), str(dest))
        lanes += 1
        files_in += len(srcs)
        prots += n
        print(f"{strain:8} {len(srcs):4} panels -> {n:5} new single-protein files"
              + (f"   ({dup} already staged singly, skipped)" if dup else ""))

    print(f"\n{'WROTE' if a.execute else 'DRY RUN'}: {lanes} lanes, "
          f"{files_in} multi-panels -> {prots} single-protein panels")
    if a.execute:
        print(f"originals moved to {ATTIC} (move back to reverse)")
    else:
        print("re-run with --execute to apply")


if __name__ == "__main__":
    sys.exit(main())
