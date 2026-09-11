#!/usr/bin/env python3
"""build_master_figure_atlas.py — DEPRECATED alias, retired v9.7.213-audit.

This was a byte-for-byte duplicate CLI shim: both this file and build_master_figures.py
called mamey.master_figure_atlas.render_master_figure_atlas with the same two required
args, and this one was never load-bearing — mamey/master_figure_atlas.py's own help text
(lines 397, 867) and docs/batches/batch12_figure_system_one_pager.md /
batch14_structural_factual_report.md all name build_master_figures.py as the tool to run.
This file had zero CHANGELOG entry recording its creation.

Kept as a redirect (not deleted) in case something outside this tree still calls it by
name; it now errors instead of silently duplicating logic that can drift out of sync.
Consolidates: build_master_figure_atlas.py -> build_master_figures.py
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys

def main(argv=None) -> int:
    emit(
        "build_master_figure_atlas.py is retired (duplicate of build_master_figures.py, "
        "found in the v9.7.213 tools/ duplication audit). Use:\n"
        "  python tools/build_master_figures.py --workbook <MASTER.xlsx> --out-dir <FIGURE_DIR>",
        file=sys.stderr,
    )
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
