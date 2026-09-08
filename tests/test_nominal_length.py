"""Tests for nominal_length — fragmented-BGC kb measurement + nominal normalization."""
from mamey.nominal_length import measure_bgc, length_kb_of, NOMINAL_REFERENCES


def test_length_kb_from_field():
    assert length_kb_of({"length_kb": 16.42}) == 16.42

def test_length_kb_from_coords():
    assert length_kb_of({"start": 0, "end": 16424}) == 16.42

def test_length_kb_guards_garbage():
    assert length_kb_of({"start": "x", "end": None}) == 0.0

def test_interior_gets_kb_only_no_nominal():
    m = measure_bgc({"BGC_ID": "B", "Boundary": "Interior", "Products": ["nucleoside"], "length_kb": 30.0})
    assert m["nominal_kb"] is None              # interior is not a fragment -> no normalization
    assert m["recovery_label"] == "30.0 kb"

def test_nucleoside_fragment_gets_nominal():
    m = measure_bgc({"BGC_ID": "B", "Boundary": "Edge", "Products": ["nucleoside"], "length_kb": 11.0})
    assert m["nominal_kb"] == 30.0
    assert m["recovery_pct"] == 36.7
    assert "yardstick" in m["recovery_label"]
    assert "unconfirmed ref" in m["recovery_label"]   # polyoxin seed is confirmed=False

def test_fragment_over_nominal_not_clipped():
    m = measure_bgc({"BGC_ID": "B", "Boundary": "Full-contig", "Products": ["nucleoside"], "length_kb": 42.0})
    assert m["recovery_pct"] > 100
    assert "exceeds nominal" in m["recovery_label"]

def test_non_matching_class_gets_kb_only():
    m = measure_bgc({"BGC_ID": "B", "Boundary": "Edge", "Products": ["NRPS", "PKS"], "length_kb": 18.0})
    assert m["reference"] is None
    assert m["recovery_label"] == "18.0 kb"

def test_recovery_is_not_a_completeness_claim():
    # the label must never imply "X% of the strain's true cluster is present"
    m = measure_bgc({"BGC_ID": "B", "Boundary": "Edge", "Products": ["nucleoside"], "length_kb": 11.0})
    assert "completeness claim" in m["recovery_label"]  # explicitly disclaims it

def test_polyoxin_seed_is_unconfirmed():
    poly = [r for r in NOMINAL_REFERENCES if "polyoxin" in r.label.lower()][0]
    assert poly.confirmed is False
    assert "EU158805.1" in poly.source_accession and "JN674503.1" in poly.source_accession
    assert poly.nominal_kb == 30.0
    assert set(poly.members) == {"EU158805.1", "JN674503.1"}
    assert poly.nominal_range_kb == (27.9, 32.0)
