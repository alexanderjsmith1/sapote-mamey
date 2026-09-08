#!/usr/bin/env python3
"""Fail-closed preflight for the governed documents add-on wheelhouse.

The audit never contacts an index and never installs a package.  It asks the
selected interpreter's pip resolver whether each direct documents requirement
has a compatible binary wheel in one local wheelhouse.  Optional import checks
are intended for a second pass after an operator performs the offline install.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable


# The bundle root is the parent of this tools/ directory; the governed documents
# profile ships at a fixed location under it. Anchoring the default here keeps the
# preflight runnable from any working directory instead of resolving against cwd.
BUNDLE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE = BUNDLE_ROOT / "sapote_addons" / "profiles" / "documents.txt"


IMPORT_NAMES = {
    "python-docx": "docx",
    "lxml": "lxml",
    "pyyaml": "yaml",
    "reportlab": "reportlab",
    "pypdf": "pypdf",
    "pillow": "PIL",
}


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def requirement_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9_.-]*)", requirement)
    if not match:
        raise ValueError(f"REQUIREMENT_NAME_UNREADABLE:{requirement}")
    return canonical_name(match.group(1))


def interpreter_path(value: str) -> Path:
    """Return an absolute interpreter path without resolving venv symlinks."""
    return Path(os.path.abspath(os.path.expanduser(value)))


def read_profile(path: Path) -> list[str]:
    requirements: list[str] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith(("-", ".")):
            raise ValueError(f"PROFILE_DIRECT_REQUIREMENT_ONLY:{path}:{line_number}:{line}")
        requirement_name(line)
        requirements.append(line)
    if not requirements:
        raise ValueError(f"PROFILE_EMPTY:{path}")
    return requirements


def _tail(text: str, lines: int = 8) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def audit_requirements(
    *,
    python: Path,
    wheelhouse: Path,
    requirements: list[str],
    check_imports: bool = False,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    if not python.is_file():
        raise ValueError(f"PYTHON_NOT_FOUND:{python}")
    if not wheelhouse.is_dir():
        raise ValueError(f"WHEELHOUSE_NOT_FOUND:{wheelhouse}")

    environment = dict(os.environ)
    environment.update({
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_CACHE_DIR": "1",
        "PIP_PROGRESS_BAR": "off",
    })
    rows: list[dict[str, Any]] = []
    for requirement in requirements:
        name = requirement_name(requirement)
        command = [
            str(python), "-m", "pip", "install", "--dry-run", "--no-index",
            "--only-binary=:all:", "--disable-pip-version-check",
            "--find-links", str(wheelhouse), requirement,
        ]
        resolved = runner(command, capture_output=True, text=True, env=environment)
        combined = (resolved.stdout or "") + (resolved.stderr or "")
        row: dict[str, Any] = {
            "distribution": name,
            "requirement": requirement,
            "resolution": "PASS" if resolved.returncode == 0 else "FAIL",
            "resolver_returncode": resolved.returncode,
            "resolver_tail": _tail(combined),
        }
        if check_imports:
            import_name = IMPORT_NAMES.get(name)
            if import_name is None:
                row["import"] = "NOT_MAPPED"
            else:
                imported = runner(
                    [str(python), "-c", f"import {import_name}"],
                    capture_output=True,
                    text=True,
                    env=environment,
                )
                row["import"] = "PASS" if imported.returncode == 0 else "FAIL"
                row["import_returncode"] = imported.returncode
                row["import_tail"] = _tail((imported.stdout or "") + (imported.stderr or ""))
        rows.append(row)

    failed_resolution = [row["distribution"] for row in rows if row["resolution"] != "PASS"]
    failed_import = [row["distribution"] for row in rows if row.get("import") == "FAIL"]
    return {
        "schema_version": "sapote-documents-wheelhouse-audit-1.0",
        "status": "PASS" if not failed_resolution and not failed_import else "FAIL",
        "network_policy": "NO_INDEX_LOCAL_BINARY_WHEELS_ONLY",
        "python": str(python),
        "wheelhouse": str(wheelhouse),
        "requirements": rows,
        "failed_resolution": failed_resolution,
        "failed_import": failed_import,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit the offline documents wheelhouse without installing or contacting an index")
    parser.add_argument("--wheelhouse", required=True, help="One platform-matched wheel directory")
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE),
                        help="Direct requirements profile (default: bundled documents profile)")
    parser.add_argument("--python", default=sys.executable, help="Target interpreter (default: current Python)")
    parser.add_argument("--check-imports", action="store_true", help="Also verify imports in the target interpreter")
    parser.add_argument("--output", default=None, help="Optional JSON receipt path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_requirements(
            python=interpreter_path(args.python),
            wheelhouse=Path(args.wheelhouse).resolve(),
            requirements=read_profile(Path(args.profile).resolve()),
            check_imports=args.check_imports,
        )
    except Exception as exc:
        report = {
            "schema_version": "sapote-documents-wheelhouse-audit-1.0",
            "status": "FAIL",
            "error": str(exc),
        }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
