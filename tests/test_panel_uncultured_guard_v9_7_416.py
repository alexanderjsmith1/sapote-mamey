"""A clone record must not be admitted as a panel REFERENCE, even when its flag was never computed.

`panel_from_16s_db.py` documents that uncultured and clone records are excluded, and enforced it
with `uncultured = 0` alone. That flag is written only by the harvest paths that compute it.
Measured against `16S Database/rrna16s.sqlite` on 2026-09-08:

    sequence-bearing `attribute_candidate` records          3,097
      of those with uncultured = 1                              0
      of those whose DEFINITION says uncultured or clone     1,451
    same leak from `pdf_candidate`                             701
    total clone records reachable as references              2,152

So the guard read as though it excluded clones while admitting 2,152 of them. They reached figures
as tips named `unnamed (KC607742)` — a clone number is not a strain: no designation, no culture
collection, nothing a caption can name. The predicate now also reads the RECORD'S OWN DEFINITION,
which is deposited text and always present, so the guard holds for a source whose flag is absent.

It is deliberately not a substring sweep for "clone". Three *Nocardia rhizosphaerae* records read
"isolate Clone1 ... type strain DSM102210T" — a named type strain, exactly the sort of reference a
panel wants. Applying the shipped predicate to the live database excludes 2,147 records and admits
6 that merely contain the word, all of them named. Over-refusing a reference is not free either.

Hermetic: builds its own three-row database in tmp_path. No network, no workspace database.

CARRIED FORWARD from EGGPLANT_415_16s_reference_layer, re-pointed at the bundled tool. It is a
REGRESSION GUARD here: the predicate it checks was landed in the loose source on 2026-09-08, so
this file passes on the unpatched tree too, and is reported separately for that reason.
"""
import re
import sqlite3
from pathlib import Path

import pytest

# Bundle-relative (v9.7.415): the tool now ships as tools/phylo_16s_panel.py, so this guard
# no longer names an operator's home directory and runs wherever the bundle is installed.
TOOL = Path(__file__).resolve().parents[1] / "tools" / "phylo_16s_panel.py"

ROWS = [
    # acc,        definition,                                                  uncultured, admit?
    ("KC607742", "Uncultured Streptomyces sp. clone Ptr15c 16S ribosomal RNA gene, partial", 0, False),
    ("KC607733", "Uncultured Amycolatopsis sp. clone R1Ant 16S ribosomal RNA gene", 0, False),
    ("AB000001", "Unidentified bacterium 16S ribosomal RNA gene, partial sequence", 0, False),
    ("NR_151944", "Micromonospora ureilytica strain CR18 16S ribosomal RNA, partial sequence", 0, True),
    ("LT629775", "Nocardia rhizosphaerae partial 16S rRNA gene, isolate Clone1, type strain "
                 "DSM102210T", 0, True),
]


def _predicate():
    if not TOOL.exists():                       # pragma: no cover - environment guard
        pytest.skip(f"tool not present at {TOOL}")
    src = TOOL.read_text()
    m = re.search(r"UNCULTURED_BY_DEFINITION = \(\n(.*?)\n\)", src, re.S)
    if not m:
        pytest.fail("panel_from_16s_db.py exposes no UNCULTURED_BY_DEFINITION predicate; the guard "
                    "is still `uncultured = 0` alone, which admits every clone record whose source "
                    "never computed the flag.")
    return eval("(" + m.group(1) + ")")         # noqa: S307 - a SQL fragment from our own source


@pytest.fixture()
def db(tmp_path):
    con = sqlite3.connect(tmp_path / "t.sqlite")
    con.execute("CREATE TABLE record (acc_base TEXT, definition TEXT, uncultured INT, seq TEXT)")
    con.executemany("INSERT INTO record VALUES (?,?,?,'ACGT')",
                    [(a, d, u) for a, d, u, _ in ROWS])
    con.commit()
    return con


def test_clone_records_are_refused_even_with_the_flag_unset(db):
    admitted = {r[0] for r in db.execute(
        f"SELECT acc_base FROM record WHERE seq IS NOT NULL AND uncultured = 0 "
        f"AND {_predicate()}")}
    for acc, definition, _, should_admit in ROWS:
        if should_admit:
            assert acc in admitted, (
                f"{acc} ({definition[:48]}...) is a NAMED record and must remain usable as a "
                f"reference; over-refusing costs the panel a comparator a caption can name.")
        else:
            assert acc not in admitted, (
                f"{acc} ({definition[:48]}...) is a clone record and reached a figure as an "
                f"unnamed tip. A clone number is not a strain.")


def test_the_guard_is_wired_into_the_reference_query():
    src = TOOL.read_text()
    m = re.search(r"def rank_references\(.*?\n(.*?)\n    params = list\(sources\)", src, re.S)
    assert m and "UNCULTURED_BY_DEFINITION" in m.group(1), (
        "the predicate exists but rank_references() does not use it — the pool must be bounded in "
        "SQL before blastn runs, not filtered afterwards, or 2,152 unusable sequences are aligned.")
