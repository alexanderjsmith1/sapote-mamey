"""Exercise privacy preflight alone: never invoke the archive builder."""
from pathlib import Path
import os
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "tools/make_public_tier.sh").read_text()
PREFLIGHT = SCRIPT.split("# BEGIN PUBLIC AS PRIVACY PREFLIGHT\n", 1)[1].split("# END PUBLIC AS PRIVACY PREFLIGHT", 1)[0]

@pytest.mark.parametrize("tier", ["code", "clean", "cohort", "public"])
@pytest.mark.parametrize("settings", [{"AS_SCRUB": "0"}, {"AS_GUARD_RETIRED": "1"}, {"AS_SCRUB": "invalid"}])
def test_public_cannot_disable_private_id_guard(tier, settings):
    env = {k: v for k, v in os.environ.items() if k not in {"AS_SCRUB", "AS_GUARD_RETIRED"}}
    result = subprocess.run(["bash", "-c", PREFLIGHT], env={**env, "TIER": tier, **settings}, capture_output=True, text=True)
    assert result.returncode == 2
    assert "check-only private-ID audit" in result.stderr

@pytest.mark.parametrize("tier", ["code", "clean", "cohort", "public", "merged"])
def test_default_preflight_is_nonmutating_and_admits_guarded_cut(tier, tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in {"AS_SCRUB", "AS_GUARD_RETIRED"}}
    result = subprocess.run(["bash", "-c", PREFLIGHT], cwd=tmp_path, env={**env, "TIER": tier}, capture_output=True, text=True)
    assert result.returncode == 0
    assert list(tmp_path.iterdir()) == []

def test_guard_defaults_are_private_and_detector_stays_check_only():
    assert 'AS_GUARD_RETIRED="${AS_GUARD_RETIRED:-0}"' in SCRIPT
    assert 'AS_SCRUB="${AS_SCRUB:-1}"' in SCRIPT
    assert '--walk --check-only --as-only' in SCRIPT
    assert SCRIPT.index("# BEGIN PUBLIC AS PRIVACY PREFLIGHT") < SCRIPT.index('ARCHIVE="$OUT/$NAME"')
