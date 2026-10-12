"""Source-owned functional evidence is present in standalone analytical output."""
import copy
import zipfile

import pytest
from rggmci import run, core
from rggmci._functional_profiles import functional_profile_from_gene_context, modular_profile_from_gene_context


def test_pure_profile_counts_and_per_cds_modular_counts():
    rows = {"BGC001": [{"gene_kind": "biosynthetic", "sec_met_domains": ["Condensation", "Condensation_subtype"]}],
            "BGC002": [{"gene_kind": "regulatory", "sec_met_domains": ["ACP", "Thioesterase"]}]}
    assert functional_profile_from_gene_context(rows)["BGC001"]["roles_present"] == ["core"]
    assert functional_profile_from_gene_context(rows)["BGC002"]["roles_present"] == ["regulatory"]
    assert modular_profile_from_gene_context(rows) == {
        "BGC001": {"assembly_line_cds": 1, "release_cds": 0},
        "BGC002": {"assembly_line_cds": 1, "release_cds": 1}}


def test_public_run_empty_context_is_recorded_not_hidden(tmp_path):
    path = tmp_path / "metadata.zip"
    with zipfile.ZipFile(path, "x") as archive: archive.writestr("metadata.txt", "no features supplied")
    result = run(path, reference_completion="off")
    assert result["functional_profiles"] == result["modular_profiles"] == {}
    assert result["functional_context"]["n_cds"] == 0
    assert result["functional_context"]["input_sha256"] == result["input"]["antismash_zip_sha256"]
    assert result["schema"] == "rggmci-shared-invocation-v3"


def test_pair_views_have_exact_missing_context_defaults_without_aliasing():
    expected = {"functional_rescue_class": "UNKNOWN_NO_PROFILE", "a_core_fraction": None,
                "b_core_fraction": None, "a_functional_roles": "", "b_functional_roles": "",
                "modular_continuation": "UNKNOWN_NO_PROFILE", "a_assembly_line_cds": "",
                "b_assembly_line_cds": "", "a_release_cds": "", "b_release_cds": ""}
    pair = {"bgc_a": "BGC001", "bgc_b": "BGC002"}
    other = copy.deepcopy(pair)
    core._annotate_functional_pair(pair, {}, {})
    core._annotate_functional_pair(other, {}, {})
    assert {k: pair[k] for k in expected} == expected
    assert {k: other[k] for k in expected} == expected
    assert pair is not other


def test_context_extraction_error_is_not_success(tmp_path, monkeypatch):
    path = tmp_path / "metadata.zip"
    with zipfile.ZipFile(path, "x") as archive: archive.writestr("metadata.txt", "no features supplied")
    def fail(*args): raise RuntimeError("declared extraction failure")
    monkeypatch.setattr(core, "extract_domain_features", fail)
    with pytest.raises(RuntimeError, match="declared extraction failure"):
        run(path, reference_completion="off")
