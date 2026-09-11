#!/usr/bin/env python3
"""Render the static three-channel evidence matrix from generic JSON or TSV."""
from __future__ import annotations

import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mamey.interactive_figures.three_channel_evidence_matrix import main


if __name__ == "__main__":
    raise SystemExit(main())
