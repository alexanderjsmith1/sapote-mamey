"""A package that failed validation must not be listed as a deliverable to hand to the user.

run used to print every sealed zip under "DELIVERABLES — hand these ... to the user", and
HANDBACK.json told an operator to surface each one, whatever its status.
"""
import inspect

from mamey import cli

OK = {"MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES", "PASS", "PASS_WITH_ISSUES"}


def test_success_without_blocking_issue_delivers():
    assert cli._run_result_delivers({"status": "MAMEY_COMPLETE", "issues": []}, OK)
    assert cli._run_result_delivers({"status": "MAMEY_COMPLETE_WITH_ISSUES", "issues": ["[WARN] x"]}, OK)


def test_failed_validation_is_held():
    assert not cli._run_result_delivers({"status": "VALIDATION_FAIL", "issues": []}, OK)
    assert not cli._run_result_delivers({"status": "FAIL"}, OK)


def test_blocking_issue_is_held_whatever_the_status():
    issue = "[BLOCKING] final post-seal validation status 'FAIL' is not a terminal success"
    assert not cli._run_result_delivers({"status": "MAMEY_COMPLETE", "issues": [issue]}, OK)


def test_handback_records_held_packages_separately():
    src = inspect.getsource(cli)
    assert '"held_packages": _held' in src
    assert "HELD — these packages did not pass validation" in src
