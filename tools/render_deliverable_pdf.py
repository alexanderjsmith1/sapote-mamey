#!/usr/bin/env python3
"""Compatibility CLI for the package-scoped ``mamey.markdown_pdf`` renderer.

Rebuilds the rich guide aesthetic: an indigo cover band, colored section headers with a left
accent bar, tinted callout boxes for blockquotes, styled tables with an indigo header row, and
grey monospace boxes for fenced code. Palette: indigo #2d398b, teal #00585c, periwinkle/teal tints.

Usage: python3 render_deliverable_pdf.py INPUT.md OUTPUT.pdf ["Cover Title"] ["Cover subtitle"]
Markdown supported: # title, ## / ### / #### headers, paragraphs, - bullets, 1. numbered lists,
| tables |, > callouts, ``` fenced code ```, --- rules, **bold** / *italic* / `code` inline.

The implementation lives in ``mamey/markdown_pdf.py`` so package consumers such
as Mode B export do not depend on a sibling ``tools/`` source-tree path.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey.markdown_pdf import *  # noqa: F401,F403 - compatibility re-export for existing in-process callers


if __name__ == "__main__":
    raise SystemExit(main())
