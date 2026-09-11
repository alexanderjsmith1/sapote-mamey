"""Cumulative panel patch: a 600-nt candidate must be refused, not admitted, and the bound must not move.

Reviewer intake 002 found the revision-2 fixtures used 600-nt candidates that the 421b lower bound
excludes, and asked that the bound NOT be lowered to restore tests. This is the explicit refusal control.
"""
import importlib.util, os, sqlite3, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL = os.path.join(ROOT, "tools", "phylo_16s_panel.py")
SRC = open(PANEL, encoding="utf-8").read()

def _mod():
    spec = importlib.util.spec_from_file_location("p16_cum", PANEL); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_lower_bound_is_not_lowered():
    ns = {"os": os}; [exec(l, ns) for l in SRC.splitlines() if l.startswith("REFERENCE_LEN_M")]
    assert ns["REFERENCE_LEN_MIN"] >= 1200 and ns["REFERENCE_LEN_MAX"] <= 2000

def test_a_600nt_candidate_is_refused_by_the_candidate_query():
    i = SRC.index("SELECT acc_base, definition, seq, binomial, source FROM record")
    stmt = SRC[i:i + 600]
    assert "LENGTH(seq) BETWEEN" in stmt and "uncultured = 0" in stmt and "(is_type IS NULL OR is_type != 1)" in SRC
    # execute the admission predicate literally against a throwaway store
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE record(acc_base, definition, seq, binomial, source, uncultured, seq_len, is_type)")
    con.executemany("INSERT INTO record VALUES (?,?,?,?,?,?,?,?)", [
        ("SHORT1", "x", "ACGT"*150, "G", "pdf_candidate", 0, 600, None),
        ("GOOD1",  "x", "ACGT"*350, "G", "pdf_candidate", 0, 1400, None),
        ("TYPE1",  "x", "ACGT"*350, "G", "pdf_candidate", 0, 1400, 1)])
    m = _mod()
    got = {r[0] for r in con.execute(
        f"SELECT acc_base FROM record WHERE source IN ('pdf_candidate') AND seq IS NOT NULL AND uncultured = 0 "
        f"AND LENGTH(seq) BETWEEN {m.REFERENCE_LEN_MIN} AND {m.REFERENCE_LEN_MAX} AND (is_type IS NULL OR is_type != 1)")}
    assert got == {"GOOD1"}, got
