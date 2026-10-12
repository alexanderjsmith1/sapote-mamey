"""Capture actual pytest identities and outcomes for partition validation.

This internal plugin does not select tests, change their outcomes or infer node IDs
from JUnit names. Its external receipt is evidence, never by itself a green gate.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from _release_validation import atomic_json, utc_now


SCHEMA = "sapote-mamey.pytest-execution.v1"


def pytest_addoption(parser):
    """Register the external evidence destination without changing test selection."""
    parser.addoption("--release-evidence", metavar="PATH", default=None,
                     help="Write actual collection and outcomes outside the source tree")


def pytest_configure(config):
    """Admit a fresh external path and register a per-session recorder."""
    supplied = config.getoption("release_evidence")
    if supplied is None:
        return
    destination = Path(supplied)
    if not destination.is_absolute():
        raise pytest.UsageError("--release-evidence must be an absolute external path")
    destination = destination.resolve()
    if destination.is_relative_to(Path(config.rootpath).resolve()):
        raise pytest.UsageError("--release-evidence must be outside the source tree")
    if destination.exists():
        raise pytest.UsageError("--release-evidence destination already exists")
    config.pluginmanager.register(ExecutionEvidence(config, destination),
                                  "release-execution-evidence")


class ExecutionEvidence:
    """Retain the measured collection, phase reports, subtests and final exit code."""

    def __init__(self, config, destination):
        self.destination = destination
        self.data = {
            "schema": SCHEMA, "started_utc": utc_now(),
            "rootpath": str(Path(config.rootpath).resolve()),
            "pytest_version": pytest.__version__,
            "invocation_args": list(config.invocation_params.args),
            "inifile": str(config.inipath) if config.inipath else None,
            "collected": [], "deselected": [], "collection_skips": [],
            "collection_errors": [], "phase_reports": [], "subtests": [],
            "collection_finished": False,
        }

    def pytest_collection_finish(self, session):
        """Record exact main node identities after normal collection hooks finish."""
        self.data["collected"] = [item.nodeid for item in session.items]
        self.data["collection_finished"] = True

    def pytest_deselected(self, items):
        """Keep exclusions explicit so a runner can reject weakened coverage."""
        self.data["deselected"].extend(item.nodeid for item in items)

    def pytest_collectreport(self, report):
        """Keep module-level skips and collection errors distinct from main nodes."""
        if report.skipped or report.failed:
            key = "collection_skips" if report.skipped else "collection_errors"
            self.data[key].append({"nodeid": report.nodeid,
                                   "reason": str(report.longrepr)})

    def pytest_runtest_logreport(self, report):
        """Record setup/call/teardown independently and identify subtest reports."""
        row = {"nodeid": report.nodeid, "when": report.when,
               "outcome": report.outcome, "duration": report.duration,
               "reason": str(report.longrepr) if report.longrepr else None,
               "wasxfail": str(report.wasxfail) if hasattr(report, "wasxfail") else None}
        if hasattr(report, "context"):
            row["context"] = repr(report.context)
            self.data["subtests"].append(row)
        else:
            self.data["phase_reports"].append(row)

    @pytest.hookimpl(wrapper=True, tryfirst=True)
    def pytest_sessionfinish(self, session, exitstatus):
        """Write measured results after other session-finish hooks have completed."""
        result = yield
        grouped = {}
        for row in self.data["phase_reports"]:
            grouped.setdefault(row["nodeid"], []).append(row)
        outcomes = []
        for nodeid in self.data["collected"]:
            rows = grouped.get(nodeid, [])
            failures = [r for r in rows if r["outcome"] == "failed"]
            skips = [r for r in rows if r["outcome"] == "skipped"]
            calls = [r for r in rows if r["when"] == "call"]
            phases = [r["when"] for r in rows]
            if any(r["when"] != "call" for r in failures):
                outcome = "error"
            elif failures:
                outcome = "failed"
            elif skips:
                outcome = "skipped"
            elif (len(calls) == 1 and calls[0]["outcome"] == "passed"
                  and phases == ["setup", "call", "teardown"]):
                outcome = "passed"
            else:
                outcome = "incomplete"
            outcomes.append({"nodeid": nodeid, "outcome": outcome,
                             "reasons": [r["reason"] for r in rows if r["reason"]],
                             "wasxfail": [r["wasxfail"] for r in rows if r["wasxfail"]]})
        collected = self.data["collected"]
        self.data.update({"completed_utc": utc_now(), "exit_code": int(session.exitstatus),
                          "testscollected": session.testscollected,
                          "outcomes": outcomes,
                          "counts": dict(Counter(r["outcome"] for r in outcomes)),
                          "subtest_counts": dict(Counter(r["outcome"] for r in self.data["subtests"])),
                          "duplicate_collected": sorted(n for n, c in Counter(collected).items() if c > 1),
                          "unexpected_report_nodes": sorted(set(grouped) - set(collected))})
        atomic_json(self.destination, self.data)
        return result
