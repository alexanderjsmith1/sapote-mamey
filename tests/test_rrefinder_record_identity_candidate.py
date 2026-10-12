import json
from types import SimpleNamespace
from zipfile import ZipFile
import pytest
from mamey import antismash_evidence as ae
from mamey.antismash_tables import build_structured_tables
from tests.test_reporting_evidence_v2 import _record, _rre_hit


def source(tmp_path, records):
    path = tmp_path / "records.zip"
    with ZipFile(path, "w") as zf:
        for i, record in enumerate(records):
            zf.writestr(str(i) + ".json", json.dumps({"version": "8.0.4", "records": [record]}))
    return path


def record(empty=False):
    return _record("NODE_1", {} if empty else {"gene": [_rre_hit("[120:150](+)", "RRE", "FAMILY")]})


def tables(path, evidence):
    bgc = SimpleNamespace(bgc_id="BGC001", contig="NODE_1", start=100, end=1000,
                          products=["RiPP"], source_gbk="")
    return build_structured_tables(path, evidence, [bgc])


@pytest.mark.parametrize("empty", [False, True])
def test_explicit_record_disagreement_is_held_even_when_empty(tmp_path, empty):
    rec = record(empty)
    rec["modules"]["antismash.modules.rrefinder"]["record_id"] = "OTHER_RECORD"
    path = source(tmp_path, [rec])
    ev = ae.parse_antismash_evidence(path, json_mode="off", include_structured=True)
    out = tables(path, ev)
    assert out["rrefinder_status"] == "SOURCE_CONFLICT"
    assert len(out["rrefinder"]) == (0 if empty else 1)
    assert ev["record_extraction"]["files"][0]["rrefinder_identity_conflicts"] == 1
    if not empty:
        row = out["rrefinder"][0]
        assert row["bgc_id"] == "UNMAPPED"
        assert row["mapping_status"] == "IDENTITY_CONFLICT_SOURCE_RECORD"
        assert "OTHER_RECORD" in row["mapping_method"]


def test_valid_and_conflicting_duplicate_measurements_are_both_retained(tmp_path):
    valid = record()
    conflict = record()
    conflict["modules"]["antismash.modules.rrefinder"]["record_id"] = "OTHER_RECORD"
    path = source(tmp_path, [valid, conflict])
    ev = ae.parse_antismash_evidence(path, json_mode="off", include_structured=True)
    out = tables(path, ev)
    assert out["rrefinder_status"] == "SOURCE_CONFLICT"
    assert len(out["rrefinder"]) == 2
    assert {row["mapping_status"] for row in out["rrefinder"]} == {"MAPPED", "IDENTITY_CONFLICT_SOURCE_RECORD"}
    assert out["counts"]["rrefinder_mapped"] == out["counts"]["rrefinder_unmapped"] == 1


def test_cached_false_conflict_flag_cannot_override_actual_source_ids(tmp_path):
    rec = record()
    rec["modules"]["antismash.modules.rrefinder"]["record_id"] = "OTHER_RECORD"
    path = source(tmp_path, [rec])
    ev = ae.parse_antismash_evidence(path, json_mode="off", include_structured=True)
    ev["rrefinder_hits"][0]["identity_conflict"] = False
    ev["record_extraction"]["files"][0]["rrefinder_identity_conflicts"] = 0
    out = tables(path, ev)
    assert out["rrefinder_status"] == "SOURCE_CONFLICT"
    assert out["rrefinder"][0]["bgc_id"] == "UNMAPPED"


def test_conflict_and_parse_failure_both_remain_in_receipt(tmp_path):
    rec = record()
    module = rec["modules"]["antismash.modules.rrefinder"]
    module["record_id"] = "OTHER_RECORD"
    module["hits_by_cds"] = {"gene": [None]}
    path = source(tmp_path, [rec])
    ev = ae.parse_antismash_evidence(path, json_mode="off", include_structured=True)
    out = tables(path, ev)
    assert out["rrefinder_status"] == "SOURCE_CONFLICT"
    receipt = ev["record_extraction"]["files"][0]
    assert receipt["rrefinder_identity_conflicts"] == 1
    assert receipt["error_counts"]["_rrefinder_from_rec"] == 1


def test_missing_containing_id_does_not_guess_from_module_id(tmp_path):
    rec = record()
    rec["id"] = ""
    path = source(tmp_path, [rec])
    ev = ae.parse_antismash_evidence(path, json_mode="off", include_structured=True)
    out = tables(path, ev)
    assert len(out["rrefinder"]) == 1
    assert out["rrefinder"][0]["bgc_id"] == "UNMAPPED"
    assert out["rrefinder"][0]["record_id"] == ""
