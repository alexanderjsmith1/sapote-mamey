"""emit-modeb-template --out must not replace an existing file.

The single-BGC route used Path.write_text, so an authored card at the --out
path was silently replaced with a fresh template (exit 0).
"""
from __future__ import annotations
import argparse

from mamey.mode_b_receipt import emit_modeb_template_command
from tests.test_emit_modeb_empty_scope_v97250 import _board


def _args(pkg, out):
    return argparse.Namespace(package=str(pkg), bgc="BGC001", batch=False, scope="all",
                              top_n=None, out=str(out), fail_on_empty=False,
                              blastp_waiver=None, contract=None)


def test_existing_out_file_is_refused_and_kept(tmp_path, capsys):
    pkg = _board(tmp_path / "pkg", "High")
    out = tmp_path / "authored-card.md"
    out.write_text("authored work\n", encoding="utf-8")
    rc = emit_modeb_template_command(_args(pkg, out))
    assert rc == 1
    assert out.read_text(encoding="utf-8") == "authored work\n"
    assert "was not changed" in capsys.readouterr().err


def test_new_out_file_is_written(tmp_path):
    pkg = _board(tmp_path / "pkg", "High")
    out = tmp_path / "new-card.md"
    rc = emit_modeb_template_command(_args(pkg, out))
    assert rc == 0
    assert "§1" in out.read_text(encoding="utf-8")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["new-card.md", "pkg"]


def test_out_inside_missing_folder_is_refused(tmp_path):
    pkg = _board(tmp_path / "pkg", "High")
    rc = emit_modeb_template_command(_args(pkg, tmp_path / "no_such_dir" / "card.md"))
    assert rc == 1
    assert not (tmp_path / "no_such_dir").exists()
