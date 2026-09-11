"""v9.7.410: the cohort class-capacity heatmap auto-emits on a multi-strain run.

Before this patch ``mamey/cohort_class_heatmap.py`` was reachable only through the manual
``--workbook`` routes (``figures --figure-set cohort-class`` / ``render-all-figures --sets
cohort-class``); ``run_batch``'s ``if len(results) > 1`` block never called it. The auto-emit
call site is ``mamey.cli._auto_emit_cohort_class_heatmap`` (the wiring into ``run_batch`` is a
plain call next to ``build_cohort_figures``). These tests exercise the helper on a fake
2-strain run layout, prove the wiring exists in ``run_batch``, and pin the no-label-overlap
layout of the renderer itself.
"""
from __future__ import annotations

import csv
import inspect
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

from mamey import cli
from mamey.cohort_class_heatmap import render_cohort_class_heatmap

_INV_HEADER = ["BGC_ID", "Release", "Contig", "Region", "Products", "Boundary"]


def _plant_package(run_dir: Path, sid: str, products_per_bgc: list[str]) -> dict:
    """Fake the run layout: <run>/<sid>/package/<sid>_2_inventory.csv (+ zip path in results)."""
    pkg = run_dir / sid / "package"
    pkg.mkdir(parents=True)
    with open(pkg / f"{sid}_2_inventory.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(_INV_HEADER)
        for i, prods in enumerate(products_per_bgc, 1):
            w.writerow([f"{sid}_{i:03d}", "PRIVATE", "c1", i, prods, "interior"])
    return {"strain_id": sid, "status": "OK", "raw_bgcs": len(products_per_bgc),
            "assembly_tier": "HIGH", "package_zip": str(run_dir / sid / f"{sid}.zip")}


def _two_strain_run(tmp_path: Path) -> tuple[Path, list[dict]]:
    run = tmp_path / "runs"
    a = _plant_package(run, "AS-901", ["NRPS", "NRPS", "T1PKS", "terpene", "NRPS; T1PKS",
                                      "saccharide", "NAPAA", "lanthipeptide-class-i"])
    b = _plant_package(run, "AS-902", ["NRPS", "terpene", "terpene", "RiPP-like",
                                      "NI-siderophore", "saccharide"])
    return run, [a, b]


def test_two_strain_run_emits_heatmap_and_data_csv(tmp_path: Path) -> None:
    run, results = _two_strain_run(tmp_path)
    lines: list[str] = []
    res = cli._auto_emit_cohort_class_heatmap(results, run, logger=lines.append)

    assert res["status"] == "OK" and res["figure_count"] == 1
    png = run / "cohort_figures" / "cohort_class_capacity_heatmap.png"
    data = run / "cohort_figures" / "cohort_class_capacity_heatmap_data.csv"
    assert png.is_file() and png.stat().st_size > 0
    assert data.is_file()
    # No skip card left beside a successful render.
    assert not png.with_suffix(".SKIPPED.md").exists()

    with open(data, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    by_strain = {r["strain"]: r for r in rows}
    assert set(by_strain) == {"AS-901", "AS-902"}
    # Counts equal the master-workbook bucketing on the same Products column:
    # "NRPS; T1PKS" contributes to BOTH classes; saccharide is a standing exclusion (dropped).
    assert by_strain["AS-901"]["NRPS"] == "3" and by_strain["AS-901"]["T1PKS"] == "2"
    assert by_strain["AS-902"]["terpene"] == "2"
    assert "saccharide" not in rows[0]
    assert "NAPAA" in rows[0]  # registry-neutral, retained
    assert rows[0]["label_provenance"] == "RAW_ANTISMASH"
    # One-line announcement, cohort-figures style.
    assert any("Cohort class heatmap:" in ln and "2 strains" in ln for ln in lines)
    # The renderer's own label-overlap smoke check is clean on the real 2-strain figure.
    assert res["detail"]["text_overlap_warnings"] == []


def test_run_batch_wires_the_auto_emit_next_to_cohort_figures() -> None:
    """Fail-before: .409 run_batch never referenced the class heatmap at all."""
    src = inspect.getsource(cli.run_batch)
    assert "_auto_emit_cohort_class_heatmap(results" in src
    # It lives inside the multi-strain block, after the cohort-figures bridge.
    assert src.index("build_cohort_figures(results") < src.index("_auto_emit_cohort_class_heatmap(results")


def test_single_strain_is_a_silent_typed_noop(tmp_path: Path) -> None:
    run = tmp_path / "runs"
    only = _plant_package(run, "AS-901", ["NRPS"])
    lines: list[str] = []
    res = cli._auto_emit_cohort_class_heatmap([only], run, logger=lines.append)
    assert res == {"status": "SKIPPED_SINGLE_STRAIN", "figure_count": 0}
    assert not (run / "cohort_figures").exists()
    assert lines == []


def test_missing_inventory_is_a_typed_skip_not_a_crash(tmp_path: Path) -> None:
    run = tmp_path / "runs"
    a = _plant_package(run, "AS-901", ["NRPS"])
    b = {"strain_id": "AS-902", "status": "FAILED", "package_zip": ""}  # no package dir at all
    lines: list[str] = []
    res = cli._auto_emit_cohort_class_heatmap([a, b], run, logger=lines.append)
    assert res["status"] == "SKIPPED_INSUFFICIENT_DATA" and res["figure_count"] == 0
    assert not (run / "cohort_figures" / "cohort_class_capacity_heatmap.png").exists()
    assert any("AS-902" in ln and "row skipped" in ln for ln in lines)
    assert any("SKIPPED" in ln for ln in lines)


def test_deterministic_reemit(tmp_path: Path) -> None:
    run, results = _two_strain_run(tmp_path)
    data = run / "cohort_figures" / "cohort_class_capacity_heatmap_data.csv"
    cli._auto_emit_cohort_class_heatmap(results, run, logger=lambda *a: None)
    first = data.read_bytes()
    cli._auto_emit_cohort_class_heatmap(results, run, logger=lambda *a: None)
    assert data.read_bytes() == first


def test_renderer_rows_entry_point_and_no_label_overlap(tmp_path: Path, monkeypatch) -> None:
    """rows= bypasses the workbook; footer, class labels and title never share pixels."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    kept: list = []
    monkeypatch.setattr(plt, "close", lambda fig=None: kept.append(fig))
    rows = [
        {"strain": "AS-901", "NRPS": 11, "T1PKS": 9, "RiPP-like": 10, "terpene": 8, "NAPAA": 3,
         "lanthipeptide-class-i": 2, "NI-siderophore": 1, "other": 13},
        {"strain": "AS-902", "NRPS": 18, "T1PKS": 13, "RiPP-like": 8, "terpene": 10, "NAPAA": 0,
         "lanthipeptide-class-i": 1, "NI-siderophore": 2, "other": 14},
    ]
    res = render_cohort_class_heatmap(None, tmp_path / "h.png", tmp_path / "h.csv",
                                      claim_prefix="PRIVATE", rows=rows)
    assert res["status"] == "OK" and res["n_strains"] == 2
    assert res["text_overlap_warnings"] == []          # project checker: axes-internal labels
    fig = kept[0]
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    ax, cbar_ax = fig.axes[0], fig.axes[1]
    footer = fig.texts[0].get_window_extent(rend)
    ticks = [t.get_window_extent(rend) for t in ax.get_xticklabels() if t.get_text()]
    # footer band sits wholly below the lowest class label
    assert footer.y1 < min(b.y0 for b in ticks)
    # class labels are vertical: no neighbour's box touches another
    for i in range(len(ticks) - 1):
        assert not ticks[i].overlaps(ticks[i + 1])
    # title and colorbar label never collide
    assert not ax.title.get_window_extent(rend).overlaps(
        cbar_ax.yaxis.label.get_window_extent(rend))


def test_renderer_empty_rows_writes_skip_card(tmp_path: Path) -> None:
    res = render_cohort_class_heatmap(None, tmp_path / "h.png", tmp_path / "h.csv", rows=[])
    assert res["status"] == "SKIPPED"
    assert (tmp_path / "h.SKIPPED.md").exists()
