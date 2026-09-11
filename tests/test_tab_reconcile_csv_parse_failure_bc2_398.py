"""v9.7.398 — `mamey/tab_reconcile.py::_read_csv_rows()` caught every exception and returned an
empty list, indistinguishable for a genuinely-absent file, a legitimately-empty-but-valid CSV,
and a file that EXISTS but fails to parse (corrupt bytes, a decode error). The last case is a
real data-loss event for this module's Mode-B evidence-ledger role (crosswalk/triage-board
inputs), not "no data" — matching this codebase's own established "silent-failure family" fix
pattern (see mamey/exclusions.py's identical warn-on-corrupt-but-present convention).
"""
from __future__ import annotations

import warnings
from pathlib import Path

from mamey.tab_reconcile import _read_csv_rows


def test_missing_file_returns_empty_silently_no_warning(tmp_path):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rows = _read_csv_rows(tmp_path / "does_not_exist.csv")
    assert rows == []
    assert not caught, "a genuinely absent file must not warn"


def test_legitimately_empty_valid_csv_returns_empty_silently(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("header1,header2\n", encoding="utf-8")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rows = _read_csv_rows(p)
    assert rows == []
    assert not caught, "a valid CSV with zero data rows must not warn"


def test_corrupt_present_file_warns_and_is_distinguishable_from_absence():
    """The defect, reproduced directly: a file that exists but fails to decode must not look
    identical to a missing file."""
    import tempfile
    tmpdir = Path(tempfile.mkdtemp())
    corrupt = tmpdir / "corrupt.csv"
    corrupt.write_bytes(b"header1,header2\n\xff\xfe invalid utf8 bytes here,val2\n")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rows = _read_csv_rows(corrupt)
    assert rows == []  # still degrades to empty for this reconciliation pass...
    assert any(
        "could not read" in str(w.message) and "corrupt.csv" in str(w.message) for w in caught
    ), "a present-but-unparseable file must warn, distinguishing it from a genuinely absent one"
