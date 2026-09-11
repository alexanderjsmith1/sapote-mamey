"""Coordinate fallback must retain malformed JSON-coordinate provenance."""
import math
import zipfile

import pytest

from mamey.antismash_tables import (
    _coordinates_for_json_row,
    _module_json_row,
    build_structured_tables,
)


def test_invalid_json_coordinates_are_visible_after_location_fallback():
    row = {
        "record_id": "generic_contig",
        "start": "not-an-integer",
        "end": "also-not-an-integer",
        "location": "10:20",
    }
    contig, start, end, strand, source = _coordinates_for_json_row(row, {}, {})
    assert (contig, start, end, strand) == ("generic_contig", 11, 20, 0)
    assert source == "JSON_LOCATION_AFTER_INVALID_JSON_COORDINATES"


def test_valid_json_coordinates_remain_preferred():
    row = {"record_id": "generic_contig", "start": 10, "end": 20}
    assert _coordinates_for_json_row(row, {}, {}) == (
        "generic_contig", 11, 20, 0, "JSON_COORDINATES"
    )


def test_absent_coordinates_remain_an_explicit_refusal():
    row = {"record_id": "generic_contig"}
    assert _coordinates_for_json_row(row, {}, {}) == (
        "generic_contig", None, None, 0, "NO_COORDINATE"
    )


def test_invalid_json_coordinates_are_visible_after_cds_fallback():
    row = {"record_id": "generic_contig", "start": "invalid", "end": "invalid", "locus_tag": "gene1"}
    direct = {("generic_contig", "gene1"): {"start": 100, "end": 200, "strand": 1}}
    assert _coordinates_for_json_row(row, direct, {"generic_contig": ["gene1"]}) == (
        "generic_contig", 100, 200, 1, "CDS_LOCUS_COORDINATES_AFTER_INVALID_JSON_COORDINATES"
    )


def test_invalid_json_coordinates_without_fallback_are_explicit():
    row = {"record_id": "generic_contig", "start": "invalid", "end": "invalid"}
    assert _coordinates_for_json_row(row, {}, {}) == (
        "generic_contig", None, None, 0, "NO_COORDINATE_AFTER_INVALID_JSON_COORDINATES"
    )


def test_invalid_coordinate_provenance_reaches_structured_table_row():
    source = {
        "record_id": "generic_contig", "start": "invalid", "end": "invalid",
        "location": "10:20", "locus_tag": "gene1",
    }
    bgcs = [{"bgc_id": "BGC001", "contig": "generic_contig", "start": 1, "end": 100}]
    row = _module_json_row(source, "TEST_EVIDENCE", bgcs, {}, {})
    assert row["mapping_status"] == "MAPPED"
    assert row["mapping_method"] == (
        "COORDINATE_OVERLAP:JSON_LOCATION_AFTER_INVALID_JSON_COORDINATES"
    )


def test_invalid_unavailable_geometry_reaches_unmapped_refusal_row():
    source = {"record_id": "generic_contig", "start": "invalid", "end": "invalid"}
    row = _module_json_row(source, "TEST_EVIDENCE", [], {}, {})
    assert row["mapping_status"] == "UNMAPPED_NO_COORDINATES"
    assert row["mapping_method"] == (
        "NO_COORDINATE:NO_COORDINATE_AFTER_INVALID_JSON_COORDINATES"
    )


@pytest.mark.parametrize("start,end", [
    (1, None), (None, 2), (True, 2), (1, False), (1.5, 3), (1, 3.5),
    (math.inf, 3), (1, math.inf), (-1, 3), (3, 3), (4, 3),
])
def test_partial_or_invalid_explicit_geometry_is_not_admitted(start, end):
    row = {"record_id": "generic_contig", "start": start, "end": end}
    assert _coordinates_for_json_row(row, {}, {}) == (
        "generic_contig", None, None, 0, "NO_COORDINATE_AFTER_INVALID_JSON_COORDINATES"
    )


@pytest.mark.parametrize("strand", [True, 1.5, math.inf, "sideways", 2, -2])
def test_invalid_explicit_strand_is_visible_without_crashing(strand):
    row = {"record_id": "generic_contig", "start": 1, "end": 3, "strand": strand}
    assert _coordinates_for_json_row(row, {}, {}) == (
        "generic_contig", 2, 3, 0, "JSON_COORDINATES_AFTER_INVALID_JSON_STRAND"
    )


@pytest.mark.parametrize("strand", [-1, 0, 1, "-1", "0", "1"])
def test_valid_strand_values_remain_supported(strand):
    row = {"record_id": "generic_contig", "start": 1, "end": 3, "strand": strand}
    assert _coordinates_for_json_row(row, {}, {}) == (
        "generic_contig", 2, 3, int(strand), "JSON_COORDINATES"
    )


def test_ripp_table_consumer_preserves_invalid_coordinate_provenance(tmp_path):
    archive = tmp_path / "empty.zip"
    with zipfile.ZipFile(archive, "w"):
        pass
    evidence = {"ripp_cores": [{
        "record_id": "generic_contig", "start": True, "end": 20,
        "location": "10:20", "module": "fixture_ripp",
    }]}
    tables = build_structured_tables(archive, evidence, [])
    assert tables["ripp_motifs"][0]["mapping_method"] == (
        "COORDINATE_OVERLAP:JSON_LOCATION_AFTER_INVALID_JSON_COORDINATES"
    )
