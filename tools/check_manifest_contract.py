#!/usr/bin/env python3
"""Validate a Mamey package against schemas/manifest_contract.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey.manifest_schema import check_package_contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_dir")
    parser.add_argument("--schema", default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    result = check_package_contract(args.package_dir, args.schema)
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        produced_by = result.get("producer_workflow_version")
        provenance = f"; sealed by {produced_by}" if produced_by else ""
        print(f"MANIFEST_CONTRACT: {result['status']} "
              f"({result.get('checked_artifact_count', 0)} artifacts; "
              f"{result.get('error_count', len(result.get('errors', [])))} errors"
              f"{provenance})")
        for error in result.get("errors", []):
            print(f"  {error['code']}: {error['path']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
