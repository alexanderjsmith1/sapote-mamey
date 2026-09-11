"""Focused contract checks for the F13 source-artwork candidate.

The fixtures are deliberately generic and only exercise the F13 consumer; they
do not select a scientific cohort or accept a scientific figure.
"""
import csv
import hashlib
import json

import pytest


pytest.importorskip("matplotlib")

from mamey import cohort_figures as figures


def _write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _package(root, strain, *, node="NODE_0001", region="region001", counts=None):
    package = root / strain / "package"
    package.mkdir(parents=True)
    _write_json(package / "manifest.json", {
        "strain_id": strain,
        "workflow_version": "1.9.99",
        "bgcs": [{
            "bgc_id": "BGC001",
            "node_id": node,
            "antismash_region": region,
        }],
    })
    _write_json(package / f"{strain}_1_intake.json", {
        "strain_id": strain,
        "antismash_version": "8.0.1",
    })
    _write_json(package / "gene_data.json", {
        "domain_arch": [{
            "sid": strain,
            "bgc_id": "BGC001",
            "architecture": str({"domain_counts": counts or {"PKS_KS": 1}}),
        }],
    })
    return {"pkg": str(package)}


def _cohort_manifest(path):
    rows = [
        {"identity": "SYN-01", "role": "STUDY", "include_by_default": True,
         "genus": "Streptomyces", "cohort": "BEE", "assembly_state": "PASS",
         "assembly_reason": "generic fixture passed"},
        {"identity": "SYN-02", "role": "STUDY", "include_by_default": True,
         "genus": "Streptomyces", "cohort": "WASP", "assembly_state": "PASS",
         "assembly_reason": "generic fixture passed"},
        {"identity": "AS-815", "role": "STUDY", "include_by_default": False,
         "genus": "Streptomyces", "cohort": "BEE", "assembly_state": "DEFAULT_OFF",
         "assembly_reason": "assembly quality is not bound"},
        {"identity": "AJS-001", "role": "EXTERNAL_BENCHMARK", "include_by_default": False,
         "genus": "Streptomyces", "cohort": "EXTERNAL_BENCHMARK", "assembly_state": "PASS",
         "assembly_reason": "external default-off fixture"},
    ]
    _write_json(path, {
        "schema_version": "sapote-mamey.figure-cohort-manifest.v1",
        "denominator_scope": "GOVERNED",
        "rows": rows,
    })
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _denominator_registry(path, *, strains=2, regions=2):
    _write_json(path, {
        "schema_version": "sapote-mamey.cohort-denominator-registry.v1",
        "scopes": [
            {"scope": "GOVERNED", "strains": strains, "regions": regions},
            {"scope": "ALL_PACKAGES", "strains": 3, "regions": 3},
            {"scope": "AS_COMPARISON_SET", "strains": 4, "regions": 4},
        ],
    })
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_f13_holds_without_a_hash_bound_cohort_manifest(tmp_path):
    source = {"SYN-01": _package(tmp_path, "SYN-01"), "SYN-02": _package(tmp_path, "SYN-02")}
    output = tmp_path / "missing-binding"

    result = figures._render_f13_domain_pca(source, ["SYN-01", "SYN-02"], output)

    assert result["status"] == "HOLD"
    assert result["code"] == "F13_COHORT_BINDING_REQUIRED"
    assert (output / "F13_bgc_domain_pca_2d_HOLD.json").is_file()
    assert not (output / "F13_bgc_domain_pca_2d.svg").exists()


def test_f13_emits_live_text_svg_and_complete_sidecars_only_for_default_study_rows(tmp_path):
    source = {
        "SYN-01": _package(tmp_path, "SYN-01", counts={"PKS_KS": 3, "NRPS_A": 1}),
        "SYN-02": _package(tmp_path, "SYN-02", counts={"PKS_AT": 2, "NRPS_C": 4}),
    }
    cohort_path = tmp_path / "cohort.json"
    digest = _cohort_manifest(cohort_path)
    denominator_path = tmp_path / "denominators.json"
    denominator_digest = _denominator_registry(denominator_path)
    output = tmp_path / "valid"

    result = figures._render_f13_domain_pca(
        source, ["SYN-01", "SYN-02", "AS-815", "AJS-001"], output,
        cohort_manifest=cohort_path, cohort_manifest_sha256=digest,
        denominator_registry=denominator_path,
        denominator_registry_sha256=denominator_digest,
    )

    assert result["status"] == "PASS_SOURCE_ARTWORK_ONLY"
    svg = output / "F13_bgc_domain_pca_2d.svg"
    assert svg.is_file()
    svg_text = svg.read_text(encoding="utf-8")
    assert "<text" in svg_text
    assert "<image" not in svg_text
    with (output / "F13_bgc_domain_pca_2d_plotdata.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["strain"] for row in rows} == {"SYN-01", "SYN-02"}
    assert all(row["node_or_contig"] and row["region"] and row["bgc_alias"] for row in rows)
    assert "raw_PKS_KS" in rows[0]
    assert "log1p_PKS_KS" in rows[0]
    caption = json.loads((output / "F13_bgc_domain_pca_2d_caption_methods.json").read_text())
    assert "default_off=true" in caption["benchmark_sensitivity"]
    assert (output / "F13_bgc_domain_pca_2d_owner_notes.json").is_file()
    provenance = json.loads((output / "F13_bgc_domain_pca_2d_provenance.json").read_text())
    assert set(provenance["pca"]["loadings"]) == {"PC1", "PC2"}
    assert provenance["denominator_policy"]["scope"] == "GOVERNED"
    assert provenance["denominator_policy"]["regions"] == 2
    assert {row["identity"] for row in provenance["excluded_default_off_or_nonstudy_identities"]} == {"AS-815", "AJS-001"}


def test_f13_holds_when_any_selected_bgc_lacks_a_complete_node_identity(tmp_path):
    source = {
        "SYN-01": _package(tmp_path, "SYN-01", node="", counts={"PKS_KS": 1}),
        "SYN-02": _package(tmp_path, "SYN-02", counts={"NRPS_A": 2}),
    }
    cohort_path = tmp_path / "cohort.json"
    digest = _cohort_manifest(cohort_path)
    denominator_path = tmp_path / "denominators.json"
    denominator_digest = _denominator_registry(denominator_path)
    output = tmp_path / "incomplete-identity"

    result = figures._render_f13_domain_pca(
        source, ["SYN-01", "SYN-02", "AS-815", "AJS-001"], output,
        cohort_manifest=cohort_path, cohort_manifest_sha256=digest,
        denominator_registry=denominator_path,
        denominator_registry_sha256=denominator_digest,
    )

    assert result["status"] == "HOLD"
    assert result["code"] == "F13_EXACT_LOCUS_IDENTITY_INCOMPLETE"
    assert not (output / "F13_bgc_domain_pca_2d.svg").exists()


def test_f13_holds_when_observed_denominator_is_not_governed(tmp_path):
    source = {
        "SYN-01": _package(tmp_path, "SYN-01", counts={"PKS_KS": 3}),
        "SYN-02": _package(tmp_path, "SYN-02", counts={"NRPS_A": 2}),
    }
    cohort_path = tmp_path / "cohort.json"
    cohort_digest = _cohort_manifest(cohort_path)
    denominator_path = tmp_path / "denominators.json"
    denominator_digest = _denominator_registry(denominator_path, strains=2, regions=3)
    output = tmp_path / "ungoverned-denominator"

    result = figures._render_f13_domain_pca(
        source, ["SYN-01", "SYN-02", "AS-815", "AJS-001"], output,
        cohort_manifest=cohort_path, cohort_manifest_sha256=cohort_digest,
        denominator_registry=denominator_path,
        denominator_registry_sha256=denominator_digest,
    )

    assert result["status"] == "HOLD"
    assert result["code"] == "DENOMINATOR_UNGOVERNED"
    hold = json.loads((output / "F13_bgc_domain_pca_2d_HOLD.json").read_text())
    assert hold["denominator_registry_filename"] == "denominators.json"
    assert not (output / "F13_bgc_domain_pca_2d.svg").exists()


def test_f13_holds_when_denominator_registry_is_unbound(tmp_path):
    source = {
        "SYN-01": _package(tmp_path, "SYN-01", counts={"PKS_KS": 3}),
        "SYN-02": _package(tmp_path, "SYN-02", counts={"NRPS_A": 2}),
    }
    cohort_path = tmp_path / "cohort.json"
    cohort_digest = _cohort_manifest(cohort_path)
    output = tmp_path / "unbound-denominator"

    result = figures._render_f13_domain_pca(
        source, ["SYN-01", "SYN-02", "AS-815", "AJS-001"], output,
        cohort_manifest=cohort_path, cohort_manifest_sha256=cohort_digest,
    )

    assert result["status"] == "HOLD"
    assert result["code"] == "DENOMINATOR_UNGOVERNED"
    assert not (output / "F13_bgc_domain_pca_2d.svg").exists()
