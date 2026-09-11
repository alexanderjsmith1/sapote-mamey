#!/usr/bin/env python3
"""Verify a structured full-suite receipt before a release cut reuses external validation.

This is an integrity and provenance gate, not an authentication system. It accepts only the
configured full-suite profile and binds it to the exact source tree, receipt, log, collected
node IDs, and per-node outcomes. Free-text pytest summaries are never sufficient authority.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
import sys


SCHEMA = "sapote-mamey.external-pytest-validation.v1"
PROFILE = "configured-full-suite"
COMMAND_TAIL = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "--run-slow", "--run-network"]
OUTCOMES = ("passed", "skipped", "xfailed", "xpassed", "failed", "errors")
_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
_SKIP_NAMES = {".DS_Store"}
_SKIP_SUFFIXES = {".pyc", ".pyo"}
_SUMMARY_RE = re.compile(r"\bin\s+\d+(?:\.\d+)?s\b")


class ReceiptRefused(ValueError):
    """Typed fail-closed receipt refusal."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_tree_sha256(root: Path) -> str:
    """Content/mode/path digest for the exact source tree, excluding only transient caches."""
    root = root.resolve()
    if not root.is_dir():
        raise ReceiptRefused(f"source root is not a directory: {root}")
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root)
        if any(part in _SKIP_DIRS or part.endswith(".egg-info") for part in rel.parts):
            continue
        if path.name in _SKIP_NAMES or path.suffix in _SKIP_SUFFIXES:
            continue
        if path.is_symlink():
            raise ReceiptRefused(f"source tree contains a symlink: {rel.as_posix()}")
        if not path.is_file():
            continue
        file_hash = sha256_file(path)
        mode = stat.S_IMODE(path.stat().st_mode)
        record = f"{rel.as_posix()}\0{mode:o}\0{path.stat().st_size}\0{file_hash}\n"
        digest.update(record.encode("utf-8"))
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReceiptRefused(message)


def _utc(value: object, field: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), f"{field} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ReceiptRefused(f"{field} is not a valid ISO-8601 UTC timestamp") from exc
    return parsed


def _resolve_artifact(receipt: Path, root: Path, block: object, label: str) -> Path:
    _require(isinstance(block, dict), f"artifacts.{label} must be an object")
    locator = block.get("path")
    expected = block.get("sha256")
    _require(isinstance(locator, str) and locator, f"artifacts.{label}.path is required")
    _require(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected) is not None,
             f"artifacts.{label}.sha256 must be lowercase SHA-256")
    path = Path(locator)
    if not path.is_absolute():
        path = receipt.parent / path
    path = path.resolve()
    _require(path.is_file(), f"artifacts.{label} is not a file: {path}")
    _require(root != path and root not in path.parents,
             f"artifacts.{label} must be outside the source tree to avoid a circular tree hash")
    observed = sha256_file(path)
    _require(observed == expected, f"artifacts.{label} SHA-256 mismatch")
    return path


def _read_identity(path: Path, declared_count: object) -> list[str]:
    nodeids = [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines()]
    _require(bool(nodeids), "test identity artifact is empty")
    _require(all(nodeids), "test identity artifact contains a blank node ID")
    _require(len(nodeids) == len(set(nodeids)), "test identity artifact contains duplicate node IDs")
    _require(isinstance(declared_count, int) and declared_count == len(nodeids),
             "test identity count does not match the identity artifact")
    return nodeids


def _read_outcomes(path: Path) -> tuple[dict[str, str], dict[str, int]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        _require(reader.fieldnames == ["nodeid", "outcome"],
                 "test result artifact header must be exactly: nodeid<TAB>outcome")
        rows = list(reader)
    _require(bool(rows), "test result artifact is empty")
    result: dict[str, str] = {}
    counts = {name: 0 for name in OUTCOMES}
    for row in rows:
        nodeid, outcome = row["nodeid"], row["outcome"]
        _require(bool(nodeid), "test result artifact contains a blank node ID")
        _require(nodeid not in result, f"duplicate result node ID: {nodeid}")
        _require(outcome in counts, f"unsupported test outcome {outcome!r} for {nodeid}")
        result[nodeid] = outcome
        counts[outcome] += 1
    return result, counts


def _log_counts(path: Path) -> dict[str, int]:
    summary = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if _SUMMARY_RE.search(line) and re.search(r"\b\d+\s+passed\b", line):
            summary = line
    _require(summary is not None, "pytest log has no final pytest summary line")
    counts = {}
    for name in OUTCOMES:
        pattern = r"\b(\d+)\s+" + ("error(?:s)?" if name == "errors" else re.escape(name)) + r"\b"
        match = re.search(pattern, summary)
        counts[name] = int(match.group(1)) if match else 0
    return counts


def verify_receipt(
    receipt_path: Path,
    root: Path,
    expected_receipt_sha256: str,
    *,
    now: datetime | None = None,
    max_age: timedelta = timedelta(hours=24),
) -> Path:
    receipt_path = receipt_path.resolve()
    root = root.resolve()
    _require(receipt_path.is_file(), f"receipt is not a file: {receipt_path}")
    _require(root != receipt_path and root not in receipt_path.parents,
             "receipt must be outside the source tree to avoid a circular tree hash")
    _require(re.fullmatch(r"[0-9a-f]{64}", expected_receipt_sha256 or "") is not None,
             "expected receipt SHA-256 must be supplied as 64 lowercase hex characters")
    _require(sha256_file(receipt_path) == expected_receipt_sha256, "receipt SHA-256 mismatch")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptRefused(f"receipt is not valid JSON: {exc}") from exc

    _require(receipt.get("schema") == SCHEMA, f"receipt schema must be {SCHEMA}")
    _require(receipt.get("status") == "PASS", "receipt status must be PASS")

    source = receipt.get("source")
    _require(isinstance(source, dict), "source block is required")
    expected_tree = source.get("tree_sha256")
    _require(isinstance(expected_tree, str) and re.fullmatch(r"[0-9a-f]{64}", expected_tree) is not None,
             "source.tree_sha256 must be lowercase SHA-256")
    _require(source_tree_sha256(root) == expected_tree, "source tree SHA-256 mismatch")

    execution = receipt.get("execution")
    _require(isinstance(execution, dict), "execution block is required")
    _require(execution.get("profile") == PROFILE, f"execution.profile must be {PROFILE}")
    argv = execution.get("argv")
    _require(isinstance(argv, list) and all(isinstance(x, str) and x for x in argv),
             "execution.argv must be a non-empty string array")
    _require(len(argv) >= 2 and argv[1:] == COMMAND_TAIL,
             "execution.argv must be an interpreter followed by the exact configured full-suite command")
    _require(execution.get("cwd") == ".", "execution.cwd must be '.'")
    _require(execution.get("exit_code") == 0, "execution.exit_code must be 0")
    for key in ("python_version", "pytest_version", "platform"):
        _require(isinstance(execution.get(key), str) and execution[key].strip(),
                 f"execution.{key} is required")

    started = _utc(execution.get("started_utc"), "execution.started_utc")
    completed = _utc(execution.get("completed_utc"), "execution.completed_utc")
    _require(completed >= started, "execution.completed_utc precedes started_utc")
    current = now or datetime.now(timezone.utc)
    _require(completed <= current + timedelta(minutes=5), "receipt completion time is in the future")
    _require(current - completed <= max_age, "external validation receipt is older than 24 hours")

    artifacts = receipt.get("artifacts")
    _require(isinstance(artifacts, dict), "artifacts block is required")
    log_path = _resolve_artifact(receipt_path, root, artifacts.get("pytest_log"), "pytest_log")
    identity_block = artifacts.get("test_identity")
    identity_path = _resolve_artifact(receipt_path, root, identity_block, "test_identity")
    outcomes_path = _resolve_artifact(receipt_path, root, artifacts.get("test_results"), "test_results")

    nodeids = _read_identity(identity_path, identity_block.get("count"))
    outcomes, observed_counts = _read_outcomes(outcomes_path)
    _require(set(nodeids) == set(outcomes), "test identity and result node-ID sets differ")

    declared_counts = receipt.get("results")
    _require(isinstance(declared_counts, dict), "results block is required")
    for name in OUTCOMES:
        _require(declared_counts.get(name) == observed_counts[name],
                 f"results.{name} does not match the per-node result artifact")
    _require(declared_counts.get("total") == len(nodeids), "results.total does not match exact identity count")
    _require(observed_counts["failed"] == 0 and observed_counts["errors"] == 0,
             "external validation contains failed or error outcomes")
    _require(observed_counts["passed"] > 0, "external validation contains no passing tests")
    _require(_log_counts(log_path) == observed_counts, "pytest log summary does not match exact outcomes")
    return log_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Exact source tree validated by the suite")
    parser.add_argument("--receipt", type=Path, help="Structured external-validation receipt JSON")
    parser.add_argument("--expected-receipt-sha256", help="Out-of-band expected receipt SHA-256")
    parser.add_argument("--emit-tree-sha256", action="store_true", help="Print this verifier's source-tree digest")
    parser.add_argument("--print-log-path", action="store_true", help="On PASS print only the verified log path")
    args = parser.parse_args(argv)
    try:
        if args.emit_tree_sha256:
            sys.stdout.write(source_tree_sha256(args.root) + "\n")
            return 0
        _require(args.receipt is not None, "--receipt is required")
        log_path = verify_receipt(args.receipt, args.root, args.expected_receipt_sha256 or "")
    except ReceiptRefused as exc:
        sys.stderr.write(f"EXTERNAL VALIDATION RECEIPT: REFUSED: {exc}\n")
        return 2
    if args.print_log_path:
        sys.stdout.write(str(log_path) + "\n")
    else:
        sys.stdout.write(f"EXTERNAL VALIDATION RECEIPT: PASS ({log_path})\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
