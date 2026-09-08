"""v9.7.243: the monolith is the parent design controller (20 referrers, incl. the system prompt).
Its content is reviewed at checkpoints, not every patch — that convention is fine. Silent anchor rot
is not: at v9.7.242 it still claimed "current bundle 9.7.57 / engine 1.9.64", 185 cuts behind."""
import subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "check_monolith_freshness.py"


def _run(*a):
    return subprocess.run([sys.executable, str(GATE), *a], capture_output=True, text=True, cwd=str(ROOT))


def test_gate_passes_on_the_shipped_monolith():
    r = _run("--quiet")
    assert r.returncode == 0, r.stdout + r.stderr


def test_gate_fails_on_asserted_retired_doctrine(tmp_path):
    mono = ROOT / "docs" / "SAPOTE_MAMEY_BUNDLE_MONOLITH.md"
    original = mono.read_text(encoding="utf-8")
    try:
        mono.write_text(original + "\nAssembly tiers: GOOD >= 66%, POOR >= 33%.\n", encoding="utf-8")
        assert _run("--quiet").returncode == 1
    finally:
        mono.write_text(original, encoding="utf-8")


def test_denials_are_not_flagged():
    """'no AS_SCRUB', 'BSL-2 flagging retired' state the CORRECT position and must not fail the gate.
    The first version of this gate flagged its own freshly-written denial line."""
    r = _run("--quiet")
    assert r.returncode == 0
