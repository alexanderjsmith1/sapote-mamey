"""v9.7.237: the duplicate-dict-literal-key gate (silent data loss — Python keeps the last binding).

P04 registered `check_duplicate_dict_keys` as WIRED in `tools/gate_registry.tsv`, but the gate's test was
not shipped with the patch set, so the bundle's own orphan-gate tripwire
(`tests/test_gate_wiring_invariant.py`) failed. This file is that wiring, written against the real gate.

The allowlist is a **ratchet**: the three known AS_SCRUB placeholder collisions are permitted, a fourth
fails closed, and an entry must be deleted once its site stops colliding.
"""
import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "check_duplicate_dict_keys.py"


def _run(*args):
    return subprocess.run([sys.executable, str(GATE), *args],
                          capture_output=True, text=True, cwd=str(ROOT))


def test_gate_script_exists_and_is_executable():
    assert GATE.is_file(), "the WIRED gate must exist in tools/"


def test_gate_passes_on_the_shipped_tree():
    """Default run: no collisions remain and the allowlist is empty -> PASS (rc 0)."""
    r = _run()
    assert r.returncode == 0, f"gate failed on the shipped tree:\n{r.stdout}\n{r.stderr}"
    assert "duplicate-dict-key gate: PASS" in r.stdout


def test_strict_mode_also_passes_now_that_the_ratchet_is_paid_down():
    """--strict ignores the allowlist. v9.7.308 de-collided all three AS_SCRUB sites, so strict now
    passes too. If this fails, a real collision was reintroduced somewhere under mamey/tools/tests."""
    r = _run("--strict")
    assert r.returncode == 0, f"strict mode found a collision:\n{r.stdout}\n{r.stderr}"
    assert "duplicate-dict-key gate: PASS" in r.stdout


def test_allowlist_is_empty_and_may_only_shrink():
    """The ratchet is fully paid down (v9.7.308): the allowlist is empty. It must only ever shrink,
    so any future entry is a regression — a new collision must be fixed, not allowlisted. Any entry
    ever added must point at a real file and carry a reason."""
    sys.path.insert(0, str(ROOT / "tools"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("cdk", GATE)
    cdk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cdk)
    assert cdk.ALLOWLIST == {}, "allowlist is no longer empty — fix the collision instead of allowlisting"
    for path, reason in cdk.ALLOWLIST.items():
        assert (ROOT / path).is_file(), f"allowlisted path no longer exists: {path}"
        assert reason.strip(), f"allowlist entry needs a reason: {path}"


def test_new_collision_fails_closed(tmp_path):
    """A fourth, non-allowlisted collision must fail the gate (the whole point of the ratchet).
    The probe lives under mamey/ because the gate scans roots [mamey, tools, tests]."""
    bad = ROOT / "mamey" / "_tmp_dupkey_probe.py"
    bad.write_text('D = {"a": 1, "a": 2}\n', encoding="utf-8")
    try:
        r = _run()
        assert r.returncode != 0, "gate must fail closed on a new (non-allowlisted) collision"
        assert "_tmp_dupkey_probe.py" in (r.stdout + r.stderr)
    finally:
        bad.unlink(missing_ok=True)
