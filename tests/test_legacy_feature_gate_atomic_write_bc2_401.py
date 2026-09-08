"""Regression test for `mamey/legacy_feature_gate.py::write_default_legacy_matrix()`
(v9.7.401, BC2, `.401` round tick 11).

`write_default_legacy_matrix()` wrote directly to its destination path. Reproduced live: an
interrupted write (crash, disk full, kill -9) leaves the real destination file itself -- not a
`.tmp` sibling -- truncated (2 of 24 rows), sitting on disk where a caller expects the committed
matrix. This is the same crash-safety gap this codebase already fixed once, for the identical
reason, in this module's own sibling writes three lines below (`findings_csv`/`report`/`receipt`
in `write_legacy_gate_outputs()`) and in `mamey/output_checklist.py`'s v9.7.371 fix ("an
interrupted write here would seal a truncated file as if it were valid -- the checksum step
never sees the half-written state to catch it").

Not a silent-false-PASS bug like this round's rglob-family finds -- `validate_legacy_rows()`
correctly fails loudly on a truncated matrix's missing P0 rows -- but `matrix_path.exists()`
being True on the truncated file means a subsequent run won't regenerate it without an explicit
`create_default=True`, leaving release QA stuck failing against what looks like a hand-tampered
matrix rather than a crash artifact.
"""
from __future__ import annotations

import csv

import pytest

from mamey.legacy_feature_gate import (
    DEFAULT_FEATURES,
    read_legacy_matrix,
    write_default_legacy_matrix,
)


def test_clean_write_still_produces_a_full_matrix(tmp_path):
    target = tmp_path / "LEGACY_FEATURE_MATRIX.csv"
    write_default_legacy_matrix(target)
    rows = read_legacy_matrix(target)
    assert len(rows) == len(DEFAULT_FEATURES)
    assert target.with_name(target.name + ".tmp").exists() is False


def _interrupt_after_two_rows(monkeypatch):
    """Simulate a crash mid-write: the underlying csv writer commits a header plus the first
    two rows to whatever file handle it was given, then raises."""
    orig_writerows = csv.DictWriter.writerows

    def flaky_writerows(self, rows):
        self.writerow(rows[0])
        self.writerow(rows[1])
        raise OSError("simulated interruption mid-write")

    monkeypatch.setattr(csv.DictWriter, "writerows", flaky_writerows)
    return orig_writerows


def test_interrupted_write_does_not_corrupt_the_destination_file(tmp_path, monkeypatch):
    """The actual regression this fix closes: after a write interrupted partway through, the
    real destination path must NOT exist in a truncated state -- either it never appears (this
    fix, atomic replace) or it must still contain the FULL matrix (never both absent-a-tmp and
    partial-at-destination)."""
    target = tmp_path / "LEGACY_FEATURE_MATRIX.csv"
    _interrupt_after_two_rows(monkeypatch)
    with pytest.raises(OSError, match="simulated interruption"):
        write_default_legacy_matrix(target)

    assert not target.exists(), (
        "destination file must not exist in a truncated state after an interrupted write -- "
        "found it partially written, which a later run's matrix_path.exists() check would "
        "treat as an already-present (but silently corrupt) matrix"
    )
    tmp_sibling = target.with_name(target.name + ".tmp")
    assert tmp_sibling.exists(), "the partial write should land in the isolated .tmp sibling"


def test_interrupted_write_leaves_no_matrix_for_exists_check_to_trust(tmp_path, monkeypatch):
    """A second, uninterrupted call after a simulated crash must produce a genuinely complete
    matrix -- confirms the fix doesn't leave the destination in a state that a caller's
    `not matrix_path.exists()` guard would skip regenerating."""
    target = tmp_path / "LEGACY_FEATURE_MATRIX.csv"
    _interrupt_after_two_rows(monkeypatch)
    with pytest.raises(OSError):
        write_default_legacy_matrix(target)
    monkeypatch.undo()

    assert not target.exists()
    write_default_legacy_matrix(target)
    rows = read_legacy_matrix(target)
    assert len(rows) == len(DEFAULT_FEATURES)
