#!/usr/bin/env python3
"""CLI front door for the tree-aligned heatmap panel (mamey.tree_heatmap_panel).

Renders a digest-bound quantitative heatmap whose row order is the bound tree's tip
order. Consumes sanity-gated trees only; never builds or re-orders one. See the module
docstring for the full contract and claim ceiling.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.tree_heatmap_panel import PanelHold, build_panel  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("config", help="panel config JSON (bound tree/crosswalk/matrix/sanity receipt)")
    args = parser.parse_args(argv)
    try:
        receipt = build_panel(args.config)
    except PanelHold as exc:
        sys.stderr.write(f"tree_heatmap_panel: REFUSED: {exc}\n")
        return 2
    sys.stdout.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
