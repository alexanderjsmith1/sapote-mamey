"""Widget regression — the BiG-SCAPE cohort widgets must not crash on MIBiG anchor rows.

deliverable_tools/_bigscape_data.strain_of() is called on EVERY gbk row by gbk_index(). A cohort DB
built with the standard `-m local2088` recipe carries MIBiG `BGCxxxxxxx.gbk` rows. strain_of had no
MIBiG branch; the .417 fail-closed rewrite made its terminal `raise ValueError("REFERENCE_STRAIN_UNBOUND")`
fire on every BGC row, so gbk_index() -- and the matrix + clinker widgets that call it -- crashed on any
MIBiG-anchored cohort DB (verified: gbk_index raised on curated_clean_2026-09-04, 2,087 BGC rows).

The fix classifies MIBiG by the same basename-BGC test the four BiG-SCAPE->Mamey tools use, and keeps
the fail-closed raise for genuinely-unbound NON-MIBiG references. Hermetic (tiny in-memory DB).

Run:  pytest tests/test_bigscape_widget_mibig_row_v9_7_417.py
"""
import importlib
import os
import sqlite3
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT, os.path.join(_ROOT, "deliverable_tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

D = importlib.import_module("_bigscape_data")


def test_mibig_bgc_row_classifies_not_crashes():
    label, cls = D.strain_of("/x/gbk_input/BGC0001234.gbk", "Streptomyces coelicolor")
    assert (label, cls) == ("MIBiG", "MIBiG")


def test_gbk_index_survives_a_mibig_row():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE gbk (id INTEGER, path TEXT, organism TEXT)")
    con.executemany("INSERT INTO gbk VALUES (?,?,?)", [
        (1, "/x/AS-001_NODE_1_length_10000_cov_20.region001.gbk", ""),
        (2, "/x/BGC0001234.gbk", "Streptomyces coelicolor"),           # MIBiG anchor
        (3, "/x/Streptomyces sp. WAC 06738_NZ_CP029618.1.region041.gbk", "Streptomyces sp. WAC 06738"),
    ])
    idx = D.gbk_index(con)   # pre-fix: raises ValueError on row 2
    assert idx[1] == ("AS-001", "AS")
    assert idx[2] == ("MIBiG", "MIBiG")
    assert idx[3] == ("Streptomyces sp. WAC 06738", "Type")


def test_amber417_collapse_fix_still_holds_on_this_base():
    # regression guard: the .417 anti-collapse behaviour must survive this MIBiG branch addition
    l1 = D.strain_of("/x/Streptomyces sp. WAC 01529_NZ_CP012345.1.region001.gbk",
                     "Streptomyces sp. WAC 01529")[0]
    l2 = D.strain_of("/x/Streptomyces sp. WAC 06738_NZ_CP029618.1.region041.gbk",
                     "Streptomyces sp. WAC 06738")[0]
    assert l1 == "Streptomyces sp. WAC 01529" and l2 == "Streptomyces sp. WAC 06738"
    assert l1 != l2
