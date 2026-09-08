"""PC-8 (v9.7.253 Bunny Hop session 2): keep the cell-status vocabulary single-sourced.

The status codes live in two places — `mamey/cell_provenance.STATUS_GLOSSARY` (the code) and
`docs/troubleshooting/CELL_STATUS_CODE_GLOSSARY.md` (the reader-facing doc). They are maintained
by hand and can drift. This test asserts the doc's status-code table documents EXACTLY the codes
the code defines, so adding/removing a code in one place fails until the other is updated.
"""
import re
from pathlib import Path

from mamey.cell_provenance import STATUS_CODES

_DOC = Path(__file__).resolve().parent.parent / "docs" / "troubleshooting" / "CELL_STATUS_CODE_GLOSSARY.md"


def _codes_from_doc() -> set[str]:
    codes: set[str] = set()
    for line in _DOC.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        # a status-code row: first cell is a single ALL_CAPS_TOKEN (skip the header + separator rows)
        if re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", first):
            codes.add(first)
    return codes


def test_doc_exists():
    assert _DOC.exists(), f"cell-status glossary doc missing at {_DOC}"


def test_doc_documents_exactly_the_code_status_set():
    documented = _codes_from_doc()
    assert documented == STATUS_CODES, (
        f"cell-status glossary drift:\n"
        f"  in doc but not code: {sorted(documented - STATUS_CODES)}\n"
        f"  in code but not doc: {sorted(STATUS_CODES - documented)}"
    )
