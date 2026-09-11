#!/usr/bin/env python3
"""Validate and bind a portable multi-strain project configuration to its project_registry.py
registry (mamey/portfolio_config.py).

stdout is the deliverable (the binding, as JSON) via sys.stdout.write. A typed refusal
(mamey.portfolio_config.PortfolioConfigError) propagates as an uncaught exception, matching the
library's own fail-closed contract.

Tools/bin/python3, PYTHONDONTWRITEBYTECODE=1 house convention.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# mamey_run.py is the documented entry point and forces the local package onto sys.path itself;
# this tool may also be invoked directly (e.g. as a subprocess in tests), so mirror that bootstrap
# rather than rely on an editable install being current -- same pattern as tools/chitin_reference_eval.py.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from mamey.portfolio_config import load_portfolio_binding, write_portfolio_binding


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--config", required=True, help="existing project-root-relative portfolio configuration")
    parser.add_argument("--write-binding", action="store_true", help="write additive lab_quest_outputs/portfolio_binding.json")
    args = parser.parse_args()
    binding = load_portfolio_binding(args.project_root, args.config)
    result = binding.as_dict()
    if args.write_binding:
        result["binding_path"] = str(write_portfolio_binding(args.project_root, binding))
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
