"""Explicit source-reviewed roles and typed front-door metadata; no native tools."""
import csv
from pathlib import Path
from types import SimpleNamespace

import pytest
from tools import _placement_report_metadata as contract

TIP = "NR_000001_1_Genus_alpha_strain_A1_16S_ribosomal_RNA_partial_sequence"
LABEL = "NR_000001.1 Genus alpha strain A1 16S ribosomal RNA, partial sequence"


def table(path, rows, fields=None):
    fields = fields or list(rows[0])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    return str(path)


def positive(**updates):
    row = dict(tip=TIP, accession="NR_000001.1", source_accession="NR_000001.1", taxon="Genus alpha", strain="A1",
               role="type_reference", type_strain_of="Genus alpha", type_evidence="synthetic explicit type-material record",
               review_state="REVIEWED", source_url="https://example.org/synthetic/NR_000001.1",
               strain_identity_basis="synthetic exact deposited strain A1")
    row.update(updates)
    return row


def test_prefix_and_legacy_mark_are_unknown_without_evidence(tmp_path):
    path = table(tmp_path/"legacy.tsv", [dict(accession="NR_000001.1", tip=TIP, type_display="Type")])
    result = contract.reviewed_type_map([path], {TIP: LABEL})
    assert result["roles"] == {}
    assert result["issues"][0]["state"] == "UNVERIFIED_LEGACY_TYPE_MARK_SUPPRESSED"
    assert contract.reviewed_type_map([], {TIP: LABEL})["unknown_role"] == "NOT_RECORDED"


def test_reviewed_exact_sequence_identity_accepts_and_preserves_raw_evidence(tmp_path):
    row = positive(); path = table(tmp_path/"reviewed.tsv", [row])
    result = contract.reviewed_type_map([path], {TIP: LABEL})
    assert result["roles"][TIP] == {key: row[key] for key in contract.TYPE_FIELDS}


@pytest.mark.parametrize("updates,reason", [
    ({"type_evidence": ""}, "EVIDENCE_MISSING"), ({"strain": "A2"}, "STRAIN_IDENTITY_CONFLICT"), ({"source_accession": "NR_000001.2"}, "SOURCE_ACCESSION_UNBOUND"),
    ({"source_accession": "GCF_000001.1"}, "SOURCE_ACCESSION_UNBOUND"), ({"review_state": "PENDING"}, "REVIEW_OR_TARGET"),
    ({"source_url": ""}, "EVIDENCE_MISSING"), ({"strain_identity_basis": ""}, "EVIDENCE_MISSING"),
    ({"tip": "OTHER"}, "TIP_IDENTITY_UNBOUND"), ({"accession": "NR_000002.1"}, "SOURCE_ACCESSION_CONFLICT")])
def test_invalid_positive_role_refuses_not_downgrades(tmp_path, updates, reason):
    path = table(tmp_path/"reviewed.tsv", [positive(**updates)])
    with pytest.raises(ValueError, match=reason):
        contract.reviewed_type_map([path], {TIP: LABEL})


def test_query_cannot_be_promoted_to_reference_type(tmp_path):
    path = table(tmp_path/"reviewed.tsv", [positive()])
    with pytest.raises(ValueError, match="TIP_IDENTITY_UNBOUND"):
        contract.reviewed_type_map([path], {TIP: LABEL}, query_tips=[TIP])


@pytest.mark.parametrize("reverse", [False, True])
def test_conflicting_type_and_explicit_non_type_refuse_in_both_orders(tmp_path, reverse):
    paths = [table(tmp_path/"type.tsv", [positive()]), table(tmp_path/"non_type.tsv", [positive(role="cultured_non_type_reference")])]
    with pytest.raises(ValueError, match="REVIEW_CONFLICT"):
        contract.reviewed_type_map(paths[::-1] if reverse else paths, {TIP: LABEL})


def test_repeated_identical_review_is_idempotent_but_conflicting_review_holds(tmp_path):
    path = table(tmp_path/"type.tsv", [positive()])
    assert len(contract.reviewed_type_map([path, path], {TIP: LABEL})["roles"]) == 1
    changed = table(tmp_path/"changed.tsv", [positive(type_evidence="different explicit reviewed evidence")])
    with pytest.raises(ValueError, match="REVIEW_CONFLICT"):
        contract.reviewed_type_map([path, changed], {TIP: LABEL})


def test_options_preserve_whole_spaced_paths_and_resolved_order(tmp_path):
    one = table(tmp_path/"one table.tsv", [dict(exact_accession="NR_1.1", verification_status="STRAIN_CONFIRMED", isolation_source="soil", location="Italy")])
    two = table(tmp_path/"two table.tsv", [dict(exact_accession="NR_2.1", verification_status="STRAIN_CONFIRMED", isolation_source="soil", location="Italy")])
    options = contract.normalize_options(SimpleNamespace(resolved_metadata=[one, two], reference_metadata="build-only.tsv"), context="all")
    argv = contract.to_argv(options)
    assert options["resolved_metadata"] == [one, two]
    assert argv[:4] == ["--resolved", one, "--resolved", two]
    assert "build-only.tsv" not in argv and options["requested"]


@pytest.mark.parametrize("field", [field for field, _flag in contract.LIST_OPTIONS])
def test_supplied_empty_metadata_path_refuses(field):
    with pytest.raises(ValueError, match="PATH_EMPTY"):
        contract.normalize_options(SimpleNamespace(**{field: [""]}))


def test_scalar_resolved_and_symlink_and_duplicate_inputs_refuse(tmp_path):
    path = table(tmp_path/"owner.tsv", [dict(tip="PUBLIC_QUERY_01", label="Synthetic query", source_category="Soil", geography_category="Europe")])
    with pytest.raises(ValueError, match="REQUIRES_LIST"):
        contract.normalize_options(SimpleNamespace(resolved_metadata=path))
    alias = tmp_path/"alias.tsv"; alias.symlink_to(path)
    with pytest.raises(ValueError, match="PATH_INVALID"):
        contract.normalize_options(SimpleNamespace(owner_table=[str(alias)]))
    with pytest.raises(ValueError, match="DUPLICATE_INPUT"):
        contract.normalize_options(SimpleNamespace(owner_table=[path, path]))


def test_non_refseq_accession_can_have_explicit_reviewed_type_evidence(tmp_path):
    tip = TIP.replace("NR_000001", "MZ000001")
    label = LABEL.replace("NR_000001", "MZ000001")
    row = positive(tip=tip, accession="MZ000001.1", source_accession="MZ000001.1")
    path = table(tmp_path/"non_refseq.tsv", [row])
    assert contract.reviewed_type_map([path], {tip: label})["roles"][tip]["role"] == "type_reference"


@pytest.mark.parametrize("status", ["ERROR", "REFUSED_STRAIN_MISMATCH", "UNKNOWN"])
def test_unadmitted_resolver_identity_cannot_support_positive_type(tmp_path, status):
    path = table(tmp_path/"type.tsv", [positive()])
    resolver = table(tmp_path/"resolved.tsv", [dict(exact_accession="NR_000001.1", verification_status=status)])
    with pytest.raises(ValueError, match="RESOLVER_IDENTITY_UNADMITTED"):
        contract.reviewed_type_map([path], {TIP: LABEL}, resolved_paths=[resolver])
