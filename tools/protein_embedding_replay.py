#!/usr/bin/env python3
"""Replay saved TriMap or t-SNE coordinates from a hash-bound manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools._embedding_replay import ReplayRefusal, prepare_replay, run_replay


def main(argv=None) -> int:
    """Validate without plotting, or render into a new output directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    from mamey.logging_setup import get_logger
    logger = get_logger("embedding_replay")
    try:
        if args.validate_only:
            plan = prepare_replay(args.manifest)
            logger.info("Validated saved-coordinate inputs: %s", json.dumps(plan["counts"], sort_keys=True))
        else:
            if args.out is None:
                raise ReplayRefusal("--out is required unless --validate-only is selected")
            receipt = run_replay(args.manifest, args.out)
            logger.info("Saved-coordinate replay: %s", json.dumps(receipt["counts"], sort_keys=True))
        return 0
    except (ReplayRefusal, OSError, ValueError, TypeError, KeyError) as error:
        logger.error("Replay refused: %s", error)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
