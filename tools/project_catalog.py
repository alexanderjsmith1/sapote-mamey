#!/usr/bin/env python3
"""Operate the portable, hash-bound project catalog without the UI.

stdout is the deliverable (JSON, or a bare output path for export-private) via sys.stdout.write --
this tool prints nothing else. Errors propagate as an uncaught exception (project_catalog.py's own
typed ValueError/FileNotFoundError), matching the library's own fail-closed contract.

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
from mamey.project_catalog import ProjectCatalog, export_private_project_handoff, import_private_project_handoff


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    register = sub.add_parser("register", help="register one package by logical path and manifest hash")
    register.add_argument("--project-root", required=True)
    register.add_argument("--package", required=True)
    verify = sub.add_parser("verify", help="recheck every registered package locator and manifest hash")
    verify.add_argument("--project-root", required=True)
    export = sub.add_parser("export-private", help="write a private, non-redacted project handoff archive")
    export.add_argument("--project-root", required=True)
    export.add_argument("--out", required=True)
    imported = sub.add_parser("import-private", help="verify and import a private handoff into an empty root")
    imported.add_argument("--project-root", required=True)
    imported.add_argument("--input", required=True)
    args = parser.parse_args()
    if args.command == "register":
        payload = ProjectCatalog(args.project_root).register_package(args.package).as_dict()
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    elif args.command == "verify":
        payload = ProjectCatalog(args.project_root).verification_report()
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    elif args.command == "export-private":
        output = export_private_project_handoff(args.project_root, args.out)
        sys.stdout.write(str(output) + "\n")
    else:
        payload = import_private_project_handoff(args.input, args.project_root)
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
