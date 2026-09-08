"""LQ-NPATLAS-01 (v9.7.330): npclassifier CLASS-frequency grounding for the Mode B §13 / S6
"class in Actinobacteria" sub-question.

Tests the aggregate class-frequency computation (organism-independent), the claim-safety boundary
string, graceful degradation when the add-on is absent, and that no genus/bioactivity field leaks.

NB: the test file/function names deliberately avoid the substring "atlas" — conftest flags any test
nodeid containing that hint as slow and skips it by default.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mamey.npatlas_resolver as npr  # noqa: E402


def _reset_caches():
    npr._class_counts.cache_clear()


def test_degrades_when_addon_absent(monkeypatch):
    monkeypatch.setattr(npr, "_load_index", lambda: {})
    _reset_caches()
    assert npr.class_frequency("Macrolides") is None
    assert "unavailable" in npr.class_in_actinobacteria_sentence("Macrolides").lower()


def test_aggregate_class_frequency(monkeypatch):
    synthetic = {
        "candicidin": {"npclassifier": {"class": ["Polyene macrolides"]}},
        "amphotericin": {"npclassifier": {"class": ["Polyene macrolides"]}},
        "rhizocticin": {"npclassifier": {"class": ["Phosphonopeptides"]}},
        "geosmin": {"npclassifier": {"class": ["Terpenoids"]}},
    }
    monkeypatch.setattr(npr, "_load_index", lambda: synthetic)
    _reset_caches()
    f = npr.class_frequency("Polyene macrolides")
    assert f["n_records"] == 2 and f["total_actino_records"] == 4 and f["pct"] == 50.0
    assert f["found"] is True
    # boundary must be explicit and carry no genus/bioactivity notion
    assert "NOT genus" in f["boundary"] and "NOT bioactivity" in f["boundary"]
    assert "genus" not in {k.lower() for k in f}  # no genus field leaks into the payload


def test_class_not_represented(monkeypatch):
    monkeypatch.setattr(npr, "_load_index", lambda: {
        "geosmin": {"npclassifier": {"class": ["Terpenoids"]}}})
    _reset_caches()
    s = npr.class_in_actinobacteria_sentence("Enediynes")
    assert "not represented" in s.lower()
    assert "not a genus" in s.lower() or "not a genus-precedence" in s.lower()


def test_case_insensitive_match(monkeypatch):
    monkeypatch.setattr(npr, "_load_index", lambda: {
        "x": {"npclassifier": {"class": ["Polyene Macrolides"]}}})
    _reset_caches()
    assert npr.class_frequency("polyene macrolides")["n_records"] == 1
