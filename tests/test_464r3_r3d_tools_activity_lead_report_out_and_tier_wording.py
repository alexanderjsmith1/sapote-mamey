"""Activity-lead report: outputs stay outside the input trees, are never replaced, and the
boundary-derived tier is described as boundary counts, not assembly reliability."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey.activity_lead_report import run as leads_run  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load("render_activity_lead_reports_r3d", ROOT / "tools" / "render_activity_lead_reports.py")
H = _load("render_activity_lead_reports_r3d_helpers",
          ROOT / "tests" / "test_render_activity_lead_reports_v97405.py")


@pytest.fixture
def cohort(tmp_path):
    runs = tmp_path / "runs"
    H._write_package(runs, "STRAIN_A", [
        H._triage_row("BGC020", "C2", "region001", 40, 30, products="terpene", boundary="Edge"),
        H._triage_row("BGC021", "C2", "region002", 20, 25, products="terpene", boundary="Edge"),
    ], genome_bp=6_100_000, contigs=930, n50=2_800)
    leads = tmp_path / "leads"
    leads_run(str(runs), str(leads), top_n=5)
    return runs, leads


def test_output_inside_a_package_is_refused(tmp_path, cohort):
    runs, leads = cohort
    package = runs / "STRAIN_A" / "package"
    before = sorted(p.name for p in package.iterdir())
    for stem in (package / "REPORT", leads / "REPORT"):
        with pytest.raises(ValueError, match="inside input tree"):
            R.render(str(runs), str(leads), str(stem), fmt="markdown")
    assert sorted(p.name for p in package.iterdir()) == before
    assert not (leads / "REPORT.md").exists()


def test_existing_markdown_is_not_replaced(tmp_path, cohort):
    runs, leads = cohort
    out = tmp_path / "out"
    out.mkdir()
    (out / "REPORT.md").write_text("kept\n")
    with pytest.raises(ValueError):
        R.render(str(runs), str(leads), str(out / "REPORT"), fmt="markdown")
    assert (out / "REPORT.md").read_text() == "kept\n"


def test_cli_reports_a_refused_output(tmp_path, cohort):
    runs, leads = cohort
    with pytest.raises(SystemExit) as stop:
        R.main(["--runs-dir", str(runs), "--leads-dir", str(leads),
                "--out", str(runs / "REPORT"), "--format", "markdown"])
    assert stop.value.code == 2


def test_tier_wording_is_boundary_only(tmp_path, cohort):
    runs, leads = cohort
    result = R.render(str(runs), str(leads), str(tmp_path / "fresh" / "REPORT"), fmt="markdown")
    text = Path(result["markdown_path"]).read_text().lower()
    for phrase in ("reliable assembly", "long-read sequencing", "assembly is unreliable",
                   "correction strongly recommended", "urgent", "counts are reliable"):
        assert phrase not in text, phrase
    assert "boundary tier very_poor" in text
    assert "does not measure assembly contiguity" in text
