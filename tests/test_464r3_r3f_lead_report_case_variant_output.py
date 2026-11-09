"""The activity-lead report refuses an output that is a case variant of an input tree.

Default APFS is case-insensitive: ``RUNS/STRAIN_A/package/REPORT`` names the same directory as
``Runs/STRAIN_A/package/REPORT``. The containment check compares existing ancestors by device
and inode, so the case variant is refused instead of writing into the sealed package.
Synthetic fixtures only.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.test_render_activity_lead_reports_v97405 import R, _triage_row, _write_package
from mamey.activity_lead_report import run as leads_run


def _case_insensitive(path: Path) -> bool:
    probe = path / "CaseProbe"
    probe.mkdir()
    try:
        return (path / "caseprobe").exists()
    finally:
        probe.rmdir()


@pytest.fixture
def cohort(tmp_path):
    if not _case_insensitive(tmp_path):
        pytest.skip("this filesystem is case-sensitive; the case variant is a different path")
    runs = tmp_path / "Runs"
    _write_package(runs, "STRAIN_A",
                   [_triage_row("BGC020", "C2", "region001", 40, 30, products="terpene", boundary="Edge")],
                   genome_bp=6_100_000, contigs=930, n50=2_800)
    leads = tmp_path / "leads"
    leads_run(str(runs), str(leads), top_n=5)
    return tmp_path, runs, leads


@pytest.mark.parametrize("variant", [("RUNS", "STRAIN_A", "package", "REPORT"), ("LEADS", "REPORT")])
def test_case_variant_of_an_input_tree_is_refused(cohort, variant):
    tmp_path, runs, leads = cohort
    before = sorted(str(p) for p in tmp_path.rglob("*"))
    with pytest.raises(ValueError, match="inside input tree"):
        R.render(str(runs), str(leads), str(tmp_path.joinpath(*variant)), fmt="markdown")
    assert sorted(str(p) for p in tmp_path.rglob("*")) == before


def test_output_beside_the_inputs_is_still_written(cohort):
    tmp_path, runs, leads = cohort
    result = R.render(str(runs), str(leads), str(tmp_path / "reports" / "REPORT"), fmt="markdown")
    md = Path(result["markdown_path"]).read_text(encoding="utf-8")
    assert "## Contig-boundary tiers" in md
    assert "contig-boundary record" in md
    assert "Assembly-quality tiers" not in md and "assembly-quality record" not in md


def test_missing_root_is_compared_by_folded_name(tmp_path, monkeypatch):
    monkeypatch.setattr(R.sys, "platform", "darwin")
    assert R._same_or_inside(tmp_path / "NoSuch" / "x", tmp_path / "nosuch")
    assert not R._same_or_inside(tmp_path / "other" / "x", tmp_path / "nosuch")
