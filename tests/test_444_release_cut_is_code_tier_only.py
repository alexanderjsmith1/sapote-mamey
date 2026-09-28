"""Releases cut the CODE tier only; the other four tiers are kept in the bundle but disabled (Alex, 2026-09-28).

"we were planning to disable the four tiers from the cut process and leave the tooling in a disabled location
within the bundle". The tooling stays (tests that exercise it set SAPOTE_ENABLE_DISABLED_TIERS=1).
"""
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_release_cut_loops_over_the_code_tier_by_default():
    text = (ROOT / "tools" / "release_cut.sh").read_text()
    assert 'CUT_TIERS="${CUT_TIERS:-code}"' in text
    assert "for tier in $CUT_TIERS; do" in text
    assert "for tier in code clean sid merged public" not in text


@pytest.mark.parametrize("tier", ["clean", "cohort", "sid", "merged", "public"])
def test_disabled_tiers_refuse_without_the_flag(tmp_path, tier):
    env = {k: v for k, v in os.environ.items() if k != "SAPOTE_ENABLE_DISABLED_TIERS"}
    r = subprocess.run(["bash", str(ROOT / "tools" / "make_public_tier.sh"), tier, str(ROOT), str(tmp_path / "out")],
                       env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "is disabled" in r.stderr
    assert not (tmp_path / "out").exists()


def test_the_four_tier_driver_refuses_without_the_flag(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "SAPOTE_ENABLE_DISABLED_TIERS"}
    r = subprocess.run(["bash", str(ROOT / "tools" / "release.sh"), "20260101v00000a", str(tmp_path / "out")],
                       env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "disabled" in r.stderr


def test_cut_protocol_documents_the_code_only_cut():
    text = (ROOT / "CUT_PROTOCOL.md").read_text()
    assert "SAPOTE_ENABLE_DISABLED_TIERS" in text and "CODE tier only" in text
