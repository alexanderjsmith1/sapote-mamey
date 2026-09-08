"""Regression tests for manifest_short.json (F1/F2 fix).

Before the fix, manifest_short.json was generated using an undefined name
`triage_records` (a NameError caught silently by the surrounding try/except),
so it either wrote an empty/wrong file or was skipped entirely with a [WARN].

v9.7.141 pytest hygiene: run the synthetic gold fixture once per module. Repeating
this fixture for every assertion made the full suite vulnerable to ChatGPT/tool
wall-clock limits without increasing coverage.
"""
import json
import pathlib

import pytest

from mamey.cli import run_one_strain

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SYNTH    = FIXTURES / "synthetic_single_contig_antismash.zip"


@pytest.fixture(scope="module")
def manifest_run(tmp_path_factory, synthetic_single_contig_full_locus_zip):
    outdir = tmp_path_factory.mktemp("manifest_short")
    res = run_one_strain(
        strain_id="MS_TEST", display_name="MS_TEST",
        input_zip=str(synthetic_single_contig_full_locus_zip), outdir=str(outdir), mode="gold",
        taxonomy="Streptomyces sp.", source="test", bioactivity="",
        master_path=None, json_mode="bounded",
    )
    pkg = pathlib.Path(outdir) / "MS_TEST" / "package"
    ms_path = pkg / "manifest_short.json"
    ms = json.loads(ms_path.read_text()) if ms_path.exists() else {}
    return {"res": res, "pkg": pkg, "ms_path": ms_path, "ms": ms}


def test_manifest_short_is_produced(manifest_run):
    """manifest_short.json must exist after a successful run."""
    assert manifest_run["ms_path"].exists(), "manifest_short.json was not written"


def test_manifest_short_no_warn_in_issues(manifest_run):
    """The [WARN] manifest_short.json skipped message must NOT appear in issues (was the F1/F2 symptom)."""
    skipped_warns = [i for i in manifest_run["res"].get("issues", []) if "manifest_short.json skipped" in i]
    assert not skipped_warns, f"manifest_short.json was skipped: {skipped_warns}"


def test_manifest_short_required_keys(manifest_run):
    """manifest_short.json must contain all required top-level keys with correct types."""
    ms = manifest_run["ms"]

    required = {
        "strain_id":        str,
        "mamey_version":    str,
        "status":           str,
        "assembly_tier":    str,
        "raw_bgcs":         int,
        "corrected_bgcs":   (int, float),
        "interior_pct":     (int, float, type(None)),
        "top_3_ab":         list,
        "top_3_af":         list,
        "phase_receipts_path": str,
        "timing_json":      str,
        "gene_by_gene_csv": str,
    }
    for key, expected_type in required.items():
        assert key in ms, f"missing key: {key}"
        assert isinstance(ms[key], expected_type), (
            f"{key}: expected {expected_type}, got {type(ms[key])} = {ms[key]!r}"
        )


def test_manifest_short_top_leads_structure(manifest_run):
    """Each entry in top_3_ab and top_3_af must have bgc_id, contig, and a numeric score."""
    ms = manifest_run["ms"]

    for field, score_key in [("top_3_ab", "ab_score"), ("top_3_af", "af_score")]:
        entries = ms[field]
        assert isinstance(entries, list), f"{field} must be a list"
        for entry in entries:
            assert "bgc_id"  in entry, f"{field} entry missing bgc_id: {entry}"
            assert "contig"  in entry, f"{field} entry missing contig: {entry}"
            assert score_key in entry, f"{field} entry missing {score_key}: {entry}"
            assert isinstance(entry[score_key], (int, float)), (
                f"{field} entry {score_key} must be numeric: {entry}"
            )


def test_manifest_short_strain_id_matches(manifest_run):
    """manifest_short.json strain_id must match the run's strain_id."""
    assert manifest_run["ms"]["strain_id"] == "MS_TEST"


def test_manifest_short_status_is_valid(manifest_run):
    """manifest_short.json status must be a recognised Mamey status string."""
    valid_statuses = {
        "MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES", "VALIDATION_FAIL",
        "PASS", "PASS_WITH_ISSUES", "FAIL",
    }
    assert manifest_run["ms"]["status"] in valid_statuses, f"unexpected status: {manifest_run['ms']['status']!r}"
