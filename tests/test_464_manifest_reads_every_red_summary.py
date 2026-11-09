"""gen_release_manifest refuses a log whose later pytest summary is red."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from gen_release_manifest import counts_from_log  # noqa: E402


def _log(tmp_path, text):
    p = tmp_path / "pytest.log"
    p.write_text(text)
    return p


def test_earlier_zero_failed_does_not_hide_a_later_red_summary(tmp_path):
    log = _log(tmp_path, "== 0 failed, 120 passed in 3.0s ==\n== 2 failed, 118 passed in 3.1s ==\n")
    with pytest.raises(SystemExit, match="2 failed"):
        counts_from_log(log)


def test_failure_only_summary_is_refused(tmp_path):
    log = _log(tmp_path, "== 120 passed in 3.0s ==\n== 1 error in 0.4s ==\n")
    with pytest.raises(SystemExit, match="1 error"):
        counts_from_log(log)


def test_green_log_still_reads(tmp_path):
    assert counts_from_log(_log(tmp_path, "== 120 passed, 4 skipped in 3.0s ==\n")) == (120, 4)
