"""v9.7.250 — `gen_release_manifest` must refuse a failing pytest log.

CUT_PROTOCOL step 7 says to pass `--pytest-log <a fresh full-suite run's captured output>` because
"it parses the real summary line instead of you re-typing two numbers by hand." It does. It also
parsed, without complaint, a log whose summary line read

    5 failed, 2906 passed, 152 skipped

and reported `tests 2906p/152s`. Caught during this cut, on my own first (red) run — the protocol's
step 4 log was fed to step 7 before step 6's generators had been re-run.

A release manifest that records the pass count of a failing suite is worse than one that records
nothing, because it looks like evidence. `counts_from_log` now raises `SystemExit` on any nonzero
`failed`/`error` count.

Separately pinned and NOT fixed here: the three `RELEASE_MANIFEST.md` sync rules ("tests passed row",
"Gate 5 test count", "tests skipped row") match **zero** lines on the current manifest, which no longer
carries test counts at all. The tool prints a WARNING and exits 0. That is a writer with no target --
the mirror of the "defined and never invoked" class this project keeps finding. Flagged for the Developer or User.
"""
from __future__ import annotations
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from gen_release_manifest import counts_from_log  # noqa: E402

GREEN = "2911 passed, 152 skipped, 2 warnings in 241.41s (0:04:01)\n"


def _log(tmp_path, text):
    p = tmp_path / "pytest.log"
    p.write_text(text, encoding="utf-8")
    return p


def test_green_log_yields_counts(tmp_path):
    assert counts_from_log(_log(tmp_path, GREEN)) == (2911, 152)


@pytest.mark.parametrize("summary", [
    "5 failed, 2906 passed, 152 skipped, 2 warnings in 267.29s",
    "1 failed, 10 passed in 1.0s",
    "3 errors, 100 passed in 2.0s",
    "1 error, 5 passed in 0.5s",
])
def test_red_log_is_refused(tmp_path, summary):
    with pytest.raises(SystemExit) as exc:
        counts_from_log(_log(tmp_path, summary))
    assert "refusing" in str(exc.value).lower()


def test_zero_failed_is_not_red(tmp_path):
    """`0 failed` is green. The guard keys on a nonzero count, not the word."""
    assert counts_from_log(_log(tmp_path, "0 failed, 12 passed, 1 skipped in 1s")) == (12, 1)
