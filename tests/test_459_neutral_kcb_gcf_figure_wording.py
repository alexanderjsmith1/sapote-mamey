"""KCB and GCF figures use neutral wording on the plot.

The owner ruled that a plot carries no interpretive text. The GCF network title and legend said
"novelty-leaning" and "novel-leaning", cohort fig6 said "candidate-novel" and "KCB novelty
composition", and the G03 bin said "no KCB hit (novel-leaning)". They now read "no KCB hit",
"KCB similarity composition" and "GCF-dark singletons". These tests read the text on the
rendered figures.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.text import Text  # noqa: E402


@pytest.fixture
def drawn_text(monkeypatch):
    """Every string on every figure saved during the test."""
    seen: list[str] = []
    original = Figure.savefig

    def capture(self, *args, **kwargs):
        seen.extend(t.get_text() for t in self.findobj(Text) if t.get_text())
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", capture)
    return seen


def _novel_words(texts):
    return [t for t in texts if "novel" in t.lower()]


def _inventory(root: Path, sid: str, rows):
    pkg = root / sid / "package"
    pkg.mkdir(parents=True)
    with open(pkg / f"{sid}_2_inventory.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Products", "Length_kb", "Boundary", "KCB_top", "KCB_score"])
        w.writerows(rows)


def test_fig6_title_and_legend_are_neutral(tmp_path, drawn_text):
    from mamey.cohort_figures_extended import fig_kcb_novelty

    root = tmp_path / "runs"
    rows = [["BGC001", "NRPS", "40", "Interior", "", ""],
            ["BGC002", "terpene", "20", "Interior", "BGC0000001.1 | x | 1", "20"],
            ["BGC003", "PKS; T1PKS", "50", "Interior", "BGC0000002.1 | y | 1", "900"]]
    for sid in ("SYNTHETIC-CASE-001", "SYNTHETIC-CASE-002"):
        _inventory(root, sid, rows)
    out = tmp_path / "figs"
    out.mkdir()
    fig_kcb_novelty(str(root), ["SYNTHETIC-CASE-001", "SYNTHETIC-CASE-002"], str(out))
    assert "KCB similarity composition across strains" in drawn_text
    assert "no KCB hit (<1)" in drawn_text
    assert not _novel_words(drawn_text), _novel_words(drawn_text)


def test_g03_no_hit_bin_is_neutral(tmp_path, monkeypatch):
    from mamey import cohort_figures as cf

    order = ["SYNTHETIC-CASE-001", "SYNTHETIC-CASE-002"]
    inv = {s: [{"BGC_ID": "BGC001", "Products": "NRPS", "KCB_top": "", "KCB_score": "", "Boundary": "Interior"},
               {"BGC_ID": "BGC002", "Products": "terpene", "KCB_top": "BGC0000001.1 | x | 1", "KCB_score": "40",
                "Boundary": "Interior"},
               {"BGC_ID": "BGC003", "Products": "PKS", "KCB_top": "BGC0000002.1 | y | 1", "KCB_score": "900",
                "Boundary": "Edge"}] for s in order}
    drawn = {}
    monkeypatch.setattr(cf, "_load_inv_g", lambda S, o: inv)
    monkeypatch.setattr(cf, "hmap", lambda mat, rowlabs, o, title, fid, OUT, **kw: drawn.__setitem__(fid, list(rowlabs)))
    cf.batch1({s: {"deep": {"bgc_profile": []}} for s in order}, order, str(tmp_path))
    labels = drawn["kcb_similarity_strength"]
    assert labels[0] == "no KCB hit"
    assert not _novel_words(labels), labels


def test_gcf_network_title_and_legend_are_neutral(tmp_path, drawn_text):
    pytest.importorskip("networkx")
    from mamey import bigscape_figures

    db = tmp_path / "bigscape_run.db"
    con = sqlite3.connect(str(db))
    con.executescript("""
        create table gbk(id integer primary key, path text);
        create table bgc_record(id integer primary key, gbk_id integer, record_type text);
        create table connected_component(id integer, record_id integer, cutoff real, run_id integer);
    """)
    for i, p in enumerate(["/x/RB68_NODE_1_length_1000_cov_5.0.region001.gbk",
                           "/x/RB68_NODE_2_length_2000_cov_6.0.region001.gbk",
                           "/x/RB68_NODE_3_length_3000_cov_6.0.region001.gbk"], start=1):
        con.execute("insert into gbk(id, path) values (?,?)", (i, p))
        con.execute("insert into bgc_record(id, gbk_id, record_type) values (?,?, 'region')", (i, i))
    con.execute("insert into connected_component values (100, 1, 0.5, 1)")
    con.execute("insert into connected_component values (100, 2, 0.5, 1)")
    con.commit(); con.close()
    res = bigscape_figures.gcf_network(str(db), "RB68", run=1, cutoff=0.5, out=str(tmp_path / "gcf_network_RB68.png"))
    assert res.get("status") == "WRITTEN", res
    assert "GCF-dark singletons" in drawn_text
    assert not _novel_words(drawn_text), _novel_words(drawn_text)
