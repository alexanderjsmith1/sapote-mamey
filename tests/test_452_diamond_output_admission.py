import sys
import types
import pytest
from mamey import diamond_align as mod

def test_missing_and_malformed_outputs_are_not_zero_hits(tmp_path):
    target = tmp_path / "hits.tsv"
    with pytest.raises(FileNotFoundError):
        mod._parse_outfmt6(str(target))
    target.write_text("")
    assert mod._parse_outfmt6(str(target)) == []
    target.write_text("truncated\trow\n")
    with pytest.raises(ValueError):
        mod._parse_outfmt6(str(target))

def test_binding_failure_status_is_not_ignored(monkeypatch):
    monkeypatch.setitem(sys.modules, "diamond4py.libdiamond", types.SimpleNamespace(main=lambda *args: 1))
    with pytest.raises(RuntimeError, match="failure status"):
        mod._run_diamond_blastp_raw("db", "query", "out", 1)
