"""Regression coverage for the shared EPA-ng/GToTree display contract."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from phylo_display_contract import ASSAY_SYMBOL, load_palette, validate_display_metadata, validate_layout_profile


def _fixture():
    rows = [
        dict(tip="QUERY", role="query", type_status="not_applicable",
             taxon_display="Genus sp. Query-1",
             label_concise="Genus sp. Query-1 [bumblebee; US]",
             label_experiment="Genus sp. Query-1 [bumblebee; US] {Experiment-1; Sample-1}",
             raw_source="Bombus specimen", source_category="bumblebee",
             raw_geography="USA: documented locality", geography="US",
             candida_state="positive", mrsa_state="missing",
             assay_provenance="generic owner fixture", experiment_id="Experiment-1", sample_id="Sample-1"),
        dict(tip="REFERENCE", role="reference", type_status="non_type",
             taxon_display="Genus sp. Strain-R",
             label_concise="Genus sp. Strain-R [soil/rock/sediment; Asia]",
             label_experiment="Genus sp. Strain-R [soil/rock/sediment; Asia]",
             raw_source="soil", source_category="soil/rock/sediment",
             raw_geography="China: documented locality", geography="Asia",
             candida_state="", mrsa_state="", assay_provenance="", experiment_id="", sample_id=""),
        dict(tip="OUTGROUP", role="outgroup", type_status="type",
             taxon_display="Outgroupus species Type-Strain",
             label_concise="Outgroupus species Type-Strain (Type) [aquatic; Pacific Ocean]",
             label_experiment="Outgroupus species Type-Strain (Type) [aquatic; Pacific Ocean]",
             raw_source="marine water", source_category="aquatic",
             raw_geography="Pacific Ocean", geography="Pacific Ocean",
             candida_state="", mrsa_state="", assay_provenance="", experiment_id="", sample_id=""),
    ]
    provenance = []
    for row in rows:
        fields = ["raw_source", "raw_geography"]
        if row["role"] == "query":
            fields += ["candida_state", "mrsa_state"]
        for field in fields:
            provenance.append(dict(tip=row["tip"], field=field, raw_value=row[field],
                                   source="generic fixture", evidence_sha256="b" * 64, status="bound"))
    return rows, provenance


def test_both_renderer_families_load_the_same_palette_file():
    for name in ("ggtree_rect_heatmap.R", "tree_reference_series.R"):
        source = (ROOT / "tools" / name).read_text(encoding="utf-8")
        assert "phylo_display_palette.tsv" in source
    gate = (ROOT / "tools" / "tree_annotation_gate.py").read_text(encoding="utf-8")
    assert "phylo_display_palette.tsv" in gate


def test_layout_profile_rejects_the_observed_tree_area_regression():
    assert validate_layout_profile("full_genus_single_line_v1", 0.39)["tree_fraction"] == 0.39
    with pytest.raises(ValueError, match="TREE_AREA_REGRESSION"):
        validate_layout_profile("full_genus_single_line_v1", 0.25)


def test_metadata_contract_is_order_invariant_and_preserves_distinct_assays():
    rows, provenance = _fixture()
    palette = load_palette(ROOT / "tools" / "phylo_display_palette.tsv")
    first = validate_display_metadata(rows, provenance, palette,
                                      profile="full_genus_single_line_v1", tree_fraction=0.39)
    second = validate_display_metadata(list(reversed(rows)), list(reversed(provenance)), palette,
                                       profile="full_genus_single_line_v1", tree_fraction=0.39)
    assert first == second
    assert ASSAY_SYMBOL == {"positive": "+", "negative": "-", "not_tested": "n.t.", "missing": "?"}


def test_provenance_value_mismatch_and_reference_assay_are_refused():
    rows, provenance = _fixture(); palette = load_palette(ROOT / "tools" / "phylo_display_palette.tsv")
    provenance[0]["raw_value"] = "different source"
    with pytest.raises(ValueError, match="PROVENANCE_VALUE"):
        validate_display_metadata(rows, provenance, palette,
                                  profile="full_genus_single_line_v1", tree_fraction=0.39)
    rows, provenance = _fixture(); rows[1]["candida_state"] = "not_tested"
    with pytest.raises(ValueError, match="REFERENCE_ASSAY_NOT_BLANK"):
        validate_display_metadata(rows, provenance, palette,
                                  profile="full_genus_single_line_v1", tree_fraction=0.39)


def test_non_type_species_label_and_unbound_experiment_are_refused():
    rows, provenance = _fixture(); palette = load_palette(ROOT / "tools" / "phylo_display_palette.tsv")
    rows[1]["taxon_display"] = "Genus species Strain-R"
    rows[1]["label_concise"] = rows[1]["label_concise"].replace("Genus sp.", "Genus species")
    rows[1]["label_experiment"] = rows[1]["label_concise"]
    with pytest.raises(ValueError, match="NONTYPE_LABEL"):
        validate_display_metadata(rows, provenance, palette,
                                  profile="full_genus_single_line_v1", tree_fraction=0.39)
    rows, provenance = _fixture(); rows[0]["sample_id"] = ""
    with pytest.raises(ValueError, match="EXPERIMENT_BINDING"):
        validate_display_metadata(rows, provenance, palette,
                                  profile="full_genus_single_line_v1", tree_fraction=0.39)


def test_jplace_alternatives_preserve_n_nm_multiplicity_and_retained_weights(tmp_path):
    from phylo_place import _jplace_placements_tsv
    fields = ["edge_num", "likelihood", "like_weight_ratio", "distal_length", "pendant_length"]
    data = {"fields": fields, "placements": [
        {"n": ["query-one"], "p": [[4, -10.0, .6, .01, .02], [7, -11.0, .3, .03, .04]]},
        {"nm": [["query-two", 3]], "p": [[9, -8.0, .8, .02, .01], [2, -12.0, .1, .05, .06]]},
    ]}
    source = tmp_path / "placements.jplace"; source.write_text(json.dumps(data))
    output = tmp_path / "alternatives.tsv"
    assert _jplace_placements_tsv(source, output) == {"queries": 2, "rows": 4}
    rows = list(csv.DictReader(output.open(), delimiter="\t"))
    assert [row["placement_rank"] for row in rows] == ["1", "2", "1", "2"]
    assert rows[0]["retained_lwr_sum"] == "0.900000" and rows[2]["multiplicity"] == "3"
    assert all(row["uncertainty_measure"] == "LWR_NOT_BOOTSTRAP_OR_SPECIES_PROBABILITY" for row in rows)


def test_jplace_query_reference_collision_and_duplicate_query_fail(tmp_path):
    from phylo_place import _jplace_placements_tsv
    fields = ["edge_num", "like_weight_ratio", "pendant_length"]
    source = tmp_path / "placements.jplace"; output = tmp_path / "out.tsv"
    source.write_text(json.dumps({"fields": fields, "placements": [{"n": ["same"], "p": [[1, 1.0, .1]]}]}))
    with pytest.raises(ValueError, match="QUERY_REFERENCE_COLLISION"):
        _jplace_placements_tsv(source, output, reference_names={"same"})
    source.write_text(json.dumps({"fields": fields, "placements": [
        {"n": ["repeat"], "p": [[1, 1.0, .1]]}, {"nm": [["repeat", 2]], "p": [[2, 1.0, .1]]}]}))
    with pytest.raises(ValueError, match="IDENTITY_DUPLICATE"):
        _jplace_placements_tsv(source, output)
