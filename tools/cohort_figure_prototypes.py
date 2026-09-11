#!/usr/bin/env python3
"""Standalone CLI for the extended cohort figure suite (see mamey/cohort_figures_extended.py).

Thin wrapper so the figures can be regenerated outside a cohort-figures run. Single source of
truth is the module; this just parses args and calls generate_extended().
Usage: python3 tools/cohort_figure_prototypes.py --packages-root <dir> [--strains ...] [--out ...]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.cohort_figures_extended import generate_extended


def main():
    ap = argparse.ArgumentParser(description="Regenerate the 11 extended cohort figures from packages.")
    ap.add_argument("--packages-root", required=True, help="dir containing <strain>/package/")
    ap.add_argument("--strains", default=None, help="comma-separated subset (default: auto-discover)")
    ap.add_argument("--out", default="./proto_figs")
    ap.add_argument("--census-csv", default=None)
    ap.add_argument("--locus-strain", default=None)
    ap.add_argument("--locus-bgc", default="BGC001")
    a = ap.parse_args()
    strains = [x.strip() for x in a.strains.split(",")] if a.strains else None
    r = generate_extended(a.packages_root, a.out, strains=strains, census_csv=a.census_csv,
                          locus_strain=a.locus_strain, locus_bgc=a.locus_bgc)
    emit(f"wrote {r['figures']} figures to {a.out}")
    for e in r.get("errors", []):
        emit("  WARN", e)


if __name__ == "__main__":
    main()
