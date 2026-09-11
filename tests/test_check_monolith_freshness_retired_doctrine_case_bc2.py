"""BC2-CMF-01 (v9.7.396): tools/check_monolith_freshness.py's RETIRED-doctrine scan matched via
bare re.finditer(pat, text) with no re.I, while the file's own _DENY negation-guard regex (used to
decide whether a match is an assertion or a denial) already had re.I. A monolith casually referencing
a retired flag/phrase in a different case (e.g. "as_scrub is still checked" instead of "AS_SCRUB")
positively asserted retired doctrine with zero signal -- a silent PASS on a genuinely stale-doctrine
monolith, the exact "anchor drifting silently... with no signal" class this tool exists to catch.

Reproduced directly against pristine v9.7.395: a monolith positively asserting (lowercase, no
negation word anywhere nearby) "as_scrub is still checked before every cut" returned a clean PASS
(exit 0). Fixed by adding re.I to the RETIRED pattern re.finditer call.

Also covers the negation guard is unaffected: it only ever looked backward from the match (the
module's own comment: "Look only at the local window before the match"), by design, in both
versions -- this test pins a lowercase denial phrased with the negation word BEFORE the retired
term ("no as_scrub check"), which the guard correctly recognizes as clean in both cases, so the
case-insensitivity fix does not regress the pre-existing denial-detection behavior.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import check_monolith_freshness as cmf  # noqa: E402


def _run(tmp_path, monolith_body: str) -> int:
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pyproject.toml").write_text('[tool.sapote]\nbundle_version = "9.7.395"\n', encoding="utf-8")
    (tmp_path / "docs" / "SAPOTE_MAMEY_BUNDLE_MONOLITH.md").write_text(monolith_body, encoding="utf-8")
    orig_root, orig_monolith = cmf.ROOT, cmf.MONOLITH
    cmf.ROOT = tmp_path
    cmf.MONOLITH = tmp_path / "docs" / "SAPOTE_MAMEY_BUNDLE_MONOLITH.md"
    try:
        return cmf.main(["--quiet"])
    finally:
        cmf.ROOT, cmf.MONOLITH = orig_root, orig_monolith


def test_lowercase_retired_doctrine_assertion_is_caught(tmp_path):
    body = (
        "vetted against bundle v9.7.395\n\n"
        "As a reminder, as_scrub is still checked before every cut, to keep the AS cohort private.\n"
    )
    assert _run(tmp_path, body) == 1


def test_uppercase_retired_doctrine_assertion_still_caught(tmp_path):
    body = (
        "vetted against bundle v9.7.395\n\n"
        "As a reminder, AS_SCRUB is still checked before every cut, to keep the AS cohort private.\n"
    )
    assert _run(tmp_path, body) == 1


def test_lowercase_denial_before_term_stays_clean(tmp_path):
    body = (
        "vetted against bundle v9.7.395\n\n"
        "As a reminder, there is no as_scrub check before a cut anymore -- the AS cohort is public "
        "per the v9.7.236 PI decision.\n"
    )
    assert _run(tmp_path, body) == 0


def test_uppercase_denial_before_term_stays_clean(tmp_path):
    body = (
        "vetted against bundle v9.7.395\n\n"
        "As a reminder, there is no AS_SCRUB check before a cut anymore -- the AS cohort is public "
        "per the v9.7.236 PI decision.\n"
    )
    assert _run(tmp_path, body) == 0


def test_clean_monolith_with_no_retired_terms_passes(tmp_path):
    body = "vetted against bundle v9.7.395\n\nNothing retired-doctrine-shaped here at all.\n"
    assert _run(tmp_path, body) == 0
