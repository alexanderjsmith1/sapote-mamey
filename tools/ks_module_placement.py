#!/usr/bin/env python3
"""ks_module_placement.py — place one isolate's KS domains on a reference cluster's module order.

Reader-side and NON-SCORING. Two steps around a KS tree you build yourself (see docs/PKS_KS_TREE_OPTIONS.md):

  inputs  write one FASTA with the isolate's KS domains and every KS of one or more reference cluster GenBank
          files (MIBiG), numbered by position along each record, plus the alignment and tree commands to run.
  place   read the IQ-TREE treefile and call, per isolate KS: PLACED_ON_REFERENCE_MODULE (module number),
          MODULE_FAMILY, AMBIGUOUS_MODULES or UNPLACED (mamey.ks_phylogeny.place_on_reference_modules).

Why: pieces of a giant modular PKS broken over many contigs all hit the same references almost equally, so
shared-reference homology (RG-GMCI) cannot tell one pathway in many pieces from a web of similar clusters. KS
phylogeny against the reference's own module KS can. Placement reads machinery, not product; module order is not
contig order; nothing is joined.

CLI:
  python tools/ks_module_placement.py inputs --gbk-dir <single-isolate region GBKs> --reference BGC0002357.gbk \
         [--reference ...] --out <dir> [--threads 4]
  python tools/ks_module_placement.py place --tree <dir>/ks_tree.treefile --out <dir>/placement.tsv [--min-ufboot 80]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import json
import sys
from pathlib import Path

try:
    from mamey import ks_phylogeny as kp
    from mamey.path_safety import assert_output_outside_bundle
except ImportError:  # bare-script run: bundle root is one level up
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from mamey import ks_phylogeny as kp
    from mamey.path_safety import assert_output_outside_bundle


def _say(*lines: str) -> None:
    emit(*lines, sep="\n")


def cmd_inputs(a) -> int:
    query = kp.extract_module_core_domains(a.gbk_dir, classes=("PKS_KS",))
    fasta = kp.domain_fastas(query).get("PKS_KS", "")
    refs = [t for g in a.reference for t in kp.reference_module_ks(g)]
    if not fasta or not refs:
        _say(f"[ks_module_placement] refused: {'no isolate KS' if not fasta else 'no reference KS'}")
        return 2
    out = assert_output_outside_bundle(Path(a.out), __file__)
    out.mkdir(parents=True, exist_ok=True)
    faa = out / "ks_with_references.faa"
    faa.write_text(fasta + "".join(f">{t['tip']}\n{t['translation']}\n" for t in refs), encoding="utf-8")
    aln, pre = out / "ks_with_references.aln.faa", out / "ks_tree"
    commands = [
        f"muscle -align {faa} -output {aln} -threads {a.threads}",
        f"iqtree3 -s {aln} -m MFP -mset LG,WAG,JTT -B 1000 -alrt 1000 -seed 12345 -T {a.threads} -pre {pre}",
        f"python tools/ks_module_placement.py place --tree {pre}.treefile --out {out / 'placement.tsv'}",
    ]
    (out / "COMMANDS.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")
    n_query = fasta.count(">")
    _say(f"[ks_module_placement] {query['strain']}: {n_query} KS + {len(refs)} reference KS -> {faa}",
         "Build the tree with:", *commands[:2])
    return 0


def cmd_place(a) -> int:
    assert_output_outside_bundle(Path(a.out), __file__)
    rows = kp.place_on_reference_modules(Path(a.tree).read_text(encoding="utf-8"), min_ufboot=a.min_ufboot)
    receipt = kp.write_placement(rows, a.out)
    _say(f"[ks_module_placement] {json.dumps(receipt['counts'], sort_keys=True)} -> {a.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Place an isolate's KS domains on a reference cluster's module order.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("inputs", help="write the KS FASTA with reference module KS and the tree commands")
    i.add_argument("--gbk-dir", required=True, help="one isolate's antiSMASH region GBKs (<STRAIN>_NODE_x_regionNNN.gbk)")
    i.add_argument("--reference", action="append", required=True, help="reference cluster GenBank file (repeatable)")
    i.add_argument("--out", required=True)
    i.add_argument("--threads", type=int, default=4)
    p = sub.add_parser("place", help="read an IQ-TREE treefile and write the placement table")
    p.add_argument("--tree", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--min-ufboot", type=float, default=80.0)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    return cmd_inputs(a) if a.cmd == "inputs" else cmd_place(a)


if __name__ == "__main__":
    sys.exit(main())
