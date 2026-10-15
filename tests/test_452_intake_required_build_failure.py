import sys
from types import SimpleNamespace
import pytest
from tools import mamey_intake as mod

def test_required_workbook_failure_propagates(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mamey_intake", "--packages", str(tmp_path), "--banked-dir", str(tmp_path / "bank"), "--workbook", str(tmp_path / "workbook.xlsx")])
    monkeypatch.setattr(mod, "init_banked", lambda *args: [])
    monkeypatch.setattr(mod, "find_snapshots", lambda *args: {})
    import _bankio
    monkeypatch.setattr(_bankio, "checked_json", lambda *args: {"strains": {}, "bgcs": []})
    monkeypatch.setattr(mod.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=7, stdout="", stderr="synthetic failure"))
    with pytest.raises(SystemExit, match="required workbook build failed"):
        mod.main()
