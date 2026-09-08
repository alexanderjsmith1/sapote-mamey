#!/usr/bin/env python3
"""CLI wrapper for mamey.cross_strain_figures.

Usage:
  python tools/build_cross_strain_figures.py \
    --rg-dir /path/to/rggmci_results \
    --ab-dir /path/to/quick_abaf_results \
    --out-dir /path/to/cross_strain_figures
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mamey.cross_strain_figures import THEME_CHOICES, build_cross_strain_figures


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Emit cross-strain RG-GMCI/AB-AF figures from result CSVs.")
    ap.add_argument("--rg-dir", required=True, help="Directory containing RG-GMCI priority/ranked/diff CSVs")
    ap.add_argument("--ab-dir", default=None, help="Optional directory containing quick AB/AF CSVs")
    ap.add_argument("--out-dir", required=True, help="Output figure directory")
    ap.add_argument("--top-n", type=int, default=30, help="Top-N bars for top-lead figures")
    ap.add_argument("--no-zip", action="store_true", help="Do not package the output directory as a ZIP")
    ap.add_argument("--theme", choices=THEME_CHOICES, default="evidence_dossier")
    args = ap.parse_args(argv)
    result = build_cross_strain_figures(args.rg_dir, args.out_dir, args.ab_dir, top_n=args.top_n, make_zip=not args.no_zip, theme=args.theme)
    emit(json.dumps(result, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
