"""BC2-VTD-01 (v9.7.396): verify_tier_derivation.py's _is_stripped() must not wrongly exclude a
root-level file from the redaction-parity comparison just because its name happens to start with
the substring "runs".

The dynamic-run-dir check was `first.startswith("runs")` — a bare prefix match with no word
boundary, so ANY root-level file or directory merely starting with those four letters (e.g.
"runsafe_check.py", "runsanalysis_helper.md" — ordinary, plausible names for a future root-level
script or doc) was wrongly classified as "stripped by design" and silently excluded from the whole
redaction-parity comparison loop. This is the same "silently narrows what actually gets checked"
bug shape this file's own v9.7.374 fix already closed for files missing from the public tier
entirely — this checker's whole purpose is asserting the public tier IS an exact redaction-view of
the private source, so a wrongly-excluded file is just as much a coverage hole as a silently-
omitted one.

Reproduced live against the unpatched tools/verify_tier_derivation.py before this fix.
"""
from __future__ import annotations
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from verify_tier_derivation import _is_stripped  # noqa: E402


def test_unrelated_root_file_merely_starting_with_runs_is_not_stripped():
    assert not _is_stripped("runsafe_check.py"), (
        "a root-level file that merely starts with the substring 'runs' but is not a dynamic "
        "run-output directory must NOT be silently excluded from the parity check"
    )
    assert not _is_stripped("runsanalysis_helper.md")


def test_genuine_dynamic_run_directories_still_stripped():
    # Regression guard: the actual purpose of this check (dynamically-named runs*/ output dirs)
    # must remain unaffected.
    assert _is_stripped("runs/example/package.json")
    assert _is_stripped("runs-old/example/package.json")
    assert _is_stripped("runs_2026/example/package.json")
    assert _is_stripped("runs")  # bare "runs" itself


def test_end_to_end_drift_is_caught_for_a_falsely_excluded_file(tmp_path):
    # Build a full mini private/public tree pair and confirm main()'s comparison loop actually
    # catches a real drift in a file that used to be silently skipped.
    import subprocess

    priv = tmp_path / "private"
    pub = tmp_path / "public"
    priv.mkdir()
    pub.mkdir()
    (priv / "runsafe_check.py").write_text("# private-only marker: AS-999\nprint('hello')\n")
    (pub / "runsafe_check.py").write_text("# public copy, NOT redacted -- a real drift\n"
                                          "print('hello')\n")

    tool = pathlib.Path(__file__).resolve().parents[1] / "tools" / "verify_tier_derivation.py"
    result = subprocess.run(
        [sys.executable, str(tool), str(priv), str(pub), "--ext", ".py"],
        capture_output=True, text=True,
    )
    assert result.returncode == 1, (
        f"a real content drift in a wrongly-excluded 'runs*'-prefixed root file must be caught; "
        f"stdout={result.stdout!r}"
    )
    assert "runsafe_check.py" in result.stdout
