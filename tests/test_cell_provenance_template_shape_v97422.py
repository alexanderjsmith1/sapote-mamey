"""SEXTANT_422o — the shipped Cell_Provenance template must satisfy the schema
the engine enforces on real runs.

In v9.7.421 the HMM-marker row carried an unquoted comma inside notes_for_llm
("This is domain/marker evidence, not BLASTP homolog evidence."), so csv parsed
it as 15 fields under a 14-column header: a surplus None-keyed field and a
truncated notes_for_llm.  mamey/cell_provenance.py defines HEADERS (14) and
validates status_code against STATUS_CODES on every real run — so the shipped
example of the schema violated the schema.

It survived because the only test touching this file asserted that it exists.
A test that cannot fail on a corrupt file is not a guard.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "Cell_Provenance_Template.csv"


def _rows():
    with TEMPLATE.open(encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


def test_template_present():
    assert TEMPLATE.is_file(), TEMPLATE


def test_every_row_has_exactly_the_header_width():
    rows = _rows()
    width = len(rows[0])
    bad = [(i, len(r)) for i, r in enumerate(rows[1:], start=2) if len(r) != width]
    assert not bad, f"header is {width} fields; offending rows (1-indexed, width): {bad}"


def test_header_matches_the_engine_contract():
    sys.path.insert(0, str(ROOT))
    from mamey.cell_provenance import HEADERS
    assert _rows()[0] == list(HEADERS)


def test_no_dictreader_surplus_field():
    with TEMPLATE.open(encoding="utf-8", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            assert None not in row, f"row {i} produced a surplus unnamed field: {row.get(None)!r}"


def test_notes_column_survives_intact():
    """The row that motivated this patch keeps its full sentence."""
    with TEMPLATE.open(encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["status_code"] == "NEEDS_HMMER_DOMTBLOUT"]
    assert rows, "expected the HMMER marker row in the template"
    assert rows[0]["notes_for_llm"].endswith("not BLASTP homolog evidence.")
