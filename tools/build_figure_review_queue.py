#!/usr/bin/env python3
"""Build a portable, paginated owner-review queue from a Figure Factory manifest."""

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

from mamey.figure_review_queue import FigureReviewQueueError, build_review_queue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--figure-root", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--page-size", type=int, default=25)
    args = parser.parse_args(argv)
    try:
        receipt = build_review_queue(
            args.manifest,
            args.figure_root,
            args.outdir,
            decisions=args.decisions,
            page_size=args.page_size,
        )
    except FigureReviewQueueError as exc:
        emit(json.dumps({"status": "REFUSED", "code": exc.code}), file=sys.stderr)
        return 2
    emit(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

