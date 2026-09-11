#!/usr/bin/env python3
"""Fail closed when a patch packet contains workspace, cache, or evidence bloat."""

from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath


FORBIDDEN_PARTS = {
    "__pycache__",
    ".pytest_cache",
    "envs",
    "pkgs",
    "site-packages",
    "reassembly",
    "read_mapping",
}
BASELINE_MARKERS = {"SOURCE_CHECKSUMS_SHA256.txt", "TIER_MANIFEST.json"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}
BINARY_DIFF_RE = re.compile(r"^Binary files (.+?) and (.+?) differ$")


@dataclass(frozen=True)
class Finding:
    code: str
    relative_path: str
    apparent_bytes: int
    detail: str


def _normalise_patch_path(raw: str) -> str | None:
    token = raw.split("\t", 1)[0].strip()
    if token == "/dev/null":
        return None
    for prefix in ("a/", "b/", "base/", "patched/", "old/", "new/"):
        if token.startswith(prefix):
            return token[len(prefix) :]
    return token


def _patch_payload_findings(path: Path, relative_path: str) -> list[Finding]:
    """Inspect logical paths named by a diff, not only packet filesystem paths."""
    text = path.read_text(encoding="utf-8", errors="replace")
    logical_paths: set[str] = set()
    binary_markers: set[str] = set()
    for line in text.splitlines():
        if line.startswith(("--- ", "+++ ")):
            logical = _normalise_patch_path(line[4:])
            if logical:
                logical_paths.add(logical)
        match = BINARY_DIFF_RE.match(line)
        if match:
            target = _normalise_patch_path(match.group(2))
            if target:
                logical_paths.add(target)
                binary_markers.add(target)
    findings: list[Finding] = []
    for logical in sorted(logical_paths):
        pure = PurePosixPath(logical)
        if set(pure.parts) & FORBIDDEN_PARTS or pure.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(Finding(
                "FORBIDDEN_PATCH_PAYLOAD_PATH",
                relative_path,
                path.stat().st_size,
                f"diff names forbidden cache/environment payload: {logical}",
            ))
    for logical in sorted(binary_markers):
        findings.append(Finding(
            "UNAPPLICABLE_BINARY_DIFF_MARKER",
            relative_path,
            path.stat().st_size,
            f"plain diff records bytes as changed without carrying an applicable delta: {logical}",
        ))
    return findings


def inspect_packet(root: Path, max_total_bytes: int, max_file_bytes: int) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("packet must be an existing directory")
    findings: list[Finding] = []
    files = sorted(path for path in root.rglob("*") if path.is_file())
    apparent_total = 0
    allocated_total = 0
    for path in files:
        rel = path.relative_to(root)
        stat = path.stat()
        apparent_total += stat.st_size
        allocated_total += getattr(stat, "st_blocks", 0) * 512
        if set(rel.parts) & FORBIDDEN_PARTS:
            findings.append(Finding("FORBIDDEN_DIRECTORY_CLASS", rel.as_posix(), stat.st_size, "environment, cache, or scientific-run output"))
        if stat.st_size > max_file_bytes:
            findings.append(Finding("FILE_TOO_LARGE", rel.as_posix(), stat.st_size, f"limit={max_file_bytes}"))
        if path.suffix.lower() in {".patch", ".diff"}:
            findings.extend(_patch_payload_findings(path, rel.as_posix()))
    if apparent_total > max_total_bytes:
        findings.append(Finding("PACKET_TOO_LARGE", ".", apparent_total, f"limit={max_total_bytes}"))
    if not (root / "PATCH_CARD.md").is_file():
        findings.append(Finding("PATCH_CARD_MISSING", "PATCH_CARD.md", 0, "required owner-facing front door"))
    has_delta = any(path.suffix in {".patch", ".diff"} for path in files)
    has_candidate_files = any("candidate_files" in path.relative_to(root).parts for path in files)
    if not has_delta and not has_candidate_files:
        findings.append(Finding("IMPLEMENTATION_DELTA_MISSING", ".", 0, "requires unified diff or candidate_files tree"))
    marker_parents: dict[Path, set[str]] = {}
    for path in files:
        if path.name in BASELINE_MARKERS:
            marker_parents.setdefault(path.parent, set()).add(path.name)
    for parent, markers in marker_parents.items():
        if markers == BASELINE_MARKERS:
            findings.append(Finding("COPIED_RELEASE_BASELINE", parent.relative_to(root).as_posix(), 0, "release baseline belongs outside patch packet"))
    return {
        "schema_version": "1.0.0",
        "packet_name": root.name,
        "path_disclosure": "RELATIVE_ONLY",
        "file_count": len(files),
        "apparent_bytes": apparent_total,
        "allocated_bytes": allocated_total,
        "max_total_bytes": max_total_bytes,
        "max_file_bytes": max_file_bytes,
        "status": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": [asdict(item) for item in findings],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--max-total-mb", type=float, default=25.0)
    parser.add_argument("--max-file-mb", type=float, default=10.0)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = inspect_packet(args.packet, int(args.max_total_mb * 1024 * 1024), int(args.max_file_mb * 1024 * 1024))
    except ValueError as exc:
        parser.error(str(exc))
    if args.summary_only:
        codes = sorted({row["code"] for row in result["findings"]})
        text = f"{result['packet_name']}: {result['status']} apparent={result['apparent_bytes']} allocated={result['allocated_bytes']} findings={','.join(codes) or 'NONE'}\n"
    else:
        text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        emit(text, end="")
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
