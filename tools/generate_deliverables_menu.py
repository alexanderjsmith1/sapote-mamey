#!/usr/bin/env python3
"""Generate or verify the registry-backed Sapote-Mamey Diner Menu.

The default is fail-closed verification.  Use ``--apply`` during a governed
cut after editing ``mamey/data/deliverables_registry.json``.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mamey.deliverables_registry import (  # noqa: E402
    CANONICAL_MENU_PATH,
    LEGACY_MENU_PATH,
    load_registry,
    render_legacy_pointer,
    render_menu,
)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify generated files (default)")
    mode.add_argument("--apply", action="store_true", help="regenerate both menu files")
    args = parser.parse_args(argv)

    registry = load_registry()
    expected = {
        CANONICAL_MENU_PATH: render_menu(registry),
        LEGACY_MENU_PATH: render_legacy_pointer(),
    }
    if args.apply:
        for path, content in expected.items():
            _atomic_write(path, content)
            sys.stdout.write(str(f"WROTE {path.relative_to(ROOT)}") + "\n")
        return 0

    stale: list[str] = []
    for path, content in expected.items():
        observed = path.read_text(encoding="utf-8") if path.is_file() else None
        if observed != content:
            stale.append(str(path.relative_to(ROOT)))
    if stale:
        sys.stderr.write(str("STALE_GENERATED_DELIVERABLE_MENU " + ", ".join(stale)) + "\n")
        sys.stderr.write(str("Run: python tools/generate_deliverables_menu.py --apply") + "\n")
        return 1
    sys.stdout.write(str("DELIVERABLE_MENU_CURRENT") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

