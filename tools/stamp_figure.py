#!/usr/bin/env python3
"""Stamp saved figures with the bundle renderer's name. Used by the R renderers after they save.

Usage: stamp_figure.py TOOL FILE [FILE ...]      (PNG, PDF or SVG)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.figure_stamp import stamp_file

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    for f in sys.argv[2:]:
        stamp_file(f, sys.argv[1])
