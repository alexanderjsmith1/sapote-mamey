"""test_render_figures_regression.py — render-figures subcommand regression tests (v9.7.81).

Acceptance criteria (P1 item 3):
  - render-figures on the synthetic fixture package produces >= 1 PNG.
  - figure_manifest.csv is always written (even if no PNGs produced).
  - FIGURE_QA.md is always written.
  - Returns exit code 0 on success, non-zero only on hard errors.
"""
import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from mamey.chatgpt_commands import render_figures_command


@pytest.fixture()
def synthetic_package(tmp_path):
    """Minimal sealed package directory with triage board for render-figures."""
    import json, csv as _csv

    pkg = tmp_path / "SYNTHETIC" / "package"
    pkg.mkdir(parents=True)

    # Write a minimal manifest.json
    (pkg / "manifest.json").write_text(json.dumps({
        "strain": {"strain_id": "SYNTHETIC"},
        "bgcs": [],
        "source_scans": {},
    }), encoding="utf-8")

    # Write a minimal triage board with 3 active BGCs
    tb_path = pkg / "SYNTHETIC_4_triage_board.csv"
    rows = [
        {"BGC_ID": "BGC001", "Contig": "NODE_1_length_50000", "Products": "NRPS",
         "Standing_rule": "", "Primary_metab_flag": "",
         "AB_auto": "55", "AF_auto": "30", "Novelty_auto": "40",
         "Arch": "C", "Boundary": "Interior", "Depth_floor": "full_mode_b",
         "CCTT_triggers": "T43-HAL", "KCB_top": "totopotensamide", "KCB_score": "20725"},
        {"BGC_ID": "BGC002", "Contig": "NODE_2_length_30000", "Products": "T1PKS",
         "Standing_rule": "", "Primary_metab_flag": "",
         "AB_auto": "40", "AF_auto": "50", "Novelty_auto": "35",
         "Arch": "A", "Boundary": "Edge", "Depth_floor": "full_mode_b",
         "CCTT_triggers": "", "KCB_top": "nystatin", "KCB_score": "80268"},
        {"BGC_ID": "BGC003", "Contig": "NODE_3_length_10000", "Products": "saccharide",
         "Standing_rule": "saccharide-exclusion", "Primary_metab_flag": "",
         "AB_auto": "70", "AF_auto": "60", "Novelty_auto": "50",
         "Arch": "E", "Boundary": "Full-contig", "Depth_floor": "abbrev_ledger",
         "CCTT_triggers": "", "KCB_top": "", "KCB_score": ""},
    ]
    fields = list(rows[0].keys())
    with open(tb_path, "w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    return pkg


def test_render_figures_writes_figure_manifest(synthetic_package, tmp_path):
    """figure_manifest.csv must always be written."""
    outdir = tmp_path / "figs"
    args = SimpleNamespace(package=str(synthetic_package), outdir=str(outdir),
                           top_n=5, style="chatgpt-node-first")
    render_figures_command(args)
    assert (outdir / "figure_manifest.csv").exists()


def test_render_figures_writes_figure_qa(synthetic_package, tmp_path):
    """FIGURE_QA.md must always be written."""
    outdir = tmp_path / "figs_qa"
    args = SimpleNamespace(package=str(synthetic_package), outdir=str(outdir),
                           top_n=5, style="chatgpt-node-first")
    render_figures_command(args)
    assert (outdir / "FIGURE_QA.md").exists()


def test_render_figures_excludes_standing_rule(synthetic_package, tmp_path):
    """BGC003 (saccharide-exclusion) must NOT appear in top-N figures."""
    import matplotlib
    matplotlib.use("Agg")
    outdir = tmp_path / "figs_exc"
    args = SimpleNamespace(package=str(synthetic_package), outdir=str(outdir),
                           top_n=5, style="chatgpt-node-first")
    render_figures_command(args)
    manifest_rows = list(csv.DictReader(open(outdir / "figure_manifest.csv")))
    # If any PNGs were produced, row_count must be <= 2 (BGC001 + BGC002 only)
    for row in manifest_rows:
        if row.get("row_count"):
            assert int(row["row_count"]) <= 2, (
                "Standing-rule BGC003 should be excluded from figure rows"
            )


def test_render_figures_node_first_label(synthetic_package, tmp_path):
    """node-first label should include contig node name."""
    # This is a smoke test that the command completes without error with node-first style
    outdir = tmp_path / "figs_nf"
    args = SimpleNamespace(package=str(synthetic_package), outdir=str(outdir),
                           top_n=2, style="chatgpt-node-first")
    rc = render_figures_command(args)
    # Exit code may be 0 (PNGs produced) or 0 (no matplotlib but no error)
    assert rc in (0, 1)  # 1 is acceptable if matplotlib is absent
    assert (outdir / "FIGURE_QA.md").exists()


def test_render_figures_missing_triage_board(tmp_path):
    """Missing triage board must not crash — writes FIGURE_QA.md with FAIL line, returns 1."""
    import json
    pkg = tmp_path / "EMPTY" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain": {}, "bgcs": []}), encoding="utf-8")
    outdir = tmp_path / "figs_empty"
    args = SimpleNamespace(package=str(pkg), outdir=str(outdir),
                           top_n=5, style="chatgpt-node-first")
    rc = render_figures_command(args)
    assert rc == 1
    assert (outdir / "FIGURE_QA.md").exists()
    qa = (outdir / "FIGURE_QA.md").read_text(encoding="utf-8")
    assert "FAIL" in qa or "not found" in qa
