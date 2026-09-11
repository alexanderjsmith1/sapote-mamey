"""Crash-safety regression for bgc_l0_program._write_rows (BLACK_CHERRY_377).

Proves the atomic-write property directly: a fault mid-write must leave the REAL
output path untouched (no truncated/partial table a later run could treat as
already-written), and must not leave a .tmp sibling behind. Fault is injected via a
rows iterable that raises partway through writerows() — a controlled OOM/SIGTERM stand-in.
"""
import csv
from pathlib import Path

import pytest

from mamey.bgc_l0_program import _write_rows

_FIELDS = ["bgc_id", "value"]
_GOOD = [{"bgc_id": "BGC001", "value": "alpha"}, {"bgc_id": "BGC002", "value": "beta"}]


class _ExplodingRows:
    """Yields the first row, then raises — writerows() gets partway, then dies."""

    def __iter__(self):
        yield {"bgc_id": "BGC001", "value": "alpha"}
        raise RuntimeError("simulated OOM/SIGTERM mid-write")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_write_rows_replaces_atomically(tmp_path):
    path = tmp_path / "table.tsv"
    _write_rows(path, _GOOD, _FIELDS)
    text = _read(path)
    assert text.splitlines()[0] == "bgc_id\tvalue"
    assert "BGC001\talpha" in text and "BGC002\tbeta" in text
    assert not (tmp_path / "table.tsv.tmp").exists()


def test_crash_mid_write_leaves_prior_file_intact(tmp_path):
    path = tmp_path / "table.tsv"
    # A prior good table exists on disk (the file a resumed run must not see corrupted).
    _write_rows(path, _GOOD, _FIELDS)
    prior = _read(path)

    with pytest.raises(RuntimeError, match="simulated OOM/SIGTERM"):
        _write_rows(path, _ExplodingRows(), _FIELDS)

    # The real path is byte-identical to the prior good table — the failed write went to
    # a .tmp sibling that os.replace never promoted.
    assert _read(path) == prior
    # No partial content leaked to the real path.
    assert "beta" in _read(path)  # still the prior two-row table, not a truncated one-row write


def test_crash_mid_write_cleans_up_tmp_sibling(tmp_path):
    path = tmp_path / "table.tsv"
    with pytest.raises(RuntimeError):
        _write_rows(path, _ExplodingRows(), _FIELDS)
    # No orphaned .tmp file, and no real file created from a never-completed first write.
    assert not (tmp_path / "table.tsv.tmp").exists()
    assert not path.exists()
