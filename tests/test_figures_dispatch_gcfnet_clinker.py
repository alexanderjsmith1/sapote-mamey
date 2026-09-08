"""Regression: `mamey figures {gcf-network,clinker}` must dispatch, not fall through.

Bug (live through v9.7.318): cli.py wired `figures gcf-network` and
`figures clinker` subparsers, but figures_command() only handled
diagram/atlas/ani, so both new kinds fell through to
"figures: specify a kind (...)" and returned 2 — a wired-but-unreachable
command (wrong output, no crash). This test pins the routing.
"""
import types
import pytest
from mamey import bgc_figures


def _args(**kw):
    ns = types.SimpleNamespace()
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def test_gcf_network_routes_to_bigscape_figures(monkeypatch):
    called = {}

    def fake_gcf_network(db, strain, run, cutoff, evidence=None, out="x.png", leads=None):
        called.update(db=db, strain=strain, run=run, cutoff=cutoff, out=out)
        return {"status": "WRITTEN", "out": out}

    from mamey import bigscape_figures
    monkeypatch.setattr(bigscape_figures, "gcf_network", fake_gcf_network)

    rc = bgc_figures.figures_command(_args(
        fig_kind="gcf-network", db="d.db", strain="AS-660",
        run=32, cutoff=0.5, evidence=None, out="net.png",
    ))
    assert rc == 0
    assert called["strain"] == "AS-660" and called["run"] == 32


def test_clinker_routes_to_bigscape_figures(monkeypatch):
    seen = {}

    def fake_clinker(gbks, out="x.html"):
        seen.update(n=len(gbks), out=out)
        return {"status": "WRITTEN", "out": out}

    from mamey import bigscape_figures
    monkeypatch.setattr(bigscape_figures, "clinker_figure", fake_clinker)

    rc = bgc_figures.figures_command(_args(
        fig_kind="clinker", gbks=["a.gbk", "b.gbk"], out="c.html",
    ))
    assert rc == 0
    assert seen["n"] == 2


def test_gcf_network_nonwritten_returns_nonzero(monkeypatch):
    from mamey import bigscape_figures
    monkeypatch.setattr(bigscape_figures, "gcf_network",
                        lambda *a, **k: {"status": "SKIPPED_NO_DEPS"})
    rc = bgc_figures.figures_command(_args(
        fig_kind="gcf-network", db="d", strain="s", run=1,
        cutoff=0.5, evidence=None, out="o.png",
    ))
    assert rc == 1


def test_unknown_kind_message_lists_all_five(capsys):
    rc = bgc_figures.figures_command(_args(fig_kind=None))
    assert rc == 2
    out = capsys.readouterr().out
    for kind in ("diagram", "atlas", "ani", "gcf-network", "clinker"):
        assert kind in out
