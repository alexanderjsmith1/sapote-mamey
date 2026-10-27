"""BiG-SCAPE family figure tools exit nonzero when figures fail or nothing is drawn.

bigscape_family_figures returned 0 with FAILED rows in its INDEX files; bigscape_clinker_html
returned 0 with "PDF FAILED" rows or when no family page was written at all.
Hermetic: database helpers and renderers are stubbed.
"""
import importlib.util
import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_458x", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _db(tmp_path):
    db = tmp_path / "bs.db"
    sqlite3.connect(db).close()
    return str(db)


@pytest.mark.parametrize("failed,want", [(2, 1), (0, 0)])
def test_family_figures_exit_reflects_failures(tmp_path, monkeypatch, failed, want):
    ff = _load("bigscape_family_figures")
    monkeypatch.setattr(ff, "job_focus", lambda a, log: failed)
    rc = ff.main(["--db", _db(tmp_path), "--gbk-dir", str(tmp_path), "--out", str(tmp_path / "o"),
                  "--focus", "AS-1"])
    assert rc == want


def _clinker(tmp_path, monkeypatch, payload, pdf):
    ch = _load("bigscape_clinker_html")
    monkeypatch.setattr(ch, "gbk_index", lambda *a, **k: {})
    monkeypatch.setattr(ch, "family_members", lambda *a, **k: {})
    monkeypatch.setattr(ch, "build_family", lambda *a, **k: payload)
    monkeypatch.setattr(ch, "write_page", lambda payload, title, outp: pathlib.Path(outp).write_text("x"))
    monkeypatch.setattr(ch, "to_pdf", lambda *a, **k: pdf)
    return ch.main(["--db", _db(tmp_path), "--out", str(tmp_path / "o"), "--family", "7",
                    "--chrome", "/nonexistent/chrome"])


PAYLOAD = {"tracks": [{"cls": "a"}, {"cls": "b"}], "n_shared": 1, "private": 0}


def test_clinker_pdf_failure_exits_nonzero(tmp_path, monkeypatch):
    assert _clinker(tmp_path, monkeypatch, PAYLOAD, None) == 1


def test_clinker_nothing_written_exits_nonzero(tmp_path, monkeypatch):
    assert _clinker(tmp_path, monkeypatch, None, None) == 1


def test_clinker_success_exits_zero(tmp_path, monkeypatch):
    out_pdf = tmp_path / "o" / "x.pdf"
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    out_pdf.write_text("pdf")
    assert _clinker(tmp_path, monkeypatch, PAYLOAD, str(out_pdf)) == 0
