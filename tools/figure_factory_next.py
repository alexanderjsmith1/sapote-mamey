#!/usr/bin/env python3
"""Render receipt-bound aggregate evidence figures from an external data root."""

from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mamey.figure_factory_next import build as build_aggregate
from mamey.phylogeny_figure_factory import (
    CONCORDANCE_KIND,
    EVIDENCE_WIDGET_KIND,
    TRACK_KIND,
    PhylogenyFigureHold,
    build as build_phylogeny,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    try:
        receipt = build_phylogeny(args.config) if config.get("figure_kind") in {TRACK_KIND, CONCORDANCE_KIND, EVIDENCE_WIDGET_KIND} else build_aggregate(args.config)
    except PhylogenyFigureHold as exc:
        sys.stderr.write("figure_factory_next: REFUSED " + str(exc) + "\n")
        return 2
    emit(json.dumps({"status": receipt["status"], "outputs": receipt["outputs"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
