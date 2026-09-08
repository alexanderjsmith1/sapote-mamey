#!/usr/bin/env python3
"""CLI wrapper for the portable Sapote-Mamey figure-theme gallery prototype."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mamey.interactive_figures.theme_gallery import main


if __name__ == "__main__":
    raise SystemExit(main())
