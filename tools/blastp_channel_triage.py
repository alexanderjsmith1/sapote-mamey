#!/usr/bin/env python3
"""Command-line front door for the fail-closed BLASTp channel triage sidecar."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mamey.blastp_channel_triage import ContractError, run_triage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare rank-1 nr and clustered_nr rows under explicit identity and provenance contracts. "
            "Never selects a cross-channel winner or changes the input package."
        )
    )
    parser.add_argument("--hits", required=True, help="CSV or TSV of per-channel hit rows")
    parser.add_argument("--identity-map", required=True, help="TSV/CSV with strain, full_node, region, bgc_alias")
    parser.add_argument(
        "--provenance",
        required=True,
        help="TSV/CSV receipt with channel, source SHA-256, portable locator, bytes, and explicit label",
    )
    parser.add_argument("--out", required=True, help="new output directory; existing outputs are never overwritten")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_triage(args.hits, args.identity_map, args.provenance, args.out)
    except (ContractError, OSError, ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
