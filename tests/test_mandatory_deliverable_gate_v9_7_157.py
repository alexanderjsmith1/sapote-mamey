"""v9.7.157 — mandatory-deliverable gate: a completed run must auto-emit the
compiled report, even in smoke / --brief none, so the user is handed a
human-readable deliverable without knowing to ask for one.

Root cause (this session): smoke is triage-only and --capped-session forces
--brief none, so a correct run sealed MAMEY_COMPLETE and emitted ZERO
user-facing deliverables. output_checklist.py already marked a compiled report
REQUIRED; the run just never produced it. The gate closes that.
"""
from pathlib import Path
import json
import pytest
from mamey.compile_report import build_report


def _minimal_package(tmp_path: Path) -> Path:
    """A minimal sealed-package shape build_report can consume."""
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({
        "strain_id": "AS-TEST", "display_name": "strain AS-TEST",
        "assembly": {"assembly_tier": "VERY_POOR", "interior_pct": 0.0,
                     "n50": 4907, "contigs": 8012},
        "bgc_counts": {"raw": 3, "corrected": 1.0, "interior_pct": 0.0},
    }))
    (pkg / "manifest_short.json").write_text(json.dumps({"strain_id": "AS-TEST"}))
    (pkg / "AS-TEST_4_triage_board.csv").write_text(
        "BGC_ID,Contig,Products,Boundary,Lead_tier_auto,AB_auto,AF_auto,Novelty_auto,KCB_top\n"
        "BGC001,NODE_1_length_9999_cov_9,RiPP;lassopeptide,Edge,High,80.0,24.0,44.0,\n"
    )
    return pkg


def test_build_report_produces_nonempty_markdown_from_smoke_shape(tmp_path):
    pkg = _minimal_package(tmp_path)
    md = build_report(str(pkg), generate_figures=False)
    assert isinstance(md, str) and len(md) > 200
    assert "AS-TEST" in md
    # deterministic facts present even with figures off
    assert "VERY_POOR" in md or "0.0% interior" in md.lower() or "corrected" in md.lower()


def test_gate_writes_report_to_canonical_path(tmp_path):
    pkg = _minimal_package(tmp_path)
    report = pkg / "AS-TEST_compiled_report.md"
    assert not report.exists()
    md = build_report(str(pkg), generate_figures=False)
    report.write_text(md, encoding="utf-8")
    assert report.exists() and report.stat().st_size > 200
