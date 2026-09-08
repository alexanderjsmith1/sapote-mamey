#!/usr/bin/env python3
"""Build current-data tables and readiness receipts for owner-kept figures."""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mamey.interactive_figures.owner_kept_inputs import build_owner_kept_inputs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--widget-data", required=True)
    parser.add_argument("--source-bundle", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument(
        "--external-benchmark",
        action="append",
        default=[],
        help="exact source identifier typed EXTERNAL_BENCHMARK; repeat to select",
    )
    args = parser.parse_args(argv)
    try:
        result = build_owner_kept_inputs(
            args.widget_data,
            args.source_bundle,
            args.outdir,
            external_benchmark_ids=args.external_benchmark,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"OUTPUT_REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

