"""mode-b given an unreadable manifest.json prints a message naming it, not a JSONDecodeError traceback."""
from types import SimpleNamespace

from mamey import chatgpt_commands as CC


def test_mode_b_invalid_manifest(tmp_path, capsys):
    pkg = tmp_path / "S1" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text("{not json", encoding="utf-8")
    (pkg / "S1_4_triage_board.csv").write_text("BGC_ID,Contig\nBGC001,NODE_1\n", encoding="utf-8")
    args = SimpleNamespace(package=str(pkg), top_n=3, outdir=str(tmp_path / "out"), strict_all=False)
    assert CC.mode_b_command(args) == 1
    err = capsys.readouterr().err
    assert "manifest.json" in err and "cannot be read" in err
    assert not (tmp_path / "out").exists()
