"""CLAUDE_409 — figure `_data.csv` sidecar coverage (v9.7.409).

Regression guard for the figure-data-sidecar lane: three figure modules previously wrote a
PNG with no adjacent tidy `_data.csv`, so those figures were not R/ggplot2-reproducible.
This test proves that a previously-sidecar-less figure now emits its `<stem>_data.csv`
carrying the exact plotted values, and that the sidecar is tidy (one observation per row).

Primary target: `mamey.cohort_figures_extended.fig_boundary_profile` — before this lane the whole
11-figure extended suite wrote zero sidecars. It reads only `<sid>_2_inventory.csv`, so it is
exercisable from tiny pure-CSV fixtures with no antiSMASH input.

Run after applying CLAUDE_409_figure_data_sidecars.patch to the bundle:
    pytest tests/test_figure_data_sidecars.py -q
"""
import csv
import os

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("numpy")

from mamey import cohort_figures_extended as cfe  # noqa: E402


def _write_inventory(pkg_dir, sid, boundaries):
    os.makedirs(pkg_dir, exist_ok=True)
    path = os.path.join(pkg_dir, f"{sid}_2_inventory.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Boundary", "Length_kb", "Products"])
        for i, b in enumerate(boundaries, 1):
            w.writerow([f"BGC{i:03d}", b, 10.0 + i, "T1PKS"])
    return path


def test_boundary_profile_writes_tidy_sidecar(tmp_path):
    root = tmp_path / "runs"
    out = tmp_path / "figs"
    out.mkdir()

    # two strains with known Boundary composition
    comp = {
        "AS-T1": ["Interior", "Interior", "Edge", "Full-contig"],
        "AS-T2": ["Interior", "Edge", "Edge"],
    }
    strains = list(comp)
    for sid, b in comp.items():
        _write_inventory(str(root / sid / "package"), sid, b)

    cfe.fig_boundary_profile(str(root), strains, str(out))

    png = out / "fig8_boundary_profile.png"
    sidecar = out / "fig8_boundary_profile_data.csv"
    assert png.exists(), "figure PNG must still render"
    assert sidecar.exists(), "figure must now ship an adjacent _data.csv sidecar"

    rows = list(csv.DictReader(open(sidecar, encoding="utf-8")))
    # tidy long form: one row per (strain x boundary-band), three bands per strain
    assert rows[0].keys() >= {"strain", "boundary", "n_bgcs"}
    got = {(r["strain"], r["boundary"]): int(r["n_bgcs"]) for r in rows}

    expected = {
        ("AS-T1", "Interior"): 2, ("AS-T1", "Edge"): 1, ("AS-T1", "Full-contig"): 1,
        ("AS-T2", "Interior"): 1, ("AS-T2", "Edge"): 2, ("AS-T2", "Full-contig"): 0,
    }
    assert got == expected, f"sidecar values must match the plotted counts; got {got}"


def test_size_vs_rich_sidecar_matches_plotted_points(tmp_path):
    """A second previously-sidecar-less figure: one row per plotted (strain x BGC) point."""
    root = tmp_path / "runs"
    out = tmp_path / "figs"
    out.mkdir()
    sid = "AS-T1"
    pkg = str(root / sid / "package")
    _write_inventory(pkg, sid, ["Interior", "Interior"])
    # gene_by_gene file so load_genes finds the richness genes
    with open(os.path.join(pkg, f"{sid}_gene_by_gene_all_bgcs.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["bgc_id", "gene_function_inference", "length_bp",
                    "cds_start", "cds_end", "strand", "sec_met_domains"])
        # BGC001: 2 core-biosynthetic genes -> richness 2 ; BGC002: 0 functional -> richness 0
        w.writerow(["BGC001", "core biosynthetic", "900", "1", "900", "+", "KS"])
        w.writerow(["BGC001", "core biosynthetic", "900", "901", "1800", "+", "AT"])
        w.writerow(["BGC002", "biosynthetic context", "600", "1", "600", "+", ""])

    cfe.fig_size_vs_rich(str(root), [sid], str(out))
    sidecar = out / "fig3_size_vs_rich_data.csv"
    assert sidecar.exists()
    rows = list(csv.DictReader(open(sidecar, encoding="utf-8")))
    by_bgc = {r["bgc_id"]: int(r["functional_gene_richness"]) for r in rows}
    assert by_bgc == {"BGC001": 2, "BGC002": 0}
