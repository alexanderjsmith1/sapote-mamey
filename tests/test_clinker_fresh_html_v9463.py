"""Clinker reports success only for a fresh, nonempty HTML artifact."""
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest
from mamey import bgc_figures, bigscape_figures


def test_existing_html_is_not_admitted_or_overwritten(tmp_path, monkeypatch):
    out = tmp_path / "result.html"
    out.write_text("old")
    monkeypatch.setattr(bigscape_figures.shutil, "which", lambda _: "/fake/clinker")
    def unexpected(*args, **kwargs):
        raise AssertionError("existing output must not trigger clinker")
    monkeypatch.setattr(bigscape_figures.subprocess, "run", unexpected)
    result = bigscape_figures.clinker_figure(["one.gbk", "two.gbk"], out)
    assert result["status"] == "CLINKER_FAILED"
    assert out.read_text() == "old"


@pytest.mark.parametrize("payload", [None, b""])
def test_success_exit_without_nonempty_html_is_failure(tmp_path, monkeypatch, payload):
    out = tmp_path / "result.html"
    monkeypatch.setattr(bigscape_figures.shutil, "which", lambda _: "/fake/clinker")
    def run(args, **kwargs):
        if payload is not None:
            Path(args[args.index("-p") + 1]).write_bytes(payload)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    monkeypatch.setattr(bigscape_figures.subprocess, "run", run)
    result = bigscape_figures.clinker_figure(["one.gbk", "two.gbk"], out)
    assert result["status"] == "CLINKER_FAILED"


@pytest.mark.parametrize("status,code", [("WRITTEN", 0), ("CLINKER_FAILED", 1), ("CLINKER_INCOMPLETE_OUTPUT", 1)])
def test_dispatcher_propagates_success_and_failure(status, code, monkeypatch):
    monkeypatch.setattr(bigscape_figures, "clinker_figure", lambda *a, **k: {"status": status})
    monkeypatch.setattr(bgc_figures, "emit", lambda *a, **k: None)
    args = Namespace(fig_kind="clinker", gbks=["one.gbk", "two.gbk"], out="output.html")
    assert bgc_figures.figures_command(args) == code
