"""The package run reports what the record-limit probe established: truncation, nothing (NOT_DETECTED), or
coverage unverified for every other probe state (P300-125 follow-up, owner ruling 14 Oct 2026)."""
import zipfile
from pathlib import Path

import pytest

from mamey.parsers import antismash_record_limit_truncation, record_limit_coverage_issue

CLI = Path(__file__).resolve().parents[1] / "mamey" / "cli.py"


def _zip(tmp_path, logs):
    z = tmp_path / "r.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("r/r.gbk", "LOCUS x\n//\n")
        for name, text in logs.items():
            zf.writestr(name, text)
    return z


def test_not_detected_raises_no_issue(tmp_path):
    probe = antismash_record_limit_truncation(_zip(tmp_path, {"r/antismash.log": "antiSMASH 8.0 run complete\n"}))
    assert probe["probe_state"] == "NOT_DETECTED" and record_limit_coverage_issue(probe) is None


@pytest.mark.parametrize("logs,state", [({}, "UNAVAILABLE"), ({"r/other.log": "unrelated tool\n"}, "UNRECOGNISED_LOG")])
def test_unverified_states_say_unverified_not_truncated(tmp_path, logs, state):
    probe = antismash_record_limit_truncation(_zip(tmp_path, logs))
    issue = record_limit_coverage_issue(probe)
    assert probe["probe_state"] == state
    assert issue.startswith("RECORD_LIMIT_COVERAGE_UNVERIFIED") and f"probe_state={state}" in issue
    assert "not evidence of truncation" in issue and "RECORD_LIMIT_TRUNCATION" not in issue


def test_failed_probe_is_unverified():
    issue = record_limit_coverage_issue({"truncated": False, "probe_state": "FAILED", "logs_read": 0})
    assert issue.startswith("RECORD_LIMIT_COVERAGE_UNVERIFIED") and "could not be read" in issue


def test_truncation_keeps_its_wording(tmp_path):
    log = "antiSMASH\nOnly analysing the first 1000 records\nNot annotating skipped record c1001: skipping all but largest 1000 meaningful records\n"
    issue = record_limit_coverage_issue(antismash_record_limit_truncation(_zip(tmp_path, {"r/antismash.log": log})))
    assert issue.startswith("RECORD_LIMIT_TRUNCATION: antiSMASH analysed only the largest 1000 records")
    assert "1 eligible records were skipped (first c1001)" in issue and "FLOOR" in issue


def test_package_run_uses_the_helper():
    src = CLI.read_text(encoding="utf-8")
    assert "record_limit_coverage_issue" in src and "_rlci(_artl(input_zip))" in src
