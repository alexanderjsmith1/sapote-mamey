#!/usr/bin/env python3
"""Run EFLS Rewire from a Pre-Sapote Lite gene evidence table."""

from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey.efls import write_efls_outputs

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gene-evidence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    outputs = write_efls_outputs(Path(args.gene_evidence), Path(args.out))
    emit(outputs["receipt"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
