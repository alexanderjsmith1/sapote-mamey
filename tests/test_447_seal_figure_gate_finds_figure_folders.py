"""mamey/seal_package.py figure gates read the figure folders and keep paths in report links.

fresh-clone audit, 2026-10-01 (D2): the gate globbed only the package root for *fig*.png and stripped the
folder from report links, so a pristine package reported "0 figures, 22 issues" and "figures: absent" although every
figure existed in gold_figures/, smoke_figures/ or locus_maps/. A pristine package could never seal PASS.
"""
from pathlib import Path

from mamey import seal_package as sp

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def _fig(path: Path, data=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG)
    if data:
        path.with_name(path.stem + "_data.csv").write_text("x\n1\n")


def _pkg(tmp_path):
    pkg = tmp_path / "package"
    _fig(pkg / "gold_figures" / "D01_bubble.png")
    _fig(pkg / "smoke_figures" / "fig_bgc_ranking.png")
    _fig(pkg / "locus_maps" / "BGC009_locus_map.png")
    (pkg / "S_compiled_report.md").write_text(
        "![D01](gold_figures/D01_bubble.png)\n![map](locus_maps/BGC009_locus_map.png)\n"
        "See fig_bgc_ranking.png and https://example.org/logo.png.\n")
    return pkg


def test_figures_in_their_folders_are_found_and_referenced_paths_resolve(tmp_path):
    r = sp._gate_figure_references(_pkg(tmp_path))
    assert r.status == "PASS", r.findings
    assert r.detail.startswith("3 figures")


def test_a_genuinely_missing_figure_still_warns_with_its_path(tmp_path):
    pkg = _pkg(tmp_path)
    (pkg / "S_compiled_report.md").write_text("![gone](gold_figures/D99_missing.png)\n")
    r = sp._gate_figure_references(pkg)
    assert r.status == "WARN"
    assert any("references missing figure gold_figures/D99_missing.png" in f["detail"] for f in r.findings)


def test_a_folder_path_is_not_satisfied_by_a_same_name_file_elsewhere(tmp_path):
    pkg = _pkg(tmp_path)
    (pkg / "S_compiled_report.md").write_text("![wrong folder](figures/D01_bubble.png)\n")
    assert sp._gate_figure_references(pkg).status == "WARN"


def test_a_figure_without_its_data_csv_warns_with_its_folder(tmp_path):
    pkg = _pkg(tmp_path)
    _fig(pkg / "gold_figures" / "D03_scatter.png", data=False)
    r = sp._gate_figure_references(pkg)
    assert any(f["detail"] == "gold_figures/D03_scatter.png: missing companion D03_scatter_data.csv" for f in r.findings)


def test_deliverable_status_sees_figures_in_folders(tmp_path):
    d = sp._gate_deliverable_status(_pkg(tmp_path), [])
    details = [f["detail"] for f in d.findings]
    assert "figures: present" in details and "figure_data_csvs: present" in details
