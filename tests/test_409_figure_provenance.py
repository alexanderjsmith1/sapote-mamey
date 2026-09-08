"""CLAUDE_409_figure_provenance — the three figure-provenance defects from the .408 numeric-accuracy audit.

Each test fails on sealed .408 and passes after the lane patch:
  (1) ANI heatmap now writes a numeric `*_ani_matrix.csv` so every plotted cell is traceable.
  (2) The per-strain 8g class distribution discloses its full denominator + both exclusions
      (lead-prioritization drop + saccharide-only omission) in the data export.
  (3) The GCF network writes a `*_scope.json` receipt proving a strain-filenamed figure is a
      strain-centric subgraph of the cohort run, not the whole cohort network.
"""
import csv
import sqlite3

import pytest


# --------------------------------------------------------------------------- (1) ANI matrix
def _write_fasta(path, seq, rid="c1"):
    path.write_text(f">{rid}\n{seq}\n", encoding="utf-8")


def test_ani_heatmap_persists_numeric_matrix(tmp_path):
    pytest.importorskip("pyskani")
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("Bio")
    from mamey import bgc_figures

    # two minimal strain dirs, each with one genome FASTA
    da, db = tmp_path / "A", tmp_path / "B"
    da.mkdir(); db.mkdir()
    base = "ATGC" * 200
    _write_fasta(da / "genome.fna", base)
    _write_fasta(db / "genome.fna", base[:600] + "TTTT" + base[604:])

    out_png = tmp_path / "ani_heatmap.png"
    res = bgc_figures.ani_heatmap([str(da), str(db)], str(out_png))
    assert res.get("names") and len(res["names"]) == 2

    matrix_csv = tmp_path / "ani_heatmap_ani_matrix.csv"
    assert matrix_csv.exists(), "the numeric ANI matrix must be written beside the figure"
    assert res.get("ani_matrix_csv") == str(matrix_csv)

    rows = list(csv.reader(matrix_csv.open()))
    header = next(r for r in rows if r and r[0] == "strain")
    names = header[1:]
    assert names == res["names"]
    body = {r[0]: r[1:] for r in rows if r and r[0] in names}
    # every plotted cell is on disk and matches the returned matrix; diagonal = 100
    for i, rn in enumerate(names):
        assert abs(float(body[rn][i]) - 100.0) < 1e-6
        for j, cn in enumerate(names):
            assert abs(float(body[rn][j]) - res["ani"][i][j]) < 1e-3


# --------------------------------------------------------------------------- (2) 8g denominator
def _read_csv(path):
    return list(csv.reader(open(path, newline="")))


def test_class_distribution_discloses_denominator(tmp_path):
    pytest.importorskip("matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mamey import figures_extra

    # 4 BGCs reach the figure (post lead-exclusion): 1 is pure-saccharide (omitted here).
    bgcs = [
        {"products": "NRPS"},
        {"products": "T1PKS"},
        {"products": "terpene"},
        {"products": "saccharide"},   # pure saccharide -> omitted by figure policy
    ]
    census = {"total": 10, "lead_excluded": 3}  # strain had 10; 3 dropped upstream; 4 reached here
    png = tmp_path / "S_8g_fig_class_distribution.png"
    out = figures_extra.fig_class_distribution(bgcs, census, str(png), "Strain S", plt)
    assert out == str(png)

    csv_path = str(png).replace(".png", "_data.csv")
    rows = _read_csv(csv_path)
    flat = {tuple(r[:2]): (r[2] if len(r) > 2 else "") for r in rows}

    # full denominator + both exclusions + plotted count are all on disk
    assert flat[("# denominator", "strain_total_bgcs")] == "10"
    assert flat[("# excluded_upstream",
                 "lead_prioritization_excluded (housekeeping/primary-metabolism/mobile-element)")] == "3"
    assert flat[("# excluded_here",
                 "saccharide_only_omitted (figure_policy.omit_saccharides)")] == "1"
    assert flat[("# plotted", "bgcs_shown_as_bars")] == "3"

    # the class rows reconcile with the plotted count (3 non-saccharide BGCs -> 3 bars summing to 3)
    hdr = rows.index(["primary_class", "bgc_count"])
    class_rows = [r for r in rows[hdr + 1:] if r]
    assert sum(int(r[1]) for r in class_rows) == 3


# --------------------------------------------------------------------------- (3) GCF scope receipt
def _build_bigscape_db(path):
    con = sqlite3.connect(str(path))
    con.executescript(
        """
        create table gbk(id integer primary key, path text);
        create table bgc_record(id integer primary key, gbk_id integer, record_type text);
        create table connected_component(id integer, record_id integer, cutoff real, run_id integer);
        """
    )
    # two RB68 region records on NODE_-style contigs (parse_locator handles these on sealed .408)
    paths = [
        "/x/RB68_NODE_1_length_1000_cov_5.0.region001.gbk",
        "/x/RB68_NODE_2_length_2000_cov_6.0.region001.gbk",
    ]
    for i, p in enumerate(paths, start=1):
        con.execute("insert into gbk(id, path) values (?,?)", (i, p))
        con.execute("insert into bgc_record(id, gbk_id, record_type) values (?,?, 'region')", (i, i))
    # one shared connected component (cutoff 0.5, run 1) grouping both -> a drawn family
    con.execute("insert into connected_component values (100, 1, 0.5, 1)")
    con.execute("insert into connected_component values (100, 2, 0.5, 1)")
    con.commit(); con.close()


def test_gcf_network_writes_scope_receipt(tmp_path):
    pytest.importorskip("networkx")
    pytest.importorskip("matplotlib")
    import json
    from mamey import bigscape_figures

    db = tmp_path / "bigscape_run.db"
    _build_bigscape_db(db)
    out_png = tmp_path / "gcf_network_RB68.png"

    res = bigscape_figures.gcf_network(str(db), "RB68", run=1, cutoff=0.5, out=str(out_png))
    assert res.get("status") == "WRITTEN", res

    scope_json = tmp_path / "gcf_network_RB68_scope.json"
    assert scope_json.exists(), "a scope receipt must be written beside the GCF network raster"
    assert res.get("scope_json") == str(scope_json)

    scope = json.loads(scope_json.read_text())
    # the receipt proves this strain-named figure is a strain-centric subgraph, with counts
    assert "strain-centric subgraph" in scope["scope"]
    assert scope["strain"] == "RB68"
    assert scope["strain_region_records"] == 2
    assert scope["families_drawn"] >= 1
    assert scope["graph_nodes"] == res["graph_nodes"] > 0
    assert scope["graph_edges"] == res["graph_edges"] > 0
