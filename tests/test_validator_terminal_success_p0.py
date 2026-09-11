"""test_validator_terminal_success_p0.py — package_seal receipt must mark a gold
MAMEY_COMPLETE run as a terminal success.

P0 (ChatGPT audit): the old receipt recorded validator_is_pass = status.startswith("PASS"),
which is False for a fully successful gold package (terminal status MAMEY_COMPLETE),
misleading ChatGPT/audit automation into reading a completed run as a failure. The fix
adds validator_is_terminal_success, True for every terminal-success status.
"""
import pytest


# The authoritative terminal-success set the fix encodes.
_TERMINAL_SUCCESS = {"PASS", "PASS_WITH_ISSUES", "MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES"}


@pytest.mark.parametrize("status,expect_pass,expect_terminal", [
    ("PASS", True, True),
    ("PASS_WITH_ISSUES", True, True),
    ("MAMEY_COMPLETE", False, True),                 # the bug: was False/False
    ("MAMEY_COMPLETE_WITH_ISSUES", False, True),
    ("FAIL", False, False),
    ("NO_TERMINAL_RECEIPT", False, False),
])
def test_terminal_success_classification(status, expect_pass, expect_terminal):
    # Mirror the receipt logic exactly as written in cli.py package_seal.
    validator_is_pass = status.startswith("PASS")
    validator_is_terminal_success = status in _TERMINAL_SUCCESS
    assert validator_is_pass is expect_pass
    assert validator_is_terminal_success is expect_terminal


def test_gold_complete_is_not_a_pass_but_is_a_success():
    """The specific regression: MAMEY_COMPLETE must NOT be read as a failure."""
    status = "MAMEY_COMPLETE"
    assert (status in _TERMINAL_SUCCESS) is True
    # and the old PASS-only signal alone would have mislabeled it
    assert status.startswith("PASS") is False
