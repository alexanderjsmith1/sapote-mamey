"""A recorded length that cannot be read is reported in binding_evidence, not silently dropped (.452)."""
import importlib.util
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("bqi_452", HERE / "tools" / "blastp_query_index.py")
bqi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bqi)


def _index(monkeypatch, recorded):
    key = (bqi.norm_strain("AS-1"), bqi.tag_of("ctg1_7"))

    class Finder:
        def __init__(self, root): pass
        def from_ledger(self, src): return {}, "none"
        def saved(self): return {key: Counter({("a" * 64, 300): 1})}
        def lengths_from_xml(self, src): return {}
        def lane_xml_lengths(self, src): return {}

    monkeypatch.setattr(bqi, "QueryFinder", Finder)
    monkeypatch.setattr(bqi, "result_genes", lambda root, src: {})
    return bqi.index_sources(Path("."), {"s.csv": {("AS-1", "ctg1_7"): recorded}})[0]


def test_unreadable_recorded_length_is_reported(monkeypatch):
    row = _index(monkeypatch, "abc")
    assert row["binding_evidence"] == "recorded_length_unreadable" and row["protein_sha256"] == ""


def test_matching_length_still_binds(monkeypatch):
    row = _index(monkeypatch, "300")
    assert row["binding_evidence"] == "saved_query_length_confirmed" and row["protein_sha256"] == "a" * 64


def test_no_silent_swallow_left_in_this_tool():
    import ast
    tree = ast.parse((HERE / "tools" / "blastp_query_index.py").read_text())
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler) and len(n.body) == 1 and isinstance(n.body[0], ast.Pass)]
