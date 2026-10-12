"""Internal coverage and provenance checks for explicit partitioned validation.

Partition receipts use their own schema. No aggregate is represented as execution
of the monolithic command accepted by verify_external_validation_receipt.py.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path, PurePosixPath

from _release_validation import ValidationRefused, canonical_json


SCHEMA = "sapote-mamey.partitioned-pytest-validation.v1"
BASELINE_SCHEMA = "sapote-mamey.partitioned-pytest-baseline.v1"
PROFILE = "configured-full-suite-partitioned"
FLAGS = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "--run-slow", "--run-network"]
CAPTURE_SCHEMA = "sapote-mamey.pytest-execution.v1"


def require(condition: bool, message: str) -> None:
    """Refuse invalid coverage or evidence with a stable typed exception."""
    if not condition:
        raise ValidationRefused(message)


def utc(value: object, label: str) -> datetime:
    """Require an aware UTC timestamp instead of guessing timezone or age."""
    require(isinstance(value, str) and value.endswith("Z"), label + " must be UTC ending in Z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValidationRefused(label + " is not an ISO timestamp") from exc


def validate_age(data: dict, *, now: datetime | None = None,
                 max_age: timedelta = timedelta(hours=24)) -> None:
    """Refuse stale or inconsistent execution times before evidence reuse."""
    started = utc(data.get("started_utc"), "started_utc")
    completed = utc(data.get("completed_utc"), "completed_utc")
    current = now or datetime.now(timezone.utc)
    require(max_age.total_seconds() > 0, "maximum evidence age must be positive")
    require(started <= completed, "execution timestamps run backwards")
    require(completed <= current + timedelta(minutes=5), "execution completion is in the future")
    require(current - started <= max_age, "execution evidence is expired")


def node_ids(value: object, label: str, *, allow_empty: bool = False) -> list[str]:
    """Validate lossless actual node IDs; do not parse them as JUnit class names."""
    require(isinstance(value, list), label + " must be an array")
    require(allow_empty or bool(value), label + " must not be empty")
    require(all(isinstance(n, str) and n and "\0" not in n and "\n" not in n for n in value),
            label + " contains invalid node IDs")
    require(len(value) == len(set(value)), label + " contains duplicate node IDs")
    return value


def partition_plan(collected: list[str], files_per_partition: int = 20) -> list[dict]:
    """Schedule every collected main node exactly once in deterministic file groups."""
    nodes = node_ids(collected, "collected")
    require(isinstance(files_per_partition, int) and not isinstance(files_per_partition, bool)
            and files_per_partition > 0, "files_per_partition must be a positive integer")
    files = {}
    for node in nodes:
        filename = node.split("::", 1)[0]
        path = PurePosixPath(filename)
        require(not path.is_absolute() and ".." not in path.parts and filename.endswith(".py"),
                "unsupported or unsafe collected test path: " + filename)
        files.setdefault(filename, []).append(node)
    names = list(files)
    groups = []
    for offset in range(0, len(names), files_per_partition):
        selected = names[offset:offset + files_per_partition]
        expected = [node for node in nodes if node.split("::", 1)[0] in selected]
        groups.append({"id": f"partition-{len(groups) + 1:04d}", "files": selected,
                       "expected_nodes": expected})
    union = [node for group in groups for node in group["expected_nodes"]]
    require(Counter(union) == Counter(nodes), "partition plan does not cover every node exactly once")
    return groups


def validate_capture(data: object, expected_nodes: list[str] | None = None, *,
                     collect_only: bool = False, now: datetime | None = None,
                     max_age: timedelta = timedelta(hours=24),
                     measure_assertion_failures: bool = False) -> dict:
    """Derive counts from complete phase evidence; never trust declared summaries alone."""
    require(isinstance(data, dict), "pytest capture must be an object")
    require(data.get("schema") == CAPTURE_SCHEMA, "pytest capture schema mismatch")
    measuring = measure_assertion_failures and not collect_only
    require(data.get("exit_code") in ({0, 1} if measuring else {0}), "pytest process did not exit green")
    require(data.get("collection_finished") is True, "pytest collection did not finish")
    validate_age(data, now=now, max_age=max_age)
    collected = node_ids(data.get("collected"), "collected")
    if expected_nodes is not None:
        node_ids(expected_nodes, "expected_nodes")
        require(collected == expected_nodes, "collected node identities/order differ from the scheduled partition")
    for key in ("deselected", "collection_errors", "duplicate_collected", "unexpected_report_nodes"):
        require(data.get(key) == [], key + " is not empty or is missing")
    require(data.get("testscollected") == len(collected), "pytest testscollected differs from node identities")
    skips = data.get("collection_skips")
    require(isinstance(skips, list), "collection_skips must be an array")
    require(all(isinstance(r, dict) and isinstance(r.get("nodeid"), str)
                and isinstance(r.get("reason"), str) and r["reason"] for r in skips),
            "collection skip identity/reason is missing")
    skip_ids = [r["nodeid"] for r in skips]
    require(len(skip_ids) == len(set(skip_ids)), "duplicate collection skip identities")
    outcomes = data.get("outcomes")
    require(isinstance(outcomes, list) and all(isinstance(r, dict) for r in outcomes),
            "main outcomes must be objects")
    outcome_ids = node_ids([r.get("nodeid") for r in outcomes], "outcome identities")
    require(outcome_ids == collected, "outcome identities/order do not exactly cover collection")
    phase_rows = data.get("phase_reports")
    subtests = data.get("subtests")
    require(isinstance(phase_rows, list) and isinstance(subtests, list), "phase/subtest reports are missing")
    counts = Counter(r.get("outcome") for r in outcomes)
    require(data.get("counts") == dict(counts), "declared main counts disagree with actual outcomes")
    if collect_only:
        require(not phase_rows and not subtests, "collect-only evidence unexpectedly executed tests")
        require(set(counts) == {"incomplete"}, "collect-only outcomes must remain unexecuted")
    else:
        allowed = {"passed", "skipped", "failed"} if measuring else {"passed", "skipped"}
        require(set(counts) <= allowed, "partition has failed, errored or incomplete main nodes")
        grouped = {node: [] for node in collected}
        for row in phase_rows:
            require(isinstance(row, dict) and row.get("nodeid") in grouped, "uncollected phase report")
            require(row.get("outcome") in allowed, "failed or malformed phase report")
            require(row.get("outcome") != "failed" or row.get("when") == "call",
                    "baseline has a setup/teardown error, not a measured assertion failure")
            grouped[row["nodeid"]].append(row)
        for result in outcomes:
            rows = grouped[result["nodeid"]]
            phases = [r.get("when") for r in rows]
            setup_skipped = bool(rows) and rows[0].get("when") == "setup" and rows[0].get("outcome") == "skipped"
            require(phases == (["setup", "teardown"] if setup_skipped else ["setup", "call", "teardown"]),
                    "missing, duplicated or reordered test phases: " + result["nodeid"])
            observed = ("failed" if any(r["outcome"] == "failed" for r in rows)
                        else "skipped" if any(r["outcome"] == "skipped" for r in rows) else "passed")
            require(result.get("outcome") == observed, "declared main outcome disagrees with test phases")
        for row in subtests:
            require(isinstance(row, dict) and row.get("nodeid") in grouped, "uncollected subtest report")
            require(row.get("when") == "call" and row.get("outcome") in allowed,
                    "failed or malformed subtest report")
    subcounts = Counter(r.get("outcome") for r in subtests)
    require(data.get("subtest_counts") == dict(subcounts), "declared subtest counts disagree with reports")
    if measuring:
        failed = counts["failed"] + subcounts["failed"]
        require((data["exit_code"] == 1) == (failed > 0), "baseline exit code and observed failures disagree")
    return {"main_counts": dict(counts), "main_nodes": len(collected),
            "collection_skips": len(skips), "subtest_counts": dict(subcounts)}


def input_binding(*, source_sha256: str, environment_sha256: str,
                  machinery_sha256: str, files_per_partition: int, purpose: str = "final") -> dict:
    """Bind the exact source/configuration, measured environment and runner code."""
    for label, value in (("source", source_sha256), ("environment", environment_sha256),
                         ("machinery", machinery_sha256)):
        require(isinstance(value, str) and len(value) == 64
                and all(c in "0123456789abcdef" for c in value), label + " digest is not SHA-256")
    require(isinstance(files_per_partition, int) and not isinstance(files_per_partition, bool)
            and files_per_partition > 0, "files_per_partition must be positive")
    require(purpose in {"final", "baseline"}, "unknown partition purpose")
    data = {"profile": PROFILE, "purpose": purpose, "source_tree_sha256": source_sha256,
            "environment_identity_sha256": environment_sha256, "machinery_sha256": machinery_sha256,
            "flags": list(FLAGS), "files_per_partition": files_per_partition}
    return {**data, "sha256": hashlib.sha256(canonical_json(data)).hexdigest()}
