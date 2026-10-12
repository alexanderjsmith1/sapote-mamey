"""Independently declared refusal boundaries for cached/source-scoped reporting."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from openpyxl import Workbook
from mamey.release_policy import resolve_run_release
from mamey.report_release_policy import policy_for_records
from mamey.rrefinder_status import state_from_structured, read_package_state
from tests.test_report_scope_raw_counts_m5 import evidence, tables, exporter


@pytest.mark.parametrize("state", [None, [], {}, True, 1, "", "HOLD", "UNSUPPORTED"])
def test_malformed_assignment_state_never_admits_public(state):
    decision = resolve_run_release("reference", "PUBLIC").to_dict()
    decision["assignment_state"] = state
    policy = policy_for_records([{"strain_id": "reference", "release": "PUBLIC", "release_decision": decision}], "reference")
    assert (policy["effective_release"], policy["privacy_assignment_state"]) == ("PRIVATE", "HOLD")


@pytest.mark.parametrize("reason,state", [("operator_public_override", "DEFAULT"),
                                          ("operator_public_override", "EXACT"),
                                          ("exact_public_assignment", "EXPLICIT"),
                                          ("exact_public_assignment", "DEFAULT")])
def test_supported_but_wrong_public_assignment_role_is_held(reason, state):
    decision = resolve_run_release("reference", "PUBLIC").to_dict()
    decision.update(reason=reason, assignment_state=state, authority_sha256="a" * 64)
    policy = policy_for_records([{"strain_id": "reference", "release": "PUBLIC", "release_decision": decision}], "reference")
    assert policy["effective_release"] == "PRIVATE"


@pytest.mark.parametrize("authority", [None, [], 123, "wrong", "A" * 64])
def test_malformed_authority_digest_is_held_even_for_operator_record(authority):
    decision = resolve_run_release("reference", "PUBLIC").to_dict()
    decision["authority_sha256"] = authority
    policy = policy_for_records([{"strain_id": "reference", "release": "PUBLIC", "release_decision": decision}], "reference")
    assert policy["effective_release"] == "PRIVATE"


@pytest.mark.parametrize("release,assignment,reason,authority", [
    ("PUBLIC", "EXPLICIT", "operator_public_override", ""),
    ("PUBLIC", "EXACT", "exact_public_assignment", "a" * 64),
    ("PRIVATE", "DEFAULT", "no_public_authority", ""),
    ("PRIVATE", "EXPLICIT", "operator_private_override", ""),
])
def test_supported_current_decision_shapes_keep_intended_release(release, assignment, reason, authority):
    decision = resolve_run_release("reference", release).to_dict()
    decision.update(assignment_state=assignment, reason=reason, authority_sha256=authority)
    policy = policy_for_records([{"strain_id": "reference", "release": release, "release_decision": decision}], "reference")
    assert policy["effective_release"] == release
    assert policy["privacy_assignment_state"] != "HOLD"


@pytest.mark.parametrize("occupied", ["prior_export", "unrelated_file", "file_destination", "symlink_destination"])
def test_occupied_export_refuses_before_any_writes_and_preserves_prior_bytes(tmp_path, occupied):
    source = tmp_path / "intentionally_unread_source.xlsx"
    source.write_bytes(b"Not a workbook: output refusal must happen before intake")
    out = tmp_path / "export"
    if occupied == "file_destination": out.write_bytes(b"preserve file")
    elif occupied == "symlink_destination":
        target = tmp_path / "target"; target.mkdir()
        (target / "old.csv").write_text("release,PUBLIC\n")
        out.symlink_to(target, target_is_directory=True)
    else:
        out.mkdir()
        (out / ("diagnostics_long.csv" if occupied == "prior_export" else "unrelated.txt")).write_text("release,PUBLIC\n")
    def bound():
        values = {str(p.relative_to(tmp_path)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in tmp_path.rglob("*") if p.is_file()}
        values["output_symlink"] = out.is_symlink()
        return values
    before = bound()
    with pytest.raises(ValueError, match="FIGURE_EXPORT_REQUIRES_FRESH_OUTPUT"):
        exporter().main(str(source), str(out))
    assert bound() == before


def test_existing_empty_export_directory_remains_compatible(tmp_path):
    wb = Workbook(); a2 = wb.active; a2.title = "A2_Strain_Registry"
    a2.append(["strain", "taxonomy", "bgc_count"]); a2.append(["legacy", "Invented reference", 1])
    b1 = wb.create_sheet("B1_BGC_Master")
    b1.append(["strain", "BGC_ID", "contig", "region", "products"])
    b1.append(["legacy", "BGC001", "CP123456.1", "region001", "RiPP"])
    source = tmp_path / "source.xlsx"; wb.save(source)
    out = tmp_path / "empty"; out.mkdir()
    exporter().main(str(source), str(out))
    assert json.loads((out / "release_policy.json").read_text())["policy"]["effective_release"] == "PRIVATE"
    assert (out / "bgc_inventory.csv").is_file()


@pytest.mark.parametrize("mutation", ["completeness", "record_contig", "module_record", "mapping_status",
                                       "mapping_method", "receipt_partial", "receipt_identity",
                                       "raw_count", "retained_count", "impossible_modules", "nonlist_rows"])
def test_cached_confident_observation_cannot_hide_contradictory_metadata(tmp_path, mutation):
    path, ev = evidence(tmp_path, "single")
    structured = tables(path, ev)
    assert structured["rrefinder_evidence_state"]["state"] == "SOURCE_OBSERVED_HITS"
    altered = copy.deepcopy(structured); state = altered["rrefinder_evidence_state"]
    row = altered["rrefinder"][0]
    if mutation == "completeness": state["source_completeness"] = "PARTIAL"
    elif mutation == "record_contig": row["contig"] = "CP123456.2"
    elif mutation == "module_record": row["module_record_id"] = "CP123456.2"
    elif mutation == "mapping_status": row["mapping_status"] = "IDENTITY_CONFLICT_SOURCE_RECORD"
    elif mutation == "mapping_method": row["mapping_method"] = "SOURCE_RECORD_ID_CONFLICT:record metadata"
    elif mutation == "receipt_partial": state["extraction_receipt"]["files"][0]["status"] = "PARSE_FAILED"
    elif mutation == "receipt_identity": state["extraction_receipt"]["files"][0]["rrefinder_identity_conflicts"] = 1
    elif mutation == "raw_count": state["raw_source_rows"] = 2
    elif mutation == "retained_count": state["retained_rows"] = 2
    elif mutation == "impossible_modules": state["extraction_receipt"]["files"][0]["rrefinder_modules_read"] = 2
    elif mutation == "nonlist_rows": altered["rrefinder"] = {"0": row}
    result = state_from_structured(altered)
    assert result["state"] == "SOURCE_CONFLICT"
    assert result["upstream_search"] == "UNKNOWN"
    assert result["biological_absence"] == "NOT_ESTABLISHED"
    package = tmp_path / "package"; package.mkdir()
    (package / "reference_3_antismash_structured.json").write_text(json.dumps(altered))
    assert read_package_state(package, "reference")["state"] == "SOURCE_CONFLICT"


@pytest.mark.parametrize("layout", ["single", "two_files", "empty"])
def test_valid_receipt_backed_states_round_trip_without_inventing_search_completion(tmp_path, layout):
    path, ev = evidence(tmp_path, layout)
    structured = tables(path, ev)
    result = state_from_structured(structured)
    assert result == structured["rrefinder_evidence_state"]
    assert result["state"] == ("SOURCE_OBSERVED_EMPTY" if layout == "empty" else "SOURCE_OBSERVED_HITS")
    assert result["upstream_search"] == "UNKNOWN"
    assert result["biological_absence"] == "NOT_ESTABLISHED"


@pytest.mark.parametrize("cached", [False, True])
def test_missing_legacy_receipt_is_unknown_even_with_cached_confident_label(tmp_path, cached):
    path, ev = evidence(tmp_path, "single")
    structured = tables(path, ev)
    if cached: structured["rrefinder_evidence_state"].pop("extraction_receipt")
    else: structured.pop("rrefinder_evidence_state")
    result = state_from_structured(structured)
    assert result["state"] == "UNKNOWN_COMPLETENESS"
    assert result["source_completeness"] == "UNKNOWN"
    assert result["source_rows"] == 1
    assert result["biological_absence"] == "NOT_ESTABLISHED"
