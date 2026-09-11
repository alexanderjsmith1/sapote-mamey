"""EVAL-P01 (v9.7.326+): npatlas compound resolution must never bind the WRONG molecule's
chemistry to a KCB label. The old bidirectional prefix match (first-in-dict-order + `k.startswith(n)`)
let a short catalog name capture a long query (e.g. 'actin' -> 'actinomycin d') and picked an
arbitrary molecule among several. The fix requires both sides >=6 chars and an unambiguous
(single distinct molecule) match; ambiguity resolves to nothing.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mamey.npatlas_resolver as R


def _idx():
    return {
        "actin":          {"npaid": "NPA100", "inchikey": "AAA", "mol_formula": "C1"},   # 5 chars
        "nocobactin":     {"npaid": "NPA200", "inchikey": "BBB", "mol_formula": "C2"},
        "streptomycin a": {"npaid": "NPA300", "inchikey": "CCC", "mol_formula": "C3"},
        "streptomycin b": {"npaid": "NPA301", "inchikey": "DDD", "mol_formula": "C4"},   # different molecule
        "desertomycin":   {"npaid": "NPA400", "inchikey": "EEE", "mol_formula": "C5"},
    }


def test_short_catalog_name_cannot_capture_long_query(monkeypatch):
    monkeypatch.setattr(R, "_load_index", _idx)
    # 'actin' (5 chars) must NOT bind to 'actinomycin d' (the old k.startswith(n) leak)
    assert R.resolve_compound("actinomycin d") is None


def test_ambiguous_prefix_resolves_to_nothing(monkeypatch):
    monkeypatch.setattr(R, "_load_index", _idx)
    # 'streptomycin' prefixes two DISTINCT molecules -> claim-safe None (was: arbitrary first-wins)
    assert R.resolve_compound("streptomycin") is None


def test_unambiguous_suffix_variant_still_resolves(monkeypatch):
    monkeypatch.setattr(R, "_load_index", _idx)
    # the documented legit case: 'nocobactin NA' -> catalog 'nocobactin' (single candidate)
    rec = R.resolve_compound("nocobactin NA")
    assert rec is not None and rec["npaid"] == "NPA200"


def test_exact_match_unaffected(monkeypatch):
    monkeypatch.setattr(R, "_load_index", _idx)
    rec = R.resolve_compound("desertomycin")
    assert rec is not None and rec["npaid"] == "NPA400"
