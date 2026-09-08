"""Fixtures for the v9.7.412 waiver-slack visibility check (BLIZZARD_BLUE-412)."""
import json

import pytest

from tools.repo_health import _RATCHETS, check_waiver_slack

SCHEMA = "sapote.strict_health_waiver/1"


def _write(tmp_path, metric, observed, ceiling=None):
    """v9.7.414: `ceiling` was filler (`1`) and is now MEANINGFUL — it is the signing ceiling.

    `_waiver_covers` reads it, so a fixture writing `ceiling: 1` describes an INACTIVE waiver and
    `check_waiver_slack` correctly reports no coverage rather than slack. These fixtures test the
    slack of an ACTIVE waiver, so they must sign at the enforced ceiling. The old value was never
    wrong on purpose; it was arbitrary, and a field that is arbitrary in a fixture is a field that
    will surprise someone the day it acquires meaning.
    """
    if ceiling is None:
        # an unratcheted metric has no enforced ceiling; the slack check skips it either way
        ceiling = _ceiling(metric) if metric in _RATCHETS else 1
    (tmp_path / "STRICT_HEALTH_WAIVER.json").write_text(json.dumps({
        "schema_version": SCHEMA, "cut": "v9.7.372",
        "waivers": [{"metric": metric, "ceiling": ceiling, "observed": observed,
                     "owner": "owner", "reason": "fixture"}]}), encoding="utf-8")
    return tmp_path


def _ceiling(metric):
    import tools.repo_health as rh
    return getattr(rh, _RATCHETS[metric])


def test_no_waiver_file_is_ok(tmp_path):
    r = check_waiver_slack(tmp_path)
    assert r.status == "OK" and r.hits == []


def test_waiver_at_the_ceiling_reports_no_slack(tmp_path):
    _write(tmp_path, "silent_swallow", _ceiling("silent_swallow"))
    r = check_waiver_slack(tmp_path)
    assert r.status == "OK", "observed == ceiling grants no regression room"


def test_waiver_below_the_ceiling_reports_no_slack(tmp_path):
    _write(tmp_path, "silent_swallow", _ceiling("silent_swallow") - 5)
    assert check_waiver_slack(tmp_path).status == "OK"


@pytest.mark.parametrize("extra", [1, 42, 340])
def test_waiver_above_the_ceiling_reports_exact_slack(tmp_path, extra):
    metric = "print_calls"
    _write(tmp_path, metric, _ceiling(metric) + extra)
    r = check_waiver_slack(tmp_path)
    assert r.status == "INFO"
    assert len(r.hits) == 1
    assert f"up to {extra} count(s)" in r.hits[0]
    assert metric in r.hits[0]


def test_unknown_metric_is_ignored(tmp_path):
    _write(tmp_path, "not_a_ratcheted_metric", 10 ** 6)
    assert check_waiver_slack(tmp_path).status == "OK"


def test_malformed_waiver_does_not_raise(tmp_path):
    (tmp_path / "STRICT_HEALTH_WAIVER.json").write_text("{not json", encoding="utf-8")
    assert check_waiver_slack(tmp_path).status == "OK"


def test_a_waiver_signed_against_a_different_ceiling_reports_inactive(tmp_path):
    """v9.7.414: the live .413 state — signed ceiling no longer matches enforced."""
    _write(tmp_path, "print_calls", _ceiling("print_calls") + 300, ceiling=1)
    r = check_waiver_slack(tmp_path)
    assert r.status == "INFO"
    assert any("inactive signing ceiling" in h for h in r.hits), r.hits
