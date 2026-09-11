"""Tests for the `mamey cohort` front-door (cohort_deliverable.py).

Focus: the mandatory-deliverable gate contract -- a cohort run must either emit at least
one human-readable deliverable (ok=True) or report failure (ok=False). We do not require a
full multi-strain master here; we assert the gate's behavior on the boundary cases.
"""
from pathlib import Path

import pytest

from mamey.cohort_deliverable import (
    run_cohort_deliverable, CohortDeliverableResult, _locate_master,
    _collect_engine_versions, _check_engine_uniformity,
)

_A2 = ["strain", "taxonomy", "ecology_source", "habitat", "n50", "bgc_count"]
_B1 = ["strain", "assembly_locator", "contig", "region", "BGC_ID", "start", "end",
       "length_kb", "products", "boundary", "arch", "kcb_top"]


def _build_master(path, versions):
    """A small but real cohort master (shipped headers) whose A3_Run_Manifest carries the given
    {strain: 'Mamey vX.Y.Z'} versions — used to exercise the COH-01 engine-uniformity gate."""
    import openpyxl
    wb = openpyxl.Workbook()
    reg = wb.active; reg.title = "A2_Strain_Registry"
    reg.append(_A2)
    for i, s in enumerate(versions):
        reg.append([s, "Streptomyces sp.", "Bombus terrestris", "nest", 400000, 2])
    b2 = wb.create_sheet("B2_Product_Class_Matrix")
    b2.append(["strain", "NRPS", "lassopeptide", "counts_reliability"])
    for i, s in enumerate(versions):
        b2.append([s, 1, 1 if i == 0 else 0, "ok"])
    b1 = wb.create_sheet("B1_BGC_Master")
    b1.append(_B1)
    for i, s in enumerate(versions):
        b1.append([s, "loc", "c1", "r1", f"{s}_BGC0001", 1, 2, 1.0, "NRPS", "complete", "high", ""])
        b1.append([s, "loc", "c1", "r2", f"{s}_BGC0002", 3, 4, 1.0, "NRPS", "complete", "high", "BGC0001234 | x"])
    a3 = wb.create_sheet("A3_Run_Manifest")
    a3.append(["run_date", "strain", "version"])
    for s, v in versions.items():
        a3.append(["2026-07-28", s, v])
    wb.save(path)


def test_missing_runs_dir_fails_gate(tmp_path):
    res = run_cohort_deliverable(runs_dir=tmp_path / "does_not_exist",
                                 out=tmp_path / "out", with_figures=False)
    assert isinstance(res, CohortDeliverableResult)
    assert res.ok is False
    assert res.deliverables == []
    assert any("does not exist" in w for w in res.warnings)


def test_empty_runs_dir_no_master_fails_gate(tmp_path):
    runs = tmp_path / "runs"; runs.mkdir()
    res = run_cohort_deliverable(runs_dir=runs, out=tmp_path / "out", with_figures=False)
    # no master -> no synthesis -> no figures requested -> zero deliverables -> gate fails
    assert res.ok is False
    assert any("master" in w for w in res.warnings)


def test_locate_master_prefers_explicit(tmp_path):
    runs = tmp_path / "runs"; runs.mkdir()
    explicit = tmp_path / "my_master.xlsx"; explicit.write_bytes(b"x")
    assert _locate_master(runs, str(explicit)) == explicit


def test_locate_master_explicit_missing_returns_none(tmp_path):
    runs = tmp_path / "runs"; runs.mkdir()
    assert _locate_master(runs, str(tmp_path / "nope.xlsx")) is None


def test_locate_master_autofinds_in_runs_dir(tmp_path):
    runs = tmp_path / "runs"; runs.mkdir()
    m = runs / "cohort_master.xlsx"; m.write_bytes(b"x")
    assert _locate_master(runs, None) == m


def test_ok_property_requires_synthesis_not_captions():
    """COH-03: the mandatory deliverable is the synthesis report, NOT figure captions. A result
    whose only 'deliverable' is captions must still be ok=False; ok flips True only once the
    CROSS_STRAIN_SYNTHESIS.md is actually written."""
    res = CohortDeliverableResult(out_dir=Path("."))
    assert res.ok is False
    # figure captions counting as "a deliverable" must NOT satisfy the promise
    res.deliverables.append(Path("figures/figure_captions.md"))
    assert res.ok is False
    # only the real synthesis report satisfies it
    res.synthesis_report = Path("CROSS_STRAIN_SYNTHESIS.md")
    res.deliverables.append(res.synthesis_report)
    assert res.ok is True


def test_ok_false_when_engine_mixed_even_with_synthesis():
    """COH-01: a written synthesis is still not ok if the cohort spans >1 scoring engine."""
    res = CohortDeliverableResult(out_dir=Path("."))
    res.synthesis_report = Path("CROSS_STRAIN_SYNTHESIS.md")
    res.deliverables.append(res.synthesis_report)
    assert res.ok is True
    res.engine_uniform = False
    assert res.ok is False


def test_collect_engine_versions_from_manifest(tmp_path):
    m = tmp_path / "master.xlsx"
    _build_master(m, {"AS-900": "Mamey v1.9.118", "AS-901": "Mamey v1.9.118"})
    vers = _collect_engine_versions(m)
    assert vers == {"AS-900": "Mamey v1.9.118", "AS-901": "Mamey v1.9.118"}


def test_engine_uniformity_gate_passes_and_fails(tmp_path):
    uni = tmp_path / "uni.xlsx"
    _build_master(uni, {"AS-900": "Mamey v1.9.118", "AS-901": "Mamey v1.9.118"})
    ok, banner = _check_engine_uniformity(uni)
    assert ok is True and banner is None

    mix = tmp_path / "mix.xlsx"
    _build_master(mix, {"AS-900": "Mamey v1.9.118", "AS-901": "Mamey v1.9.114"})
    ok, banner = _check_engine_uniformity(mix)
    assert ok is False and banner and "1.9.114" in banner


def test_cohort_deliverable_uniform_engine_ok(tmp_path):
    runs = tmp_path / "runs"; runs.mkdir()
    m = tmp_path / "master.xlsx"
    _build_master(m, {"AS-900": "Mamey v1.9.118", "AS-901": "Mamey v1.9.118"})
    res = run_cohort_deliverable(runs_dir=runs, out=tmp_path / "out",
                                 master_path=str(m), with_figures=False)
    assert res.engine_uniform is True
    assert res.synthesis_report is not None
    assert res.ok is True
    text = res.synthesis_report.read_text()
    assert "MIXED-ENGINE" not in text


def test_cohort_deliverable_mixed_engine_fails_gate_and_banners(tmp_path):
    """COH-01 end-to-end: a mixed-engine cohort still writes the synthesis (inspectable) but
    stamps a MIXED-ENGINE banner and fails the gate (ok=False, loud warning)."""
    runs = tmp_path / "runs"; runs.mkdir()
    m = tmp_path / "master.xlsx"
    _build_master(m, {"AS-900": "Mamey v1.9.118", "AS-901": "Mamey v1.9.114"})
    res = run_cohort_deliverable(runs_dir=runs, out=tmp_path / "out",
                                 master_path=str(m), with_figures=False)
    assert res.engine_uniform is False
    assert res.ok is False
    assert any("MIXED-ENGINE" in w for w in res.warnings)
    assert res.synthesis_report is not None            # still emitted for inspection
    assert "MIXED-ENGINE COHORT" in res.synthesis_report.read_text()
