#!/usr/bin/env python3
"""register_compute_output.py — the formal "register after running" step for heavy compute.

WHY THIS EXISTS (the Developer or User flag 2026-08-17, reported to auditors). A chat recommended re-running BiG-SCAPE
while 5.3 GB of finished results sat on disk, findable by `Tools/find_asset.py`. The download-blocking
hook did not catch it (a prose recommendation is not a tool call) and — the root cause — the finished
results were only registered in OFFICIAL_DATA/ASSET_REGISTRY.tsv MANUALLY, after the fact. So the next
new tree / BiG-SCAPE run / clinker set is unregistered until someone remembers, and the same miss recurs.

This makes registration a FORMAL, idempotent step the compute workflow ends with, instead of a memory
task. Run it as the last line of any heavy-compute recipe (BiG-SCAPE, GToTree/IQ-TREE, clinker, antiSMASH
intake) or call `register_result()` from a Sapote-Mamey subcommand that produces a durable result.

    tools/register_compute_output.py <result_path> \
        --id bigscape_gcf_results --type computed_result \
        --tokens "bigscape -|bigscape cluster|run_bigscape|clinker -" \
        --desc "COMPUTED RESULTS - DO NOT RE-RUN: cohort BiG-SCAPE GCF clustering ..."

Idempotent: if a row with the same id OR the same resolved path already exists, it is a NO-OP (exit 0,
prints the existing row). Never rewrites or duplicates. Registry path is bundle-portable via the same
env contract the engine uses (SAPOTE_WORKSPACE_ROOT -> SAPOTE_ROOT -> historical literal).

Claim ceiling: this registers the EXISTENCE and location of a computed artifact so it is not recomputed.
It makes no scientific claim about the result; downstream judgment is deferred as always.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import os
import subprocess
import sys
from pathlib import Path

REGISTRY_REL = "OFFICIAL_DATA/ASSET_REGISTRY.tsv"
COLS = ("asset_id", "type", "path", "size", "guard_tokens", "description")


def workspace_root() -> Path:
    """Portable root resolution. Delegates to mamey/workspace_root.py — the single
    sanctioned home of the historical default (the portability guard
    test_no_bare_workspace_path_in_code forbids the literal anywhere else, and it
    caught exactly this duplication at fold time). Env vars win; without env or the
    mamey package, fail VISIBLY with a setup instruction rather than assume a path."""
    for env in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT"):
        v = os.environ.get(env)
        if v:
            return Path(v)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from mamey.workspace_root import workspace_root as _wr
        return Path(_wr())
    except Exception:
        raise SystemExit(
            "register_compute_output: no workspace root configured. Set "
            "SAPOTE_WORKSPACE_ROOT (or SAPOTE_ROOT), or run from a bundle where "
            "the mamey package is importable.")


def _human_size(path: Path) -> str:
    if not path.exists():
        return "-"
    try:
        out = subprocess.run(["du", "-sh", str(path)], capture_output=True, text=True, timeout=120)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.split()[0]
    except Exception:
        # size is cosmetic registry metadata; on any du failure record "-" rather
        # than blocking registration (explicit fallthrough, not a silent pass —
        # this was the 151st silent_swallow, added by this tool's own author at
        # the .369 fold and caught by the .370 swallow triage).
        return "-"
    return "-"


def _load_rows(reg: Path) -> list[list[str]]:
    if not reg.exists():
        return []
    rows = []
    for line in reg.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(line.split("\t"))
    return rows


def register_result(result_path: str, asset_id: str, asset_type: str, tokens: str,
                    desc: str, root: Path | None = None) -> tuple[str, str]:
    """Idempotently append a registry row. Returns (status, message).

    status in {"registered", "exists_id", "exists_path"}. A no-op returns exists_* and changes nothing.
    """
    root = root or workspace_root()
    reg = root / REGISTRY_REL
    resolved = (root / result_path) if not os.path.isabs(result_path) else Path(result_path)
    # store the path relative to root when it lives under root (registry convention), else absolute
    try:
        stored_path = str(resolved.relative_to(root))
    except ValueError:
        stored_path = str(resolved)

    rows = _load_rows(reg)
    data = rows[1:] if rows and rows[0][:1] == [COLS[0]] else rows  # skip header if present
    for r in data:
        if r and r[0] == asset_id:
            return ("exists_id", f"asset_id '{asset_id}' already registered -> {r[2] if len(r) > 2 else '?'} (no-op)")
        if len(r) > 2 and r[2] == stored_path:
            return ("exists_path", f"path '{stored_path}' already registered as '{r[0]}' (no-op)")

    size = _human_size(resolved)
    desc = desc.replace("\t", " ").replace("\n", " ")
    tokens = tokens.replace("\t", " ").replace("\n", " ")
    row = "\t".join((asset_id, asset_type, stored_path, size, tokens, desc))
    with reg.open("a", encoding="utf-8") as fh:
        if rows and not reg.read_text(encoding="utf-8").endswith("\n"):
            fh.write("\n")
        fh.write(row + "\n")
    return ("registered", f"registered '{asset_id}' -> {stored_path} ({size})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Register a computed result so it is never recomputed.")
    ap.add_argument("result_path", help="path to the result dir/file (relative to workspace root or absolute)")
    ap.add_argument("--id", required=True, help="asset_id (unique key), e.g. bigscape_gcf_results")
    ap.add_argument("--type", default="computed_result", help="asset type (default: computed_result)")
    ap.add_argument("--tokens", required=True, help="pipe-separated guard tokens the recompute-gate matches on")
    ap.add_argument("--desc", required=True, help="one-line description; prefix 'COMPUTED RESULTS - DO NOT RE-RUN' for run outputs")
    ap.add_argument("--root", help="override workspace root (else SAPOTE_WORKSPACE_ROOT/SAPOTE_ROOT/default)")
    a = ap.parse_args(argv)
    status, msg = register_result(a.result_path, a.id, a.type, a.tokens, a.desc,
                                  root=Path(a.root) if a.root else None)
    emit(f"[register_compute_output] {status}: {msg}")
    return 0  # idempotent: a no-op is success, never an error


if __name__ == "__main__":
    sys.exit(main())
