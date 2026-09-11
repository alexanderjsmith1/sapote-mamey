"""v9.7.421 — a 16S reference panel must contain 16S genes.

Measured on sealed v9.7.420 against 16S Database/rrna16s.sqlite, over the 31,302 non-type records that
carry a sequence: 19 exceed 2,000 nt — including CP054932.1 at 9,430,849 nt, "Actinomadura sp. NAK00032
chromosome, complete genome" — and 5,188 (16.6%) fall below 1,200 nt. `rank_references()` filtered on
`seq IS NOT NULL AND uncultured = 0` only, so a complete bacterial genome was admissible as a reference.
Type strains never exposed this because RefSeq 16S records are uniform in length.

Real-store tests read the workspace 16S sqlite from the SAPOTE_16S_STORE environment variable and skip
when it is unset or the file is absent (SEXTANT_426: no workspace path is hardcoded).
"""
import importlib.util, os, re
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "tools", "phylo_16s_panel.py")
SRC = open(PANEL, encoding="utf-8").read()

STORE = os.environ.get("SAPOTE_16S_STORE", "")


def test_the_candidate_query_bounds_reference_length():
    i = SRC.index("SELECT acc_base, definition, seq, binomial, source FROM record")
    stmt = SRC[i:i + 500]
    assert "LENGTH(seq) BETWEEN" in stmt, "reference candidates are not length-bounded"


def test_bounds_are_named_constants_and_overridable():
    assert "REFERENCE_LEN_MIN" in SRC and "REFERENCE_LEN_MAX" in SRC
    assert "PHYLO16S_REF_LEN_MIN" in SRC, "a marker with another natural length must be configurable"


def test_the_bounds_are_sane_for_16S():
    ns = {"os": os}
    for line in SRC.splitlines():
        if line.startswith("REFERENCE_LEN_M"):
            exec(line, ns)
    assert ns["REFERENCE_LEN_MIN"] >= 1000, ns["REFERENCE_LEN_MIN"]
    assert 1500 <= ns["REFERENCE_LEN_MAX"] <= 2000, ns["REFERENCE_LEN_MAX"]


def test_the_existing_guards_are_not_weakened():
    """Negative control: adding a length bound must not drop the uncultured refusals."""
    i = SRC.index("SELECT acc_base, definition, seq, binomial, source FROM record")
    stmt = SRC[i:i + 500]
    assert "uncultured = 0" in stmt
    assert "UNCULTURED_BY_DEFINITION" in stmt
    assert "seq IS NOT NULL" in stmt


@pytest.mark.skipif(not os.path.exists(STORE), reason="workspace store not present (set SAPOTE_16S_STORE)")
def test_against_the_real_store_a_complete_genome_is_now_excluded():
    import sqlite3
    ns = {"os": os}
    for line in SRC.splitlines():
        if line.startswith("REFERENCE_LEN_M"):
            exec(line, ns)
    lo, hi = ns["REFERENCE_LEN_MIN"], ns["REFERENCE_LEN_MAX"]
    con = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    NT = "source IN ('pdf_candidate','attribute_candidate','nontype_fetch')"
    over = con.execute(f"SELECT COUNT(*) FROM record WHERE {NT} AND seq IS NOT NULL AND seq_len>2000").fetchone()[0]
    assert over > 0, "the store no longer contains the oversized records this guard exists for"
    admitted = con.execute(
        f"SELECT COUNT(*) FROM record WHERE {NT} AND seq IS NOT NULL AND seq_len BETWEEN ? AND ? AND seq_len>2000",
        (lo, hi)).fetchone()[0]
    assert admitted == 0, "an oversized record is still admissible as a 16S reference"
