"""Require fresh, nonempty alignment output and surface incomplete attempts."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from mamey import bigscape_figures


@pytest.mark.parametrize("alignment", [None, b""])
def test_missing_or_empty_alignment_is_incomplete(tmp_path, monkeypatch, alignment):
    out = tmp_path / "result.html"
    monkeypatch.setattr(bigscape_figures.shutil, "which", lambda _: "/fake/clinker")
    def run(args, **kwargs):
        Path(args[args.index("-p") + 1]).write_text("new html")
        if alignment is not None:
            Path(args[args.index("-o") + 1]).write_bytes(alignment)
        return SimpleNamespace(returncode=0, stdout="bounded diagnostic", stderr="")
    monkeypatch.setattr(bigscape_figures.subprocess, "run", run)
    result = bigscape_figures.clinker_figure(["one.gbk", "two.gbk"], out)
    assert result["status"] == "CLINKER_INCOMPLETE_OUTPUT"
    assert result["out"] == str(out)
    assert "bounded diagnostic" in result["diagnostic"]


def test_fresh_pair_uses_sibling_alignment_path(tmp_path, monkeypatch):
    out = tmp_path / "parent.html" / "result.html"
    monkeypatch.setattr(bigscape_figures.shutil, "which", lambda _: "/fake/clinker")
    def run(args, **kwargs):
        Path(args[args.index("-p") + 1]).write_text("new html")
        Path(args[args.index("-o") + 1]).write_text("new alignment")
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(bigscape_figures.subprocess, "run", run)
    result = bigscape_figures.clinker_figure(["one.gbk", "two.gbk"], out)
    assert result["status"] == "WRITTEN"
    assert Path(result["alignments"]) == out.parent / "result_alignments.txt"
    assert Path(result["alignments"]).read_text() == "new alignment"


def test_existing_alignment_is_preserved_and_refused(tmp_path, monkeypatch):
    out = tmp_path / "result.html"
    alignment = tmp_path / "result_alignments.txt"
    alignment.write_text("old")
    monkeypatch.setattr(bigscape_figures.shutil, "which", lambda _: "/fake/clinker")
    def unexpected(*args, **kwargs):
        raise AssertionError("existing alignment must not trigger clinker")
    monkeypatch.setattr(bigscape_figures.subprocess, "run", unexpected)
    result = bigscape_figures.clinker_figure(["one.gbk", "two.gbk"], out)
    assert result["status"] == "CLINKER_FAILED"
    assert alignment.read_text() == "old" and not out.exists()
