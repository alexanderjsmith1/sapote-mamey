import importlib.util
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "phylo_16s_panel", ROOT / "tools" / "phylo_16s_panel.py"
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def database():
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE record (
        acc_base TEXT PRIMARY KEY, source TEXT, definition TEXT, seq TEXT,
        designation TEXT, genus TEXT
    )""")
    con.execute("""CREATE TABLE query_identity_review (
        review_id TEXT PRIMARY KEY,
        match_accession TEXT,
        match_designation TEXT,
        match_genus TEXT,
        reviewed_action TEXT,
        reason_code TEXT
    )""")
    return con


def test_accession_and_designation_genus_rules_exclude_without_global_rename():
    con = database()
    rows = [
        ("PX566631", "as_governed", "Pseudonocardia sp. strain AS-522", "ACGT", "AS-522", "Pseudonocardia"),
        ("LOCAL_KRIB", "as_governed", "Kribbella sp. strain AS-522", "ACGT", "AS-522", "Kribbella"),
        ("PX589567", "as_governed", "Pseudonocardia sp. strain AS-22", "ACGT", "AS-22", "Pseudonocardia"),
    ]
    con.executemany("INSERT INTO record VALUES (?,?,?,?,?,?)", rows)
    con.executemany("INSERT INTO query_identity_review VALUES (?,?,?,?,?,?)", [
        ("QIR-PX566631", "PX566631", None, None, "exclude_query", "MISLABELED_STRAIN_ID"),
        ("QIR-AS522-PSEUDONOCARDIA", None, "AS-522", "Pseudonocardia", "exclude_query", "INVALID_GENUS_ASSOCIATION"),
    ])
    queries = [(r[0], r[2], r[3], r[4]) for r in rows]
    kept = MOD.apply_query_identity_review(con, queries)
    assert [r[0] for r in kept] == ["LOCAL_KRIB", "PX589567"]


def test_absent_review_table_preserves_existing_database_behavior():
    con = database()
    con.execute("DROP TABLE query_identity_review")
    query = ("PX1", "Pseudonocardia sp. strain AS-1", "ACGT", "AS-1")
    assert MOD.apply_query_identity_review(con, [query]) == [query]


def test_malformed_review_table_fails_closed():
    con = database()
    con.execute("DROP TABLE query_identity_review")
    con.execute("CREATE TABLE query_identity_review (review_id TEXT)")
    try:
        MOD.apply_query_identity_review(con, [])
    except ValueError as exc:
        assert str(exc) == "QUERY_IDENTITY_REVIEW_SCHEMA_INVALID"
    else:
        raise AssertionError("malformed review table was accepted")
