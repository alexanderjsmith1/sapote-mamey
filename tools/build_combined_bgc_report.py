#!/usr/bin/env python3
"""Build one portable combined V7 + Mode B BGC dossier."""

from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import json
from pathlib import Path
import sys


# CUT-03 (v9.7.364). Implementation from the Codex/Rootstock patch bundle, adopted over the
# sealer's equivalent: same effect, but it uses pathlib, names the code tier, and is idempotent.
# Keep the source-tree front door runnable from any working directory. This is the same
# portability contract as mamey_run.py: the script's own code-tier parent, rather than the
# caller's cwd, owns the package import. Verified by Codex on a CLEAN .363 copy —
# baseline exit 1 `ModuleNotFoundError: No module named 'mamey'`, candidate exit 0.
_CODE_TIER = Path(__file__).resolve().parents[1]
if str(_CODE_TIER) not in sys.path:
    sys.path.insert(0, str(_CODE_TIER))

from mamey.combined_report_builder import build_from_path


def _roots(values: list[str]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--source-root requires ROOT_ID=/absolute/path")
        root_id, path = value.split("=", 1)
        if not root_id or root_id in out:
            raise ValueError(f"Missing or duplicate source-root ID: {root_id!r}")
        candidate = Path(path)
        if not candidate.is_absolute():
            raise ValueError("--source-root paths must be absolute")
        out[root_id] = candidate
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compose exact-current P357-015 evidence with preserved V7, Mode B, map, and structured overlays."
    )
    parser.add_argument("--job-spec", type=Path, required=True)
    parser.add_argument("--source-root", action="append", default=[], required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    args = parser.parse_args()
    result = build_from_path(args.job_spec, _roots(args.source_root), args.out_root)
    emit(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

