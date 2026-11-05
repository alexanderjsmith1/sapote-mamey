"""The documented incomplete clinker result is rejected by the dispatcher."""
from argparse import Namespace
from pathlib import Path

from mamey import bgc_figures, bigscape_figures


def test_documented_incomplete_status_returns_failure(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    doc = (root / "docs/BIGSCAPE_FIGURES.md").read_text(encoding="utf-8")
    assert "CLINKER_INCOMPLETE_OUTPUT" in doc
    assert "nonempty HTML and alignment files" in doc
    monkeypatch.setattr(bigscape_figures, "clinker_figure", lambda *a, **k: {"status": "CLINKER_INCOMPLETE_OUTPUT"})
    monkeypatch.setattr(bgc_figures, "emit", lambda *a, **k: None)
    assert bgc_figures.figures_command(Namespace(fig_kind="clinker", gbks=["one.gbk", "two.gbk"], out="output.html")) == 1
