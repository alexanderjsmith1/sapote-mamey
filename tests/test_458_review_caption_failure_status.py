from pathlib import Path
import importlib.util
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("review_tool", ROOT / "tools/caption_band.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

def test_missing_pillow_uses_documented_status(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(tool, "_pillow", lambda: None)
    outdir = tmp_path / "output"
    with pytest.raises(SystemExit) as caught:
        tool.add_band(tmp_path / "plot.png", tmp_path / "caption.md", outdir)
    assert caught.value.code == 2
    assert "Pillow is not installed" in capsys.readouterr().err
    assert not outdir.exists()
