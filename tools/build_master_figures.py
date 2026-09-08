#!/usr/bin/env python3
"""Build boss-ready master figure atlas from a Sapote–Mamey workbook."""
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

from mamey.master_figure_atlas import render_master_figure_atlas


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render boss-ready cross-strain figures from a Sapote–Mamey master workbook.")
    ap.add_argument("--workbook", required=True, help="Master workbook with Strain_Summary / Top_Antibacterial / Top_Antifungal sheets")
    ap.add_argument("--out-dir", required=True, help="Output figure directory")
    ap.add_argument("--no-zip", action="store_true", help="Do not write a ZIP package next to the output directory")
    args = ap.parse_args(argv)
    result = render_master_figure_atlas(args.workbook, args.out_dir, make_zip=not args.no_zip)
    emit(json.dumps(result, indent=2))
    return 0 if result.get("status") in {"PASS", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
