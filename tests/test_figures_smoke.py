"""test_figures_smoke.py — tests for mamey/figures_smoke.py.

Covers W2 Part B (v9.7.149b wishlist):
- each of the three figures writes a PNG with valid magic bytes
- companion sidecar CSV is written alongside each figure
- non-blocking when matplotlib absent
- non-blocking when triage CSV is malformed
- non-blocking when no source CSVs present

Fixtures use AS-XXX only.
"""
from __future__ import annotations

import pathlib
import sys

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _make_pkg(tmp_path: pathlib.Path,
              strain_id: str = "AS-XXX",
              *,
              with_inventory: bool = True,
              with_triage: bool = True,
              corrupt_triage: bool = False) -> pathlib.Path:
    """Build a minimal synthetic Mamey package with triage + inventory CSVs."""
    pkg = tmp_path / strain_id / "package"
    pkg.mkdir(parents=True)

    if with_triage:
        if corrupt_triage:
            (pkg / f"{strain_id}_4_triage_board.csv").write_text(
                "not\x00,a,valid\ncsv\nfile,really")
        else:
            rows = [
                "BGC_ID,Assembly_Locator,Products,Standing_rule,Corrected_rank",
                "BGC001,Interior,NRPS,,1",
                "BGC002,Edge,RiPP,,2",
                "BGC003,Interior,saccharide,saccharide-exclusion,3",
                "BGC004,Full-contig,NRPS; PKS,,4",
                "BGC005,Interior,terpene,,5",
                "BGC006,Edge,RiPP,,6",
            ]
            (pkg / f"{strain_id}_4_triage_board.csv").write_text(
                "\n".join(rows) + "\n")

    if with_inventory:
        rows = [
            "BGC_ID,Assembly_Locator,Length_kb,Products",
            "BGC001,Interior,42.1,NRPS",
            "BGC002,Edge,28.7,RiPP",
            "BGC003,Interior,18.2,saccharide",
            "BGC004,Full-contig,53.4,NRPS; PKS",
            "BGC005,Interior,31.0,terpene",
            "BGC006,Edge,22.5,RiPP",
        ]
        (pkg / f"{strain_id}_2_inventory.csv").write_text(
            "\n".join(rows) + "\n")

    return pkg


def _valid_png(path: pathlib.Path) -> bool:
    if not path.exists() or path.stat().st_size < 16:
        return False
    return path.read_bytes()[:8] == PNG_MAGIC


# ---------------------------------------------------------------------------
# Tests — Part B
# ---------------------------------------------------------------------------

def test_smoke_figures_generates_all_three_pngs(tmp_path):
    pytest.importorskip("matplotlib")
    from mamey.figures_smoke import generate
    pkg = _make_pkg(tmp_path)
    res = generate(pkg)
    files = set(res["files"])
    assert "fig_bgc_ranking.png" in files
    assert "fig_class_composition.png" in files
    assert "fig_assembly_tier.png" in files
    assert res["figures"] == 3


def test_smoke_figures_pngs_have_valid_magic_bytes(tmp_path):
    pytest.importorskip("matplotlib")
    from mamey.figures_smoke import generate
    pkg = _make_pkg(tmp_path)
    generate(pkg)
    out = pkg / "smoke_figures"
    for name in ("fig_bgc_ranking.png", "fig_class_composition.png",
                 "fig_assembly_tier.png"):
        assert _valid_png(out / name), f"bad PNG: {name}"


def test_smoke_figures_writes_sidecar_csvs(tmp_path):
    """Per the Developer or User's standing rule: data-only PNGs + companion fig_<id>_data.csv."""
    pytest.importorskip("matplotlib")
    from mamey.figures_smoke import generate
    pkg = _make_pkg(tmp_path)
    generate(pkg)
    out = pkg / "smoke_figures"
    for name in ("fig_bgc_ranking_data.csv", "fig_class_composition_data.csv",
                 "fig_assembly_tier_data.csv"):
        sidecar = out / name
        assert sidecar.exists(), f"missing sidecar: {name}"
        assert sidecar.read_text(encoding="utf-8").strip() != ""


def test_class_composition_excludes_standing_rule_rows(tmp_path):
    pytest.importorskip("matplotlib")
    from mamey.figures_smoke import generate
    pkg = _make_pkg(tmp_path)
    generate(pkg)
    sidecar = (pkg / "smoke_figures" / "fig_class_composition_data.csv"
               ).read_text()
    # BGC003 is standing-rule excluded with class 'saccharide' — must not appear
    assert "saccharide" not in sidecar
    assert "NRPS" in sidecar  # other classes still present


def test_bgc_ranking_orders_by_length_desc(tmp_path):
    pytest.importorskip("matplotlib")
    from mamey.figures_smoke import generate
    pkg = _make_pkg(tmp_path)
    generate(pkg)
    sidecar = (pkg / "smoke_figures" / "fig_bgc_ranking_data.csv"
               ).read_text().splitlines()
    # First data row should be BGC004 (53.4 kb — longest)
    first_data = sidecar[1]  # header is line 0
    assert first_data.startswith("BGC004"), f"got: {first_data}"


def test_non_blocking_when_matplotlib_absent(tmp_path, monkeypatch):
    """If matplotlib import fails the module returns an empty result, no raise."""
    from mamey import figures_smoke
    pkg = _make_pkg(tmp_path)
    monkeypatch.setattr(figures_smoke, "_import_matplotlib", lambda: None)
    res = figures_smoke.generate(pkg)
    assert res["figures"] == 0
    assert "matplotlib" in (res["skipped_reason"] or "")


def test_non_blocking_when_triage_csv_malformed(tmp_path):
    """A malformed triage CSV doesn't crash. With a valid inventory present,
    the length-ranking figure still emits via the inventory fallback."""
    pytest.importorskip("matplotlib")
    from mamey.figures_smoke import generate
    pkg = _make_pkg(tmp_path, corrupt_triage=True)
    res = generate(pkg)
    # Bare minimum: nothing raised
    assert res["figures"] >= 0
    # The bgc_ranking figure should still work (uses inventory for length)
    # The class_composition cannot (needs triage); assembly_tier should also
    # work since it falls back to inventory.
    # We assert non-zero — at least one figure made it.
    assert res["figures"] >= 1


def test_non_blocking_when_no_csvs_present(tmp_path):
    """Empty package — no triage, no inventory — should degrade silently."""
    pytest.importorskip("matplotlib")
    from mamey.figures_smoke import generate
    pkg = tmp_path / "AS-XXX" / "package"
    pkg.mkdir(parents=True)
    res = generate(pkg)
    assert res["figures"] == 0
    assert res["skipped_reason"] is not None


def test_smoke_figures_output_dir_is_smoke_figures(tmp_path):
    """The output dir name matters — compile_report and the wishlist both
    reference smoke_figures/ explicitly."""
    pytest.importorskip("matplotlib")
    from mamey.figures_smoke import generate
    pkg = _make_pkg(tmp_path)
    res = generate(pkg)
    assert res["out"].endswith("smoke_figures")
    assert (pkg / "smoke_figures").is_dir()
