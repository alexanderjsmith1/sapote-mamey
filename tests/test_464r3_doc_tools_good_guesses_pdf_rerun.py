"""Synthetic Markdown only: a GOOD_GUESSES.pdf rerun is refused unless --replace, and a failed replace restores."""
import importlib.util
from pathlib import Path

import pytest

from mamey import good_guesses as gg


def _md(tmp_path):
    md = tmp_path / "GOOD_GUESSES.md"
    md.write_text("# Good Guesses\n\nSynthetic text.\n", encoding="utf-8")
    return md


def _fake(status, payload=b"NEW"):
    def once(md_path, pdf_path, pkg_hint=None):
        pdf_path.write_bytes(payload)
        Path(str(pdf_path)[:-4] + ".render_preflight.json").write_text("{}", encoding="utf-8")
        return {"status": status, "path": str(pdf_path) if status == "WRITTEN" else None}
    return once


def test_existing_pdf_is_refused_without_replace(tmp_path, monkeypatch):
    md, pdf = _md(tmp_path), tmp_path / "GOOD_GUESSES.pdf"
    pdf.write_bytes(b"EARLIER")
    monkeypatch.setattr(gg, "_render_pdf_once", _fake("WRITTEN"))
    res = gg.render_pdf(md, pdf)
    assert res["status"] == "OUTPUT_EXISTS" and "--replace" in res["detail"]
    assert pdf.read_bytes() == b"EARLIER"


def test_replace_swaps_in_the_new_pdf(tmp_path, monkeypatch):
    md, pdf = _md(tmp_path), tmp_path / "GOOD_GUESSES.pdf"
    pdf.write_bytes(b"EARLIER")
    monkeypatch.setattr(gg, "_render_pdf_once", _fake("WRITTEN"))
    assert gg.render_pdf(md, pdf, replace=True)["status"] == "WRITTEN"
    assert pdf.read_bytes() == b"NEW"
    assert not list(tmp_path.glob(".GOOD_GUESSES.previous.*"))


def test_failed_replace_restores_the_earlier_set(tmp_path, monkeypatch):
    md, pdf = _md(tmp_path), tmp_path / "GOOD_GUESSES.pdf"
    pdf.write_bytes(b"EARLIER")
    monkeypatch.setattr(gg, "_render_pdf_once", _fake("RENDER_FAILED", b"PARTIAL"))
    assert gg.render_pdf(md, pdf, replace=True)["status"] == "RENDER_FAILED"
    assert pdf.read_bytes() == b"EARLIER"
    assert not (tmp_path / "GOOD_GUESSES.render_preflight.json").exists()
    assert not list(tmp_path.glob(".GOOD_GUESSES.previous.*"))


def test_symlink_at_output_is_not_replaced(tmp_path, monkeypatch):
    md, pdf = _md(tmp_path), tmp_path / "GOOD_GUESSES.pdf"
    target = tmp_path / "elsewhere.pdf"
    target.write_bytes(b"KEEP")
    pdf.symlink_to(target)
    monkeypatch.setattr(gg, "_render_pdf_once", _fake("WRITTEN"))
    assert gg.render_pdf(md, pdf, replace=True)["status"] == "OUTPUT_NOT_REPLACEABLE"
    assert target.read_bytes() == b"KEEP" and pdf.is_symlink()


@pytest.mark.skipif(importlib.util.find_spec("reportlab") is None, reason="needs reportlab")
def test_real_rerun_refuses_then_replaces(tmp_path):
    md, pdf = _md(tmp_path), tmp_path / "GOOD_GUESSES.pdf"
    assert gg.render_pdf(md, pdf)["status"] == "WRITTEN"
    first = pdf.read_bytes()
    assert gg.render_pdf(md, pdf)["status"] == "OUTPUT_EXISTS"
    assert pdf.read_bytes() == first
    assert gg.render_pdf(md, pdf, replace=True)["status"] == "WRITTEN"
    assert pdf.read_bytes().startswith(b"%PDF")


def test_cli_has_replace_flag():
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), pytest.raises(SystemExit):
        gg.main(["--help"])
    assert "--replace" in buf.getvalue()
