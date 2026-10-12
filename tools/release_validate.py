#!/usr/bin/env python3
"""Admit an existing test interpreter and produce measured release-validation evidence."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

from _console import emit
from _release_validation import (
    DEFAULT_MIN_DISK,
    DEFAULT_RSS_LIMIT,
    ValidationRefused,
    admit_environment,
)


def retries(values: list[str]) -> dict[str, str]:
    """Require a distinct explicit disposition for every named failed stage."""
    result = {}
    for value in values:
        stage, separator, reason = value.partition("=")
        if not separator or not stage or not reason.strip() or stage in result:
            raise ValidationRefused("--retry must be a unique STAGE=reason entry")
        result[stage] = reason
    return result


@dataclass(frozen=True)
class Outcome:
    """A command result independent of terminal delivery or logging settings."""

    text: str
    code: int = 0
    stderr: bool = False


def parse_args(argv: list[str] | None = None):
    """Parse the bounded validation command without running an operation."""
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="operation", required=True)
    preflight = subcommands.add_parser("preflight", help="Probe existing Python/pytest and an offline disposable venv")
    preflight.add_argument("--python", default=sys.executable, help="Existing Python executable or command")
    preflight.add_argument("--out", required=True, type=Path, help="Fresh evidence directory outside the source tree")
    preflight.add_argument("--rss-limit", type=int, default=DEFAULT_RSS_LIMIT, help="Process-tree RSS stop threshold in bytes")
    preflight.add_argument("--min-free-disk", type=int, default=DEFAULT_MIN_DISK, help="Minimum free disk bytes")
    preflight.add_argument("--probe-timeout", type=float, default=120, help="Seconds per admission probe")
    partition = subcommands.add_parser("partition", help="Run or resume the explicit configured partition profile")
    partition.add_argument("--source", required=True, type=Path)
    partition.add_argument("--out", required=True, type=Path, help="External evidence root; fresh unless --resume")
    partition.add_argument("--python", default=sys.executable)
    partition.add_argument("--files-per-partition", type=int, default=20)
    partition.add_argument("--rss-limit", type=int, default=DEFAULT_RSS_LIMIT)
    partition.add_argument("--min-free-disk", type=int, default=DEFAULT_MIN_DISK)
    partition.add_argument("--timeout", type=float, default=3600)
    partition.add_argument("--resume", action="store_true")
    partition.add_argument("--retry", action="append", default=[], metavar="STAGE=REASON")
    partition.add_argument("--baseline", action="store_true",
                           help="Measure test-call failures as a distinct MEASURED baseline; never final PASS")
    verify = subcommands.add_parser("verify", help="Re-admit the current environment and independently verify a partition receipt")
    verify.add_argument("--source", required=True, type=Path)
    verify.add_argument("--receipt", required=True, type=Path)
    verify.add_argument("--sha256", required=True)
    verify.add_argument("--python", default=sys.executable)
    verify.add_argument("--out", required=True, type=Path, help="Fresh environment-verification evidence directory")
    verify_baseline = subcommands.add_parser("verify-baseline", help="Verify a measured baseline without admitting it as final validation")
    verify_baseline.add_argument("--source", required=True, type=Path)
    verify_baseline.add_argument("--receipt", required=True, type=Path)
    verify_baseline.add_argument("--sha256", required=True)
    verify_baseline.add_argument("--python", default=sys.executable)
    verify_baseline.add_argument("--out", required=True, type=Path)
    smoke = subcommands.add_parser("import-smoke", help="Inventory and test the complete production import roster in admitted controlled workers")
    smoke.add_argument("--source", required=True, type=Path)
    smoke.add_argument("--out", required=True, type=Path)
    smoke.add_argument("--python", default=sys.executable)
    verify_import = subcommands.add_parser("verify-import", help="Re-admit the current environment and verify complete import evidence")
    verify_import.add_argument("--source", required=True, type=Path)
    verify_import.add_argument("--receipt", required=True, type=Path)
    verify_import.add_argument("--sha256", required=True)
    verify_import.add_argument("--python", default=sys.executable)
    verify_import.add_argument("--out", required=True, type=Path)
    return parser.parse_args(argv)


def run_operation(args) -> Outcome:
    """Produce exactly one result, preserving the operation's refusal status."""
    try:
        if args.operation == "import-smoke":
            from _release_import_smoke import run_import_smoke
            report = run_import_smoke(args.source, args.out, args.python)
            return Outcome("CONTROLLED IMPORT SMOKE: " + report["status"] + " — "
                           + str(args.out / "import-smoke.json"), 0 if report["status"] == "PASS" else 2)
        if args.operation == "verify-import":
            from _release_import_smoke import verify_import_receipt
            from _release_partition_runner import test_environment
            from _release_validation import atomic_json
            environment = admit_environment(args.python, output=args.out, env=test_environment(args.source.resolve()))
            if environment['status'] != 'READY':
                raise ValidationRefused('Current import-verification environment refused')
            summary = verify_import_receipt(args.source,args.receipt,args.sha256,environment['identity_sha256'])
            atomic_json(args.out/'import-verification.json', {'status':'VERIFIED_IMPORTS','receipt_sha256':args.sha256,
                                                            'summary':summary})
            return Outcome('CONTROLLED IMPORT SMOKE: VERIFIED — '+str(args.out/'import-verification.json'))
        if args.operation == "partition":
            from _release_partition_runner import PartitionRunner
            report = PartitionRunner(args.source, args.out, args.python,
                files_per_partition=args.files_per_partition, rss_limit=args.rss_limit,
                min_disk=args.min_free_disk, timeout=args.timeout, baseline=args.baseline).run(resume=args.resume, retry=retries(args.retry))
            return Outcome(("RELEASE BASELINE: " if args.baseline else "RELEASE PARTITIONS: ")
                           + report["status"] + " — " + str(args.out / "partition.json"))
        if args.operation in {"verify", "verify-baseline"}:
            from _release_partition_runner import test_environment, verify_partition_receipt
            environment = admit_environment(args.python, output=args.out,
                                             env=test_environment(args.source.resolve()))
            if environment["status"] != "READY":
                raise ValidationRefused("Current environment refused; see " + str(args.out))
            summary = verify_partition_receipt(args.receipt, args.source, args.sha256,
                                               environment["identity_sha256"], baseline=args.operation == "verify-baseline")
            return Outcome(("RELEASE BASELINE" if args.operation == "verify-baseline" else "RELEASE PARTITIONS")
                           + ": VERIFIED — " + str(summary["main_nodes"]) + " main nodes")
        report = admit_environment(args.python, output=args.out, rss_limit=args.rss_limit,
                                   min_disk=args.min_free_disk, probe_timeout=args.probe_timeout)
    except (ValidationRefused, OSError) as exc:
        return Outcome(f"RELEASE VALIDATION: REFUSED: {exc}", 2, stderr=True)
    if report["status"] != "READY":
        return Outcome("RELEASE ENVIRONMENT: REFUSED: " + report.get("reason", "probe incomplete")
                       + "\nEvidence: " + str(args.out / "environment.json"), 2, stderr=True)
    return Outcome("RELEASE ENVIRONMENT: READY — " + report["resolved_executable"]
                   + "\nEvidence: " + str(args.out / "environment.json"))


def main(argv: list[str] | None = None) -> int:
    """Deliver the selected result unfiltered, including when MAMEY_LOG is quiet."""
    outcome = run_operation(parse_args(argv))
    emit(outcome.text, file=sys.stderr if outcome.stderr else sys.stdout)
    return outcome.code


if __name__ == "__main__":
    raise SystemExit(main())
