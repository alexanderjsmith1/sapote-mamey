"""Generic regressions for record-scoped RiQ source identity in bounded JSON."""
import io
import json
import zipfile
import importlib

import pytest

from mamey import antismash_evidence as ae


@pytest.fixture(autouse=True, params=["selected", "python"])
def _backend(request, monkeypatch):
    if not ae._HAVE_IJSON:
        pytest.skip("bounded parsing requires system or bundled ijson")
    if request.param == "python":
        monkeypatch.setattr(ae, "ijson", importlib.import_module("ijson.backends.python"))


def _modules(score, region="1"):
    return {"cluster_compare": {"by_region": {region: {
        "RegionToRegion_RiQ": {"scores_by_region": {"reference": score}}
    }}}}


def _record(identity, score, *, late=False):
    if late:
        return {"modules": _modules(score), "id": identity}
    return {"id": identity, "modules": _modules(score)}


def _parse(document):
    raw = document if isinstance(document, str) else json.dumps(document)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("results.json", raw)
    stream.seek(0)
    evidence = {"by_region": {}, "loose_hits": []}
    with zipfile.ZipFile(stream) as archive:
        ae._parse_json_bounded(archive, "results.json", evidence)
    return evidence


def _scores(evidence):
    return {key: rows[0]["riq_score"]
            for key, rows in evidence["by_region"].items()}


def test_missing_id_cannot_inherit_previous_record():
    evidence = _parse({"records": [
        _record("contig_alpha", 0.1),
        {"modules": _modules(0.99)},
    ]})
    assert _scores(evidence) == {"contig_alpha_c1": 0.1}
    assert evidence["riq_unmapped_count"] == 1
    assert evidence["loose_hits"][0]["riq_identity_status"] == "UNMAPPED_MISSING_RECORD_ID"
    assert evidence["riq_genome_summary"]["max"] == 0.1


@pytest.mark.parametrize("late", [False, True])
def test_record_field_order_does_not_change_binding(late):
    evidence = _parse({"records": [
        _record("contig_alpha", 0.1),
        _record("contig_beta", 0.8, late=late),
    ]})
    assert _scores(evidence) == {"contig_alpha_c1": 0.1, "contig_beta_c1": 0.8}
    assert evidence["riq_unmapped_count"] == 0
    assert evidence["riq_genome_summary"]["median"] == pytest.approx(0.45)


@pytest.mark.parametrize("identity", [None, "", "   ", 7, False])
def test_invalid_or_blank_id_is_unassigned(identity):
    evidence = _parse({"records": [
        _record("contig_alpha", 0.1), _record(identity, 0.9),
        _record("contig_gamma", 0.4, late=True),
    ]})
    assert _scores(evidence) == {"contig_alpha_c1": 0.1, "contig_gamma_c1": 0.4}
    assert evidence["riq_unmapped_count"] == 1


def test_first_missing_id_does_not_hide_later_valid_record():
    evidence = _parse({"records": [
        {"modules": _modules(0.9)}, _record("contig_beta", 0.2, late=True),
    ]})
    assert _scores(evidence) == {"contig_beta_c1": 0.2}
    assert evidence["riq_unmapped_count"] == 1


def test_scores_outside_records_do_not_reuse_last_identity():
    evidence = _parse({
        "records": [_record("contig_alpha", 0.1)],
        "other": _modules(0.99),
    })
    assert _scores(evidence) == {"contig_alpha_c1": 0.1}
    assert evidence["riq_unmapped_count"] == 1
    assert evidence["loose_hits"][0]["riq_identity_status"] == "UNMAPPED_RECORD_OR_REGION"


def test_unfinished_record_preserves_values_without_assignment():
    raw = '{"records":[' + json.dumps(_record("contig_alpha", 0.1)) + ","
    raw += json.dumps(_record("contig_beta", 0.99))[:-1]
    evidence = _parse(raw)
    assert evidence["json_errors"]
    assert _scores(evidence) == {"contig_alpha_c1": 0.1}
    assert evidence["riq_unmapped_count"] == 1
    assert evidence["loose_hits"][0]["riq_identity_status"] == "UNMAPPED_INCOMPLETE_RECORD"


def test_unassigned_maximum_keeps_observation_count():
    modules = _modules(0.3)
    modules["cluster_compare"]["by_region"]["1"]["RegionToRegion_RiQ"]["scores_by_region"]["second"] = 0.9
    evidence = _parse({"records": [{"modules": modules}]})
    assert evidence["by_region"] == {}
    assert evidence["riq_unmapped_count"] == 2
    assert len(evidence["loose_hits"]) == 1
    assert evidence["loose_hits"][0]["riq_score"] == 0.9
    assert evidence["loose_hits"][0]["riq_observation_count"] == 2


def test_repeated_valid_identity_retains_existing_maximum_semantics():
    evidence = _parse({"records": [
        _record("contig_alpha", 0.8), _record("contig_alpha", 0.3, late=True),
    ]})
    assert _scores(evidence) == {"contig_alpha_c1": 0.8}


def test_public_bounded_entrypoint_uses_record_scoped_identity(tmp_path):
    archive_path = tmp_path / "generic.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("results.json", json.dumps({"records": [
            _record("contig_alpha", 0.1), _record("contig_beta", 0.8, late=True),
            {"modules": _modules(0.99)},
        ]}))
    evidence = ae.parse_antismash_evidence(archive_path, json_mode="bounded")
    assert _scores(evidence) == {"contig_alpha_c1": 0.1, "contig_beta_c1": 0.8}
    assert evidence["riq_unmapped_count"] == 1


def test_leaf_cap_cannot_assign_an_unfinished_record(monkeypatch):
    monkeypatch.setattr(ae, "BOUNDED_MAX_RECORDS_STREAMING", 1)
    second = _record("contig_beta", 0.99)
    second["clusterblast"] = {"first": "hit", "second": "stop"}
    evidence = _parse({"records": [_record("contig_alpha", 0.1), second]})
    assert evidence["json_bounded_truncated"] is True
    assert _scores(evidence) == {"contig_alpha_c1": 0.1}
    assert evidence["riq_unmapped_count"] == 1
    assert evidence["loose_hits"][-1]["riq_identity_status"] == "UNMAPPED_INCOMPLETE_RECORD"


@pytest.mark.parametrize("shape", ["object", "dotted_key", "nested_array"])
def test_non_record_shapes_cannot_supply_an_identity(shape):
    record = _record("contig_alpha", 0.9)
    document = ({"records": {"item": record}} if shape == "object" else
                {"records.item": record} if shape == "dotted_key" else
                {"records": [[record]]})
    evidence = _parse(document)
    assert _scores(evidence) == {}
    assert evidence["riq_unmapped_count"] == 1


@pytest.mark.parametrize("second_id", ['"contig_beta"', '"contig_alpha"', 'null', '{}'])
def test_duplicate_id_is_unassigned_even_when_values_agree(second_id):
    raw = '{"records":[{"id":"contig_alpha","modules":' + json.dumps(_modules(0.9))
    raw += ',"id":' + second_id + '}]}'
    evidence = _parse(raw)
    assert _scores(evidence) == {}
    assert evidence["riq_unmapped_count"] == 1
    assert evidence["loose_hits"][0]["riq_identity_status"] == "UNMAPPED_DUPLICATE_RECORD_ID"


def test_full_contig_identifier_is_preserved():
    identity = "NODE_12_length_5000_cov_16.37"
    evidence = _parse({"records": [_record(identity, 0.4, late=True)]})
    assert _scores(evidence) == {identity + "_c1": 0.4}


def test_assignment_preserves_unassigned_observation_count():
    modules = _modules(0.3)
    modules["cluster_compare"]["by_region"]["1"]["RegionToRegion_RiQ"]["scores_by_region"]["second"] = 0.9
    evidence = _parse({"records": [{"modules": modules}]})
    ae.apply_evidence_to_bgcs([], evidence)
    assert evidence["riq_unmapped_count"] == 2
