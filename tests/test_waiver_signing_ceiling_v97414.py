"""The signing ceiling comes from the schema's existing `ceiling` field (BLIZZARD_BLUE-414).

v9.7.412 added `ceiling_at_signing`. The schema already had `ceiling` for the same purpose, and
nothing adopted the new field, so the guard never fired. These fixtures pin BOTH sources.
"""
import pytest

from tools.repo_health import _ratchet_ceiling, _waiver_covers

M = "print_calls"


def _w(observed, ceiling=None, at_signing=None):
    w = {"metric": M, "observed": observed, "owner": "o", "reason": "r"}
    if ceiling is not None:
        w["ceiling"] = ceiling
    if at_signing is not None:
        w["ceiling_at_signing"] = at_signing
    return w


def test_the_live_v9_7_413_waiver_state_is_now_voided():
    """print_calls: signed ceiling 1300, enforced 1280, count 1320 -> must NOT be covered."""
    assert _ratchet_ceiling(M) != 1300, "fixture assumes the ceiling has moved since signing"
    assert _waiver_covers(_w(1620, ceiling=1300), 1320) is False


def test_matching_signing_ceiling_still_covers():
    now = _ratchet_ceiling(M)
    assert _waiver_covers(_w(now + 300, ceiling=now), now + 100) is True


@pytest.mark.parametrize("drift", [-20, -1, 1, 40])
def test_any_drift_from_the_signed_ceiling_voids(drift):
    now = _ratchet_ceiling(M)
    assert _waiver_covers(_w(now + 300, ceiling=now + drift), now + 100) is False


def test_ceiling_at_signing_still_wins_when_present():
    """The explicit field takes precedence over the legacy `ceiling`."""
    now = _ratchet_ceiling(M)
    assert _waiver_covers(_w(now + 300, ceiling=999, at_signing=now), now + 100) is True
    assert _waiver_covers(_w(now + 300, ceiling=now, at_signing=999), now + 100) is False


def test_observed_remains_the_hard_upper_limit():
    now = _ratchet_ceiling(M)
    assert _waiver_covers(_w(now + 10, ceiling=now), now + 11) is False


def test_a_waiver_with_neither_field_keeps_legacy_behaviour():
    assert _waiver_covers(_w(10**6), 1320) is True


def test_non_int_ceiling_is_ignored_not_crashed():
    assert _waiver_covers(_w(10**6, ceiling="1300"), 1320) is True
