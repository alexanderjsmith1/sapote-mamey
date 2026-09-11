"""v9.7.416 — no test may leave a synthetic `mamey.*` module behind in `sys.modules`.

THE BUG THIS LOCKS DOWN. `tests/test_409_package_path_privacy.py` registers stub modules under
REAL dotted names (`mamey`, `mamey.console`, `mamey.exact_identity`, `mamey.figure_theme`) so the
modules it loads by file path resolve their top-level imports without the full figure stack. Those
stubs were never removed, and the `mamey` stub set `__path__ = []`, so after that file ran, ANY
later `import mamey.<anything>` in the same interpreter failed. Measured on the sealed v9.7.415
tree:

    pytest <42 files touching sync_version/seal_sweep/ingest_blastp/...>   11 failed, 563 passed
    each of those files run on its own                                      all green

The failures were loud, which is the lucky case. The unlucky case is a later test that imports one
of the stubbed names, gets the stub, and passes while testing nothing — the stubbed
`exact_locus_display` returned `""` for every input.

The same stubbing broke the file in the OTHER direction too: `mamey.exact_identity` was stubbed
with two symbols while the real module grew three more that `mamey/layperson_guide.py` imports at
module top level, so `test_409_package_path_privacy.py` failed 4 of its own 7 tests when run
ALONE against the seal, and passed more of them in a polluted full run than in a clean one. A test
whose green depends on another test having polluted the interpreter first is not measuring what it
claims to.

Claim safety: process hygiene only. Nothing here reads biology or moves any score.
"""
from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"

# The file that planted the stubs, and a file that imports the real `mamey.exact_identity`.
_STUBBER = "tests/test_409_package_path_privacy.py"
_VICTIM = "tests/test_cut415_repair_regressions.py"


def _pytest(*rel_paths: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", *rel_paths, "-q", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(ROOT))


def test_the_stubbing_file_is_green_on_its_own():
    """It must not need another test to have imported the real package first."""
    out = _pytest(_STUBBER)
    assert out.returncode == 0, (
        f"{_STUBBER} does not pass in isolation:\n{out.stdout[-3000:]}{out.stderr[-2000:]}")


def test_stubs_do_not_leak_into_the_next_file():
    """The ordered pair that reproduced the leak must pass."""
    out = _pytest(_STUBBER, _VICTIM)
    assert out.returncode == 0, (
        f"running {_STUBBER} before {_VICTIM} poisons it:\n{out.stdout[-3000:]}{out.stderr[-2000:]}")


def test_real_exact_identity_is_importable_here():
    """In-process sentinel: by the time this file runs, `mamey.exact_identity` must be the real one.

    Cheap and order-dependent by nature (pytest walks tests/ alphabetically, so the 4-prefixed
    stubber runs first), which is exactly the ordering that broke. The two subprocess tests above
    are the deterministic proof; this one costs nothing and fails loudly in a full run.
    """
    import mamey.exact_identity as ei
    assert getattr(ei, "__file__", None), (
        "`mamey.exact_identity` resolved to a module with no file — a synthetic stub is still "
        "registered in sys.modules from an earlier test")
    for symbol in ("exact_locus_display", "exact_locus_from_mapping",
                   "exact_locus_from_native_manifest_bgc", "exact_locus_from_native_inventory_row"):
        assert hasattr(ei, symbol), f"`mamey.exact_identity` is missing {symbol}; stub in place?"


def _files_planting_mamey_stubs():
    """Test files that assign `sys.modules["mamey..."] = ...` anywhere."""
    out = []
    for p in sorted(TESTS.rglob("test_*.py")):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if (isinstance(target, ast.Subscript)
                        and isinstance(target.value, ast.Attribute)
                        and target.value.attr == "modules"
                        and isinstance(target.slice, ast.Constant)
                        and isinstance(target.slice.value, str)
                        and target.slice.value.split(".")[0] == "mamey"):
                    out.append(p)
                    break
            else:
                continue
            break
    return out


# Restoring constructs that count as containment. A string check on purpose: the point is that the
# file visibly takes responsibility for undoing what it planted, not which idiom it picks.
#
# `del sys.modules[...]` is deliberately NOT on this list. The sealed v9.7.415 file contained one --
# inside `_load`, to force a fresh exec BEFORE registering the module. That is a pre-load reset, not
# a restore, and accepting it made this gate pass against the exact tree it was written to catch.
_CONTAINMENT = ("sys.modules.pop", "monkeypatch.setitem", "monkeypatch.delitem",
                "_contain_stub_modules")


def test_every_mamey_stubber_restores_sys_modules():
    """Planting a stub under a real package name is allowed; leaving it there is not."""
    offenders = []
    for p in _files_planting_mamey_stubs():
        text = p.read_text(encoding="utf-8", errors="replace")
        if not any(marker in text for marker in _CONTAINMENT):
            offenders.append(p.relative_to(ROOT).as_posix())
    assert not offenders, (
        "test file(s) register a synthetic `mamey.*` module in sys.modules and never remove it:\n  "
        + "\n  ".join(offenders)
        + "\nEvery later test in the same interpreter then imports the stub instead of the real "
          "module — loudly if a symbol is missing, silently if it is not. Restore sys.modules in a "
          "fixture (see _contain_stub_modules in tests/test_409_package_path_privacy.py).")


def test_the_gate_sees_the_known_stubber():
    """Positive control: the detector must actually find the file this test was written for."""
    found = {p.relative_to(ROOT).as_posix() for p in _files_planting_mamey_stubs()}
    assert _STUBBER in found, f"detector no longer sees {_STUBBER}; it found {sorted(found)}"
