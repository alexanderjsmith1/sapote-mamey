"""Regression: `mamey doctor`'s governed-denominator check must always report something
(OK or WARN), never be silently swallowed.

On a genuinely code-only tree (no OFFICIAL_DATA reachable anywhere -- the exact scenario the
existing WARN branch exists to report), `mamey.exclusions.governed_denominator()` returns `{}`.
`doctor_command()`'s governed-denominator block then built an f-string via bare `_den['strains']`
/ `_den['regions']` -- a KeyError on that empty dict -- caught by the block's own
`except Exception: pass`, so the intended "uses in-module _DEFAULT" warning could never actually
print. The doctor probe just silently skipped this check instead of reporting the exact
diagnostic a new user on a portable install most needs to see.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey import cli  # noqa: E402


def test_governed_denominator_check_reports_something_with_no_official_data(monkeypatch):
    monkeypatch.delenv("MAMEY_OFFICIAL_DATA", raising=False)
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.doctor_command(argparse.Namespace())
    out = buf.getvalue()
    assert rc == 0, "doctor_command should never crash the whole probe"
    assert "Governed denominator" in out, (
        "the governed-denominator check produced no output at all -- it was silently "
        "swallowed rather than reporting OK or WARN"
    )
    assert "strains" in out and "regions" in out
