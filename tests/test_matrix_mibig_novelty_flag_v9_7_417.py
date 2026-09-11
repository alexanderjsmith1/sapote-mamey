"""Widget regression (co-required) — the matrix AS-private novelty flag must count MIBiG presence.

`MIBiG row handling` gives MIBiG anchor BGCs their own class `"MIBiG"` (previously
they crashed / were mislabelled `"Type"`). The matrix novelty flag in `bigscape_matrix_widget.build_payload`
was `private = as_n>0 and sid_n==0 and type_n==0` — it does not count MIBiG. So once MIBiG is its own class,
an AS+MIBiG family (which clustered with a characterized MIBiG reference → KNOWN) is falsely flagged
AS-private (a spurious novelty lead). This test pins that a MIBiG-bearing family is NOT AS-private.

Hermetic: monkeypatch `family_members`, use an in-memory `run` table.
Run:  pytest tests/test_matrix_mibig_novelty_flag_v9_7_417.py
"""
import importlib
import os
import sqlite3
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT, os.path.join(_ROOT, "deliverable_tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

M = importlib.import_module("bigscape_matrix_widget")


def _con():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE run (label TEXT)")
    con.execute("INSERT INTO run VALUES ('test_run')")
    return con


def _member(cls, strain, product="NRPS"):
    return {"cls": cls, "strain": strain, "product": product, "gbk_id": 0, "record_id": 0}


def _payload(fam):
    con = _con()
    M.family_members = lambda con, cutoff=0.3: fam   # monkeypatch the imported symbol
    return M.build_payload(con)


def _fam_by_id(payload, fid):
    return next(f for f in payload["families"] if f["id"] == fid)


def test_as_plus_mibig_family_is_not_private():
    fam = {1: [_member("AS", "AS-001"), _member("MIBiG", "MIBiG")]}
    f = _fam_by_id(_payload(fam), 1)
    assert f["private"] is False, "AS+MIBiG family clustered with a reference is KNOWN, not AS-private"
    assert f.get("mibig_n") == 1


def test_as_only_family_is_private():
    fam = {2: [_member("AS", "AS-001"), _member("AS", "AS-002")]}
    assert _fam_by_id(_payload(fam), 2)["private"] is True


def test_as_plus_type_family_is_not_private():
    # regression guard: the existing Type disqualifier must still hold
    fam = {3: [_member("AS", "AS-001"), _member("Type", "Streptomyces sp. WAC 06738")]}
    assert _fam_by_id(_payload(fam), 3)["private"] is False
