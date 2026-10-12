"""Portable lead-ledger CSV parity tests for the dependent V4 repair.

Only synthetic CSV files and the pure reader are used. This helper authored but
has not executed these tests; parent owns serial validation.
"""
from __future__ import annotations

import csv
import hashlib

import pytest

from mamey.interactive_figures.figure_set_renderer_tranche6 import _read_lead_ledger


def _legacy_rows(path):
    # Preserve the original file-stream contract exactly, including newline="".
    with path.open(newline="", encoding="utf-8-sig") as stream:
        lines = [line for line in stream if not line.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"])
def test_unicode_cell_separators_preserve_legacy_physical_csv_lines(tmp_path, separator, newline, bom):
    ledger = tmp_path / "leads.csv"
    note = f"left{separator}right"
    text = newline.join(["# source provenance", "strain,notes", f"TEST-STUDY,{note}", ""])
    raw = bom + text.encode("utf-8")
    ledger.write_bytes(raw)
    expected = [{"strain": "TEST-STUDY", "notes": note}]
    assert _legacy_rows(ledger) == expected
    path, rows, leads = _read_lead_ledger(
        ledger, ["TEST-STUDY"], expected_sha256=hashlib.sha256(raw).hexdigest(),
    )
    assert path == ledger.resolve()
    assert rows == expected
    assert leads == {"TEST-STUDY": ["STRAIN_LEVEL"]}
    assert ledger.read_bytes() == raw


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_quoted_multiline_cell_preserves_legacy_csv_newlines(tmp_path, newline):
    ledger = tmp_path / "leads.csv"
    note = "first" + newline + "second"
    raw = ("strain,notes" + newline + 'TEST-STUDY,"' + note + '"' + newline).encode("utf-8")
    ledger.write_bytes(raw)
    legacy = _legacy_rows(ledger)
    assert legacy == [{"strain": "TEST-STUDY", "notes": note}]
    _path, rows, leads = _read_lead_ledger(
        ledger, ["TEST-STUDY"], expected_sha256=hashlib.sha256(raw).hexdigest(),
    )
    assert rows == legacy
    assert leads == {"TEST-STUDY": ["STRAIN_LEVEL"]}
