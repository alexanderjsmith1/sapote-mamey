"""Fixtures for the optional `ceiling_at_signing` waiver field (BLIZZARD_BLUE-412)."""
import pytest

from tools.repo_health import _ratchet_ceiling, _waiver_covers

METRIC = "print_calls"


def _w(observed, signed=None):
    w = {"metric": METRIC, "observed": observed, "owner": "o", "reason": "r"}
    if signed is not None:
        w["ceiling_at_signing"] = signed
    return w


def test_legacy_waiver_without_the_field_is_unchanged():
    """No existing signed file may change behaviour on the day this lands."""
    assert _waiver_covers(_w(1620), 1500) is True
    assert _waiver_covers(_w(1620), 1621) is False


def test_matching_ceiling_still_covers():
    now = _ratchet_ceiling(METRIC)
    assert _waiver_covers(_w(now + 300, signed=now), now + 100) is True


@pytest.mark.parametrize("drift", [-20, -1, 1, 40])
def test_any_ceiling_movement_since_signing_voids_the_waiver(drift):
    """Down OR up: if the ground moved, re-sign. Silent extension is the defect."""
    now = _ratchet_ceiling(METRIC)
    assert _waiver_covers(_w(now + 300, signed=now + drift), now + 100) is False


def test_the_measured_v9_7_411_inversion_is_closed():
    """print_calls: ceiling 1280, signed at 1300, observed 1620 -> the 340-count band closes."""
    now = _ratchet_ceiling(METRIC)
    stale = _w(1620, signed=1300)
    assert now != 1300, "fixture assumes the ceiling has moved since signing"
    assert _waiver_covers(stale, now + 50) is False


def test_observed_ceiling_is_still_the_hard_limit():
    now = _ratchet_ceiling(METRIC)
    assert _waiver_covers(_w(now + 10, signed=now), now + 11) is False


def test_non_int_field_is_ignored_not_crashed():
    now = _ratchet_ceiling(METRIC)
    assert _waiver_covers(_w(now + 300, signed="1300"), now + 100) is True
