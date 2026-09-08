#!/usr/bin/env python3
"""bgc_neighbor_layer.py — build a SEPARATE labeled tree layer for shared-BGC / BLASTp-neighbor
genomes, distinct from the taxonomy (16S-nearest-type) comparators.

Context: a genome tree for a query strain usually carries two very different kinds of extra tips:
  (a) TAXONOMY anchors — the 16S-nearest NAMED type strains (who the query IS), and
  (b) BGC NEIGHBORS — genomes that merely SHARE biosynthetic gene clusters / BLASTp hits with the
      query (who makes SIMILAR molecules). These are scientifically interesting but must NOT be read
      as taxonomic placement.
Mixing them silently mis-reads a shared-pathway neighbor as a phylogenetic relative. This tool emits a
per-tip layer annotation so the renderer can show BGC neighbors as their own labeled/colored layer.

Input: a NEIGHBORS_BY_STRAIN csv (cols: strain,genome_file,related_organism,accession,status).
Output: a tree-layer annotation TSV: tip_key, layer, source_strain, related_organism, accession, status
  layer = query | bgc_neighbor   (taxonomy-type tips are marked already_in_tree->bgc_neighbor unless
  a --type-list marks them as type_16S; see --types).

Read-only. Generic: no hardcoded project paths (uses $SAPOTE_ROOT / --csv / cwd).
Usage:
  python bgc_neighbor_layer.py --csv NEIGHBORS_BY_STRAIN.csv [--strain <STRAIN>] [--out layer.tsv]
        [--types type_names.txt]   # optional: organisms to tag as taxonomy type anchors
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, re, sys
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path

ROOT = Path(os.environ.get("SAPOTE_ROOT", os.getcwd()))


def tip_key(genome_file: str) -> str:
    """Derive a stable tip key from a genome filename (drop extension + common decorations)."""
    b = re.sub(r"\.(fna|fasta|fa|fas)$", "", os.path.basename(genome_file), flags=re.I)
    return b


def build_layer(rows, strain_filter=None, type_names=None):
    type_names = {t.strip().lower() for t in (type_names or []) if t.strip()}
    out = []
    for r in rows:
        strain = r.get("strain", "")
        if strain_filter and strain != strain_filter:
            continue
        org = (r.get("related_organism") or "").strip()
        gf = r.get("genome_file", "")
        status = (r.get("status") or "").strip()
        # the strain's own genome (query) vs neighbors
        if gf.startswith(strain) or org == strain or tip_key(gf) == strain:
            layer = "query"
        elif org.lower() in type_names:
            layer = "type_16S"
        else:
            layer = "bgc_neighbor"
        out.append(dict(tip_key=tip_key(gf), layer=layer, source_strain=strain,
                        related_organism=org, accession=(r.get("accession") or "").strip(),
                        status=status))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build a separate labeled BGC-neighbor tree layer.")
    ap.add_argument("--csv", required=True, help="NEIGHBORS_BY_STRAIN csv")
    ap.add_argument("--strain", default=None, help="restrict to one strain (default: all)")
    ap.add_argument("--types", default=None, help="optional file: organism names to tag as type_16S anchors")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    csv_path = Path(a.csv)
    if not csv_path.exists():
        sys.exit(f"csv not found: {csv_path}")
    rows = list(csv.DictReader(csv_path.open()))
    type_names = Path(a.types).read_text().splitlines() if a.types and Path(a.types).exists() else []
    layer = build_layer(rows, a.strain, type_names)

    # summary
    from collections import Counter
    by_layer = Counter(x["layer"] for x in layer)
    by_strain = Counter(x["source_strain"] for x in layer if x["layer"] == "bgc_neighbor")
    emit(f"tips: {len(layer)}  |  " + "  ".join(f"{k}={v}" for k, v in sorted(by_layer.items())))
    if not a.strain:
        emit("bgc_neighbor tips per strain:")
        for s, c in sorted(by_strain.items()):
            emit(f"   {s}: {c}")

    if a.out:
        with open(a.out, "w", newline="") as f:
            w = _SafeWriter(f, delimiter="\t")
            w.writerow(["tip_key", "layer", "source_strain", "related_organism", "accession", "status"])
            for x in layer:
                w.writerow([x["tip_key"], x["layer"], x["source_strain"], x["related_organism"],
                            x["accession"], x["status"]])
        emit(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
