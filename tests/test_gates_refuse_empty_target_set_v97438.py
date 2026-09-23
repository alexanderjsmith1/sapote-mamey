"""A gate must not report a clean result when it examined nothing.

Before v9.7.438 both of these tools produced **byte-identical output and exit code** for a run over
the real bundle and a run over an empty directory:

    $ python3 tools/check_no_brace_paths.py .            -> "brace-path check OK ..."   exit 0
    $ python3 tools/check_no_brace_paths.py /tmp/empty   -> "brace-path check OK ..."   exit 0

    $ python3 tools/audit_chatgpt_nextpaths_drift.py .            -> "... PASS"   exit 0
    $ python3 tools/audit_chatgpt_nextpaths_drift.py /tmp/empty   -> "... PASS"   exit 0

Neither a reader nor CI could tell the two apart. The verdict was a function of the FINDINGS
collection only (`return 1 if hits else 0`), with nothing asserting that the TARGET set was
non-empty — so zero files checked reported the same as zero problems found.

This is not hypothetical for this project: a workspace-root document sat four cuts stale while its
own `--check` passed every cut, because the check was looking somewhere else and had no way to say
so. `check_no_brace_paths.py` already refused to call an unreadable directory "confirmed
brace-free"; these tests extend that same reasoning to an empty target set.

Both tools now also print the denominator on success. "OK" is a claim; "OK, 4,566 paths scanned" is
a receipt.
"""
import subprocess
import sys
from pathlib import Path

import pytest

BUNDLE = Path(__file__).resolve().parents[1]
TOOLS = BUNDLE / "tools"


def run(tool, target):
    r = subprocess.run([sys.executable, str(TOOLS / tool), str(target)],
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


@pytest.mark.parametrize("tool", [
    "check_no_brace_paths.py",
    "audit_chatgpt_nextpaths_drift.py",
])
def test_gate_refuses_an_empty_target_set(tmp_path, tool):
    """The core of the defect: nothing to check must not read as nothing wrong."""
    rc, out = run(tool, tmp_path)
    assert rc == 2, f"{tool} returned {rc} on an empty tree; a refusal is exit 2, not a pass"
    assert "REFUS" in out.upper(), f"{tool} did not say it refused: {out[:200]}"


@pytest.mark.parametrize("tool", [
    "check_no_brace_paths.py",
    "audit_chatgpt_nextpaths_drift.py",
])
def test_gate_still_passes_on_the_real_bundle(tool):
    """The refusal must not be so eager that the gate stops working on a real tree."""
    rc, out = run(tool, BUNDLE)
    assert rc == 0, f"{tool} returned {rc} on the real bundle: {out[:300]}"
    assert "REFUS" not in out.upper()


@pytest.mark.parametrize("tool", [
    "check_no_brace_paths.py",
    "audit_chatgpt_nextpaths_drift.py",
])
def test_a_real_run_and_an_empty_run_are_distinguishable(tmp_path, tool):
    """The property that was actually missing. Stated directly so it cannot regress quietly."""
    rc_real, out_real = run(tool, BUNDLE)
    rc_empty, out_empty = run(tool, tmp_path)
    assert (rc_real, out_real) != (rc_empty, out_empty), (
        f"{tool} produces the same exit code AND the same text whether or not it examined "
        f"anything — which is the whole defect")


@pytest.mark.parametrize("tool,needle", [
    ("check_no_brace_paths.py", "scanned"),
    ("audit_chatgpt_nextpaths_drift.py", "checked"),
])
def test_success_reports_how_much_was_examined(tool, needle):
    """A verdict without a denominator cannot be audited. Require the count on the success path."""
    rc, out = run(tool, BUNDLE)
    assert rc == 0
    assert needle in out.lower(), f"{tool} passed without saying how much it looked at: {out[:200]}"
    assert any(ch.isdigit() for ch in out), "no count in the success line"
