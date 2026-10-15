import sys
import subprocess
from pathlib import Path
from types import SimpleNamespace
from tools import lab_office_render as mod

def test_recursive_same_basename_is_refused_before_rendering(tmp_path, monkeypatch):
    for folder in ("first", "second"):
        source = tmp_path / folder / "figure.json"
        source.parent.mkdir()
        source.write_text('{"template":"synthetic","data":{}}')
    monkeypatch.setattr(mod, "NODE", sys.executable)
    monkeypatch.setattr(mod, "RENDERER", sys.executable)
    monkeypatch.setitem(sys.modules, "cairosvg", SimpleNamespace(svg2png=lambda **kwargs: None))
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append(a) or SimpleNamespace(returncode=0))
    out = tmp_path / "output"
    monkeypatch.setattr(sys, "argv", ["lab_office_render", "--dir", str(tmp_path), "--recursive", "--out", str(out)])
    assert mod.main() == 2
    assert calls == []
    assert not out.exists()
