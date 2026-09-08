#!/usr/bin/env python3
"""Compile human figure decisions into a deterministic, non-rendering action plan.

The compiler consumes a Figure Factory ``FIGURE_MANIFEST.json`` and a small TSV
edited by the scientific owner.  It never interprets free text, edits source
data, selects a figure for publication, or renders a figure.  Missing decisions
remain explicit ``UNREVIEWED`` rows.
"""

from __future__ import annotations

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = "figure_owner_review_v1"
DECISION_HEADER = (
    "figure_set_id",
    "decision",
    "owner_comment",
    "requested_changes",
    "target_use",
)
ALLOWED_DECISIONS = frozenset({"KEEP", "REDESIGN", "DROP", "HOLD"})
FIGURE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
OUTPUT_NAMES = (
    "OWNER_REVIEW_PLAN.json",
    "OWNER_REVIEW_PLAN.tsv",
    "OWNER_REVIEW_SUMMARY.md",
)


class ReviewCompileError(ValueError):
    """Typed refusal raised before any final output directory is created."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_utf8(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise ReviewCompileError(f"{label}_UNREADABLE: {type(exc).__name__}") from exc


def _safe_locator(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewCompileError(f"MANIFEST_SCHEMA: {label} must be a non-empty string")
    text = value.strip().replace("\\", "/")
    locator = PurePosixPath(text)
    if locator.is_absolute() or ".." in locator.parts:
        raise ReviewCompileError(f"MANIFEST_LOCATOR_UNSAFE: {label}")
    return text


def load_manifest(path: Path) -> tuple[str, list[dict[str, str]]]:
    try:
        payload = json.loads(_read_utf8(path, "MANIFEST"))
    except json.JSONDecodeError as exc:
        raise ReviewCompileError(f"MANIFEST_JSON_INVALID: line {exc.lineno}") from exc
    figures = payload.get("figures") if isinstance(payload, dict) else None
    if not isinstance(figures, list) or not figures:
        raise ReviewCompileError("MANIFEST_SCHEMA: figures must be a non-empty list")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(figures, 1):
        if not isinstance(item, dict):
            raise ReviewCompileError(f"MANIFEST_SCHEMA: figures[{index}] must be an object")
        figure_id = item.get("figure_set_id")
        if not isinstance(figure_id, str) or not FIGURE_ID.fullmatch(figure_id):
            raise ReviewCompileError(f"MANIFEST_FIGURE_ID_INVALID: row {index}")
        if figure_id in seen:
            raise ReviewCompileError(f"MANIFEST_FIGURE_ID_DUPLICATE: {figure_id}")
        seen.add(figure_id)
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ReviewCompileError(f"MANIFEST_SCHEMA: title missing for {figure_id}")
        normalized.append(
            {
                "figure_set_id": figure_id,
                "title": title.strip(),
                "svg": _safe_locator(item.get("svg"), f"{figure_id}.svg"),
                "data_csv": _safe_locator(item.get("data_csv"), f"{figure_id}.data_csv"),
                "caption_methods": _safe_locator(
                    item.get("caption_methods"), f"{figure_id}.caption_methods"
                ),
            }
        )
    return str(payload.get("schema_version", "UNSPECIFIED")), normalized


def load_decisions(path: Path, known_ids: set[str]) -> dict[str, dict[str, str]]:
    text = _read_utf8(path, "DECISIONS")
    try:
        rows = list(csv.DictReader(text.splitlines(), delimiter="\t"))
    except csv.Error as exc:
        raise ReviewCompileError(f"DECISIONS_TSV_INVALID: {exc}") from exc
    reader = csv.DictReader(text.splitlines(), delimiter="\t")
    if tuple(reader.fieldnames or ()) != DECISION_HEADER:
        raise ReviewCompileError(
            "DECISIONS_HEADER_INVALID: expected " + "|".join(DECISION_HEADER)
        )
    decisions: dict[str, dict[str, str]] = {}
    for index, raw in enumerate(rows, 2):
        if None in raw:
            raise ReviewCompileError(f"DECISIONS_WIDTH_INVALID: row {index}")
        row = {key: (value or "").strip() for key, value in raw.items()}
        figure_id = row["figure_set_id"]
        if not figure_id:
            raise ReviewCompileError(f"DECISIONS_FIGURE_ID_MISSING: row {index}")
        if figure_id not in known_ids:
            raise ReviewCompileError(f"DECISIONS_FIGURE_ID_UNKNOWN: {figure_id}")
        if figure_id in decisions:
            raise ReviewCompileError(f"DECISIONS_FIGURE_ID_DUPLICATE: {figure_id}")
        decision = row["decision"].upper()
        if decision not in ALLOWED_DECISIONS:
            raise ReviewCompileError(f"DECISIONS_VALUE_INVALID: {figure_id}={decision or 'EMPTY'}")
        if decision in {"REDESIGN", "DROP", "HOLD"} and not row["owner_comment"]:
            raise ReviewCompileError(f"DECISIONS_COMMENT_REQUIRED: {figure_id}")
        if decision == "REDESIGN" and not row["requested_changes"]:
            raise ReviewCompileError(f"DECISIONS_CHANGES_REQUIRED: {figure_id}")
        row["decision"] = decision
        decisions[figure_id] = row
    return decisions


def compile_plan(manifest_path: Path, decisions_path: Path) -> dict[str, Any]:
    manifest_schema, figures = load_manifest(manifest_path)
    decisions = load_decisions(decisions_path, {row["figure_set_id"] for row in figures})
    rows: list[dict[str, str]] = []
    counts = {name: 0 for name in (*sorted(ALLOWED_DECISIONS), "UNREVIEWED")}
    for figure in figures:
        review = decisions.get(figure["figure_set_id"])
        if review is None:
            review = {
                "decision": "UNREVIEWED",
                "owner_comment": "",
                "requested_changes": "",
                "target_use": "",
            }
        counts[review["decision"]] += 1
        rows.append({**figure, **review})
    return {
        "schema_version": SCHEMA_VERSION,
        "source_manifest_schema": manifest_schema,
        "source_manifest_sha256": _sha256(manifest_path),
        "source_manifest_bytes": manifest_path.stat().st_size,
        "source_decisions_sha256": _sha256(decisions_path),
        "source_decisions_bytes": decisions_path.stat().st_size,
        "figure_count": len(rows),
        "counts": counts,
        "publication_selection_performed": False,
        "figures": rows,
    }


def _write_plan(stage: Path, plan: dict[str, Any]) -> None:
    (stage / OUTPUT_NAMES[0]).write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    columns = (
        "figure_set_id", "title", "decision", "owner_comment", "requested_changes",
        "target_use", "svg", "data_csv", "caption_methods",
    )
    with (stage / OUTPUT_NAMES[1]).open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: row[key] for key in columns} for row in plan["figures"])
    counts = plan["counts"]
    lines = [
        "# Figure owner-review summary",
        "",
        "This file records review decisions only. It does not select figures for publication or render outputs.",
        "",
        "## Counts",
        "",
    ]
    for decision in ("KEEP", "REDESIGN", "DROP", "HOLD", "UNREVIEWED"):
        lines.append(f"- {decision}: {counts[decision]}")
    lines.extend(["", "## Review plan", "", "| ID | Decision | Target | Owner comment | Requested changes |", "|---|---|---|---|---|"])
    for row in plan["figures"]:
        values = [
            row["figure_set_id"], row["decision"], row["target_use"],
            row["owner_comment"], row["requested_changes"],
        ]
        escaped = [value.replace("|", "\\|").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(escaped) + " |")
    (stage / OUTPUT_NAMES[2]).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_atomic(plan: dict[str, Any], output_dir: Path) -> None:
    if output_dir.exists() or output_dir.is_symlink():
        raise ReviewCompileError("OUTPUT_EXISTS: choose a new output directory")
    parent = output_dir.parent.resolve(strict=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.stage-", dir=parent))
    try:
        _write_plan(stage, plan)
        os.replace(stage, output_dir)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--decisions", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = compile_plan(args.manifest, args.decisions)
        write_atomic(plan, args.outdir)
    except (ReviewCompileError, OSError) as exc:
        print(f"OWNER_REVIEW_REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "PASS", "figures": plan["figure_count"], "counts": plan["counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
