#!/usr/bin/env python3
"""Run Directed PKS Study Mode from a source CDS CSV and JSON spec."""

from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import dataclasses
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey.directed_studies.pks import load_study_spec, run_directed_pks_study

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", required=True)
    parser.add_argument("--study-spec", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--comparator-gene-table", default=None)
    args = parser.parse_args()
    spec = load_study_spec(Path(args.study_spec))
    if args.comparator_gene_table:
        # v9.7.151 (bunny-hop): was a hand-rolled type(spec)(...) reconstruction
        # naming all 5 fields explicitly — a future 6th field on
        # DirectedPKSStudySpec would silently drop on this override. frozen
        # dataclasses.replace() preserves every field automatically.
        spec = dataclasses.replace(spec, comparator_gene_table=args.comparator_gene_table)
    receipt = run_directed_pks_study(Path(args.source_csv), spec, Path(args.out))
    emit(receipt["status"])
    return 0 if receipt["status"] == "READY" else 2

if __name__ == "__main__":
    raise SystemExit(main())
