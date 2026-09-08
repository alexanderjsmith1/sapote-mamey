"""Cohort evidence admission must distinguish unknown from measured absence."""
import csv
from pathlib import Path
import pytest
from mamey import mibig_comparator_coverage as mcc


def write_profile(root, strain, text="mibig_accession\nREF_TEST\n"):
    package = root / strain / "package"
    package.mkdir(parents=True, exist_ok=True)
    path = package / f"{strain}_3_mibig_per_gene.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_focal_noncarrier_excluded_from_denominator(tmp_path):
    write_profile(tmp_path, "FOCAL", "mibig_accession\n")
    write_profile(tmp_path, "OTHER_A")
    write_profile(tmp_path, "OTHER_B")
    write_profile(tmp_path, "OTHER_C", "mibig_accession\n")
    cp = mcc.compute_cohort_prevalence(tmp_path)["REF_TEST"]
    actual = mcc.assess_cohort_prevalence(cp, focal_strain="FOCAL")
    assert actual["cohort_prevalence"] == "2/3"
    assert actual["cohort_prevalence_basis"] == "other_strains_focal_excluded"


@pytest.mark.parametrize("kind", ["wrong_schema", "empty", "duplicate_header", "ragged", "malformed", "duplicate_files", "unreadable", "invalid_utf8"])
def test_invalid_evidence_excluded_from_denominator(tmp_path, monkeypatch, kind):
    write_profile(tmp_path, "VALID")
    bad = write_profile(tmp_path, "UNKNOWN")
    content = {
        "wrong_schema": "wrong_column\nvalue\n",
        "empty": "",
        "duplicate_header": "mibig_accession,mibig_accession\nREF_TEST,REF_TEST\n",
        "ragged": "mibig_accession,extra\nREF_TEST\n",
        "malformed": 'mibig_accession\n"unterminated\n',
    }
    if kind in content:
        bad.write_text(content[kind])
    elif kind == "duplicate_files":
        (bad.parent / "other_3_mibig_per_gene.csv").write_text("mibig_accession\nREF_TEST\n")
    elif kind == "invalid_utf8":
        bad.write_bytes(b"mibig_accession\n\xff\n")
    elif kind == "unreadable":
        original = __import__("builtins").open
        def denied(path, *args, **kwargs):
            if Path(path) == bad:
                raise PermissionError("fixture denied")
            return original(path, *args, **kwargs)
        monkeypatch.setattr("builtins.open", denied)
    cp = mcc.compute_cohort_prevalence(tmp_path)["REF_TEST"]
    assert cp["total"] == 1
    assert cp["strains"] == 1
    assert cp["cohort_strain_ids"] == ["VALID"]
    assert "UNKNOWN" in cp["unassessed_strains"]


def test_header_only_is_assessed_noncarrier(tmp_path):
    write_profile(tmp_path, "CARRIER")
    write_profile(tmp_path, "NONCARRIER", "mibig_accession\n")
    cp = mcc.compute_cohort_prevalence(tmp_path)["REF_TEST"]
    assert cp["strains"] == 1
    assert cp["total"] == 2


@pytest.mark.parametrize("update", [
    {"strains": -1}, {"strains": 5}, {"strains": 1.5},
    {"total": float("inf")}, {"total": True},
    {"strain_ids": ["A", "A"]}, {"strain_ids": "AB"},
    {"strain_ids": ["A", "Z"]}, {"cohort_strain_ids": ["A", "B"]},
])
def test_invalid_external_record_unassessed(update):
    cp = {"strains": 2, "total": 4, "strain_ids": ["A", "B"],
          "cohort_strain_ids": ["A", "B", "C", "D"]}
    cp.update(update)
    out = mcc.assess_cohort_prevalence(cp, focal_strain="A")
    assert out["cohort_prevalence_flag"] == "NOT_COMPUTED"
    assert out["cohort_prevalence"] == ""
    assert out["cohort_prevalence_basis"] == "invalid_cohort_record"


def test_legacy_noncarrier_membership_unknown():
    out = mcc.assess_cohort_prevalence(
        {"strains": 2, "total": 4, "strain_ids": ["A", "B"]},
        focal_strain="FOCAL")
    assert out["cohort_prevalence_flag"] == "NOT_COMPUTED"
    assert out["cohort_prevalence_basis"] == "focal_membership_unknown"


@pytest.mark.parametrize("kind", ["invalid", "missing", "zero_hits"])
def test_empty_result_preserves_cohort_diagnostics(tmp_path, kind):
    path = write_profile(tmp_path, "SAMPLE", "mibig_accession\n" if kind == "zero_hits" else "wrong_header\n")
    if kind == "missing":
        path.unlink()
    diagnostics = {}
    assert mcc.compute_cohort_prevalence(tmp_path, diagnostics=diagnostics) == {}
    assert diagnostics["assessed_strain_count"] == (1 if kind == "zero_hits" else 0)
    assert diagnostics["status"] == ("ASSESSED" if kind == "zero_hits" else "NO_ASSESSED_STRAINS")
    assert bool(diagnostics["unassessed_strains"]) == (kind != "zero_hits")


def test_package_summary_preserves_cohort_admission(tmp_path):
    import json
    path = write_profile(tmp_path, "FOCAL", "mibig_accession\n")
    write_profile(tmp_path, "UNKNOWN", "wrong_header\n")
    result = mcc.run_for_package(path.parent, cohort_runs_dir=tmp_path)
    summary = json.loads(Path(result["_written"]["summary_json"]).read_text())
    admission = summary["summary"]["cohort_evidence_admission"]
    assert admission["status"] == "PARTIALLY_ASSESSED"
    assert admission["assessed_strain_ids"] == ["FOCAL"]
    assert "UNKNOWN" in admission["unassessed_strains"]
