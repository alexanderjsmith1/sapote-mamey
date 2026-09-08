import struct

import pytest

from mamey.figure_policy import (
    ALL_ZERO_SEMANTICS,
    CAPTION_METHOD_SCHEMA,
    COHORT_PALETTE,
    FigurePolicyError,
    SPECIALIST_CLASSES,
    apply_genus_preset,
    is_pure_saccharide,
    omit_saccharides,
    plan_heatmap_scale,
    preflight_chart_data,
    validate_caption_methods,
    validate_cohort_manifest,
    validate_cohort_palette,
    validate_genus_comparison,
    validate_layout_rectangles,
    validate_tick_label_data_clearance,
    validate_publication_artwork,
    validate_publication_profile,
)

def test_pure_saccharide_omitted():
    assert is_pure_saccharide("saccharide")
    assert is_pure_saccharide("saccharide;saccharide")
    assert is_pure_saccharide(["saccharide"])

def test_specialist_with_sugar_arm_kept():
    # specialist class + saccharide tailoring arm is NOT pure-saccharide
    assert not is_pure_saccharide("NRPS;saccharide")
    assert not is_pure_saccharide("T2PKS")
    assert not is_pure_saccharide("nucleoside;saccharide")
    assert not is_pure_saccharide("")

def test_omit_saccharides_filters():
    bgcs=[{"products":"saccharide"},{"products":"NRPS;saccharide"},{"products":"T2PKS"},{"products":"terpene"}]
    kept=omit_saccharides(bgcs)
    assert {b["products"] for b in kept}=={"NRPS;saccharide","T2PKS","terpene"}
    # bypass switch returns all
    assert len(omit_saccharides(bgcs, enabled=False))==4

def test_terpene_is_specialist():
    assert "terpene" in SPECIALIST_CLASSES
    assert not is_pure_saccharide("terpene")


def test_preflight_refuses_empty_all_zero_and_one_point_scatter():
    with pytest.raises(FigurePolicyError, match="FIGURE_DATA_EMPTY"):
        preflight_chart_data([], chart_kind="bar", numeric_fields=["value"])
    with pytest.raises(FigurePolicyError, match="FIGURE_DATA_ALL_ZERO"):
        preflight_chart_data(
            [{"value": 0}, {"value": 0}], chart_kind="bar", numeric_fields=["value"]
        )
    with pytest.raises(FigurePolicyError, match="FIGURE_SCATTER_TOO_FEW_POINTS"):
        preflight_chart_data(
            [{"x": 3, "y": 7}], chart_kind="scatter", numeric_fields=["x", "y"]
        )


def test_preflight_warns_on_constant_scatter_but_keeps_real_variation():
    constant = preflight_chart_data(
        [{"x": 1, "y": 2}, {"x": 1, "y": 2}],
        chart_kind="scatter",
        numeric_fields=["x", "y"],
    )
    assert constant["status"] == "PASS_WITH_WARNINGS"
    assert constant["warnings"][0]["code"] == "FIGURE_SCATTER_NO_VARIATION"
    receipt = preflight_chart_data(
        [{"x": 1, "y": 2}, {"x": 2, "y": 2}],
        chart_kind="scatter",
        numeric_fields=["x", "y"],
    )
    assert receipt["status"] == "PASS"
    assert receipt["row_count"] == 2
    assert receipt["field_summaries"]["x"]["unique_values"] == 2


def test_typed_state_heatmap_can_explicitly_report_observed_zero():
    receipt = preflight_chart_data(
        [{"state": 0}, {"state": 0}],
        chart_kind="state_heatmap",
        numeric_fields=["state"],
        allow_all_zero=True,
        all_zero_semantics="OBSERVED_ZERO_NOT_MISSING",
        all_zero_meaning=ALL_ZERO_SEMANTICS["OBSERVED_ZERO_NOT_MISSING"],
    )
    assert receipt["allow_all_zero"] is True
    assert receipt["all_zero_semantics"] == "OBSERVED_ZERO_NOT_MISSING"
    assert receipt["all_zero_meaning"] == ALL_ZERO_SEMANTICS["OBSERVED_ZERO_NOT_MISSING"]


def test_all_zero_exception_requires_registered_semantics_and_canonical_explanation():
    for semantics, explanation, code in (
        (None, None, "FIGURE_ALL_ZERO_SEMANTICS_INVALID"),
        (None, "xxxxxxxxxxxxxxxxxxxx", "FIGURE_ALL_ZERO_SEMANTICS_INVALID"),
        ("UNKNOWN", "xxxxxxxxxxxxxxxxxxxx", "FIGURE_ALL_ZERO_SEMANTICS_INVALID"),
        ("OBSERVED_ZERO_NOT_MISSING", "xxxxxxxxxxxxxxxxxxxx", "FIGURE_ALL_ZERO_EXPLANATION_INVALID"),
    ):
        with pytest.raises(FigurePolicyError, match=code):
            preflight_chart_data(
                [{"value": 0}, {"value": 0}],
                chart_kind="bar",
                numeric_fields=["value"],
                allow_all_zero=True,
                all_zero_semantics=semantics,
                all_zero_meaning=explanation,
            )


def test_caption_methods_require_owner_selected_fields_and_visual_grammar():
    complete = {
        "caption_schema_version": CAPTION_METHOD_SCHEMA,
        "figure_question": "How does the measured quantity vary?",
        "source": "table.csv sha256=abc",
        "source_bindings": f"table.csv; sha256={'a' * 64}; bytes=12",
        "source_release": "release-1",
        "software_versions": "renderer 1",
        "unit_of_analysis": "one strain",
        "inclusion_exclusion_roles": "12 study strains; benchmark excluded",
        "denominator": "12 strains",
        "group_denominators": "grouping=genus; Streptomyces(rows=12; strains=12)",
        "typed_missingness": "plotted_rows=12; state(typed_rows=12; rows_missing_state_key=0; state=OBSERVED: 12)",
        "benchmark_sensitivity": "available=1; selected=0; default_off=true; benchmarks remain excluded from study n and percentages",
        "transformation": "raw counts",
        "statistics_uncertainty": "median and IQR",
        "comparison_group": "within-genus references",
        "genus_control": "WITHIN_GENUS",
        "contradictions": "NONE_RECORDED",
        "visual_grammar": "Rows are genera; bars are means; whiskers are SEM.",
        "interpretation_boundary": "Counts do not establish expression.",
    }
    assert validate_caption_methods(complete, nonstandard_visual=True)["status"] == "PASS"
    incomplete = dict(complete)
    incomplete["denominator"] = ""
    with pytest.raises(FigurePolicyError, match="FIGURE_CAPTION_METHODS_INCOMPLETE"):
        validate_caption_methods(incomplete)
    missing_grammar = dict(complete)
    missing_grammar.pop("visual_grammar")
    with pytest.raises(FigurePolicyError, match="FIGURE_CAPTION_METHODS_INCOMPLETE"):
        validate_caption_methods(missing_grammar, nonstandard_visual=True)
    wrong_schema = dict(complete, caption_schema_version="legacy")
    with pytest.raises(FigurePolicyError, match="FIGURE_CAPTION_SCHEMA_INVALID"):
        validate_caption_methods(wrong_schema)
    bad_binding = dict(complete, source_bindings="table.csv; sha256=abc")
    with pytest.raises(FigurePolicyError, match="FIGURE_CAPTION_SOURCE_BINDING_INVALID"):
        validate_caption_methods(bad_binding)
    for field, code in (
        ("unit_of_analysis", "FIGURE_CAPTION_UNIT_INVALID"),
        ("denominator", "FIGURE_CAPTION_DENOMINATOR_INVALID"),
        ("group_denominators", "FIGURE_CAPTION_GROUP_DENOMINATOR_INVALID"),
        ("typed_missingness", "FIGURE_CAPTION_TYPED_MISSINGNESS_INVALID"),
    ):
        placeholder = dict(complete, **{field: "x"})
        with pytest.raises(FigurePolicyError, match=code):
            validate_caption_methods(placeholder)
    repeated_character_unit = dict(complete, unit_of_analysis="xxxxxxxx")
    with pytest.raises(FigurePolicyError, match="FIGURE_CAPTION_UNIT_INVALID"):
        validate_caption_methods(repeated_character_unit)
    incomplete_coverage = dict(complete, typed_missingness="state=OBSERVED: 12")
    with pytest.raises(FigurePolicyError, match="FIGURE_CAPTION_TYPED_MISSINGNESS_INVALID"):
        validate_caption_methods(incomplete_coverage)
    for statement in (
        "available=1; selected=0; default_off=false; benchmark pooled into study n and percentages",
        "available=1; selected=0; default_off=true",
    ):
        contradictory = dict(complete, benchmark_sensitivity=statement)
        with pytest.raises(FigurePolicyError, match="FIGURE_CAPTION_BENCHMARK_SENSITIVITY_INVALID"):
            validate_caption_methods(contradictory)


def test_cross_genus_requires_control_and_within_genus_is_default_safe():
    assert validate_genus_comparison("WITHIN_GENUS")["status"] == "PASS"
    with pytest.raises(FigurePolicyError, match="FIGURE_CROSS_GENUS_CONTROL_MISSING"):
        validate_genus_comparison("CROSS_GENUS")
    assert validate_genus_comparison("CROSS_GENUS", "COMPOSITION_SHOWN")["status"] == "PASS"


def test_genus_preset_keeps_defaults_and_independently_selected_options():
    rows = [
        {"genus": "Streptomyces", "value": 1},
        {"genus": "Actinomadura", "value": 2},
        {"genus": "Paenibacillus", "value": 3},
        {"genus": "Leucocoprinus", "value": 4},
    ]
    kept, receipt = apply_genus_preset(
        rows,
        genus_field="genus",
        default_genera=["Streptomyces", "Actinomadura"],
        optional_genera=["Paenibacillus", "Leucocoprinus"],
        selected_optional=["Paenibacillus"],
    )
    assert [row["genus"] for row in kept] == ["Streptomyces", "Actinomadura", "Paenibacillus"]
    assert receipt["included_rows"] == 3
    assert receipt["excluded_rows"] == 1
    with pytest.raises(FigurePolicyError, match="FIGURE_GENUS_OPTION_UNDECLARED"):
        apply_genus_preset(
            rows,
            genus_field="genus",
            default_genera=["Streptomyces"],
            optional_genera=["Paenibacillus"],
            selected_optional=["Leucocoprinus"],
        )


def test_cohort_manifest_roles_default_off_and_assembly_hold_are_not_inferred():
    rows = [
        {
            "identity": "SYN-STUDY-1",
            "role": "STUDY",
            "include_by_default": True,
            "genus": "Genus alpha",
            "cohort": "BEE",
            "assembly_state": "PASS",
            "assembly_reason": "NONE_RECORDED",
        },
        {
            "identity": "SYN-ASSEMBLY-HOLD",
            "role": "STUDY",
            "include_by_default": False,
            "genus": "Genus alpha",
            "cohort": "WASP",
            "assembly_state": "DEFAULT_OFF",
            "assembly_reason": "FRAGMENTATION_MAY_INFLATE_COUNTS",
        },
        {
            "identity": "SYN-BENCHMARK",
            "role": "EXTERNAL_BENCHMARK",
            "include_by_default": False,
            "genus": "Genus beta",
            "cohort": "EXTERNAL_BENCHMARK",
            "assembly_state": "PASS",
            "assembly_reason": "NONE_RECORDED",
        },
    ]
    normalized, receipt = validate_cohort_manifest(
        rows, selected_optional_identities=["SYN-ASSEMBLY-HOLD", "SYN-BENCHMARK"]
    )
    assert receipt["default_study_count"] == 1
    assert receipt["assembly_default_off_count"] == 1
    assert receipt["selected_optional_count"] == 2
    held = next(row for row in normalized if row["identity"] == "SYN-ASSEMBLY-HOLD")
    assert held["selected_optional"] is True
    assert held["study_denominator_member"] is False
    invalid = [dict(rows[2], include_by_default=True)]
    with pytest.raises(FigurePolicyError, match="FIGURE_EXTERNAL_ROLE_DEFAULT_ON"):
        validate_cohort_manifest(invalid)


def test_accessible_cohort_palette_is_distinct_and_solid_by_default():
    receipt = validate_cohort_palette(COHORT_PALETTE)
    assert receipt["fill_mode"] == "SOLID"
    assert receipt["bee_wasp_rgb_distance"] >= 60
    with pytest.raises(FigurePolicyError, match="FIGURE_PATTERN_NOT_OWNER_AUTHORIZED"):
        validate_cohort_palette(COHORT_PALETTE, hatches={"ATTINE": "//"})


def test_heatmap_scale_separates_other_and_robustly_caps_extremes():
    rows = [
        {"category": "named-a", "value": 1},
        {"category": "named-b", "value": 2},
        {"category": "named-c", "value": 3},
        {"category": "named-d", "value": 100},
        {"category": "OTHER", "value": 1000},
    ]
    receipt = plan_heatmap_scale(
        rows,
        value_field="value",
        category_field="category",
        lower_quantile=0.0,
        upper_quantile=0.75,
    )
    assert receipt["raw_maximum"] == 1000
    assert receipt["separated_value_count"] == 1
    assert receipt["normalization_maximum"] < 100
    assert receipt["clipped_high_count"] == 1
    assert receipt["raw_values_preserved"] is True


def _write_png_header(path, width: int, height: int) -> None:
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + struct.pack(">II", width, height))


def test_low_resolution_raster_enlarged_for_pdf_is_rejected(tmp_path):
    thumbnail = tmp_path / "thumbnail.png"
    _write_png_header(thumbnail, 600, 400)
    with pytest.raises(FigurePolicyError, match="FIGURE_EFFECTIVE_DPI_INSUFFICIENT"):
        validate_publication_artwork(
            thumbnail,
            profile="DOUBLE_COLUMN",
            embedded_width_in=7.2,
            plot_minimum_text_pt=8,
            caption_text_pt=9,
        )


def test_live_text_vector_is_preserved_and_pdf_screenshot_is_never_source_artwork(tmp_path):
    svg = tmp_path / "figure.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="700" height="400">'
        '<rect x="0" y="0" width="700" height="400" fill="#ffffff"/>'
        '<text x="20" y="40" font-size="16">Readable label</text></svg>',
        encoding="utf-8",
    )
    receipt = validate_publication_artwork(
        svg, profile="SINGLE_COLUMN", plot_minimum_text_pt=8, caption_text_pt=9
    )
    assert receipt["artwork_type"] == "VECTOR_SVG"
    assert receipt["vector_preserved"] is True
    assert receipt["live_text"] is True
    with pytest.raises(FigurePolicyError, match="FIGURE_PDF_SCREENSHOT_NOT_SOURCE_ARTWORK"):
        validate_publication_artwork(
            svg,
            profile="SINGLE_COLUMN",
            source_kind="PDF_REVIEW_SCREENSHOT",
        )


def test_single_and_double_column_profiles_enforce_text_and_caption_scale():
    for profile in ("SINGLE_COLUMN", "DOUBLE_COLUMN"):
        assert validate_publication_profile(
            profile, plot_minimum_text_pt=8, caption_text_pt=9
        )["status"] == "PASS"
        with pytest.raises(FigurePolicyError, match="FIGURE_TEXT_TOO_SMALL_AT_PHYSICAL_SIZE"):
            validate_publication_profile(
                profile, plot_minimum_text_pt=7.5, caption_text_pt=8.5
            )
    with pytest.raises(FigurePolicyError, match="FIGURE_CAPTION_SCALE_DOMINATES_PLOT"):
        validate_publication_profile(
            "SINGLE_COLUMN", plot_minimum_text_pt=8, caption_text_pt=11
        )


def test_layout_gate_rejects_touching_labels_and_overflow():
    assert validate_layout_rectangles(
        [
            {"id": "a", "x0": 1, "y0": 1, "x1": 10, "y1": 5},
            {"id": "b", "x0": 12, "y0": 1, "x1": 20, "y1": 5},
        ],
        canvas_width_px=30,
        canvas_height_px=10,
    )["status"] == "PASS"
    with pytest.raises(FigurePolicyError, match="FIGURE_LAYOUT_COLLISION"):
        validate_layout_rectangles(
            [
                {"id": "a", "x0": 1, "y0": 1, "x1": 10, "y1": 5},
                {"id": "b", "x0": 10, "y0": 1, "x1": 20, "y1": 5},
            ],
            canvas_width_px=30,
            canvas_height_px=10,
        )
    with pytest.raises(FigurePolicyError, match="FIGURE_LAYOUT_OVERFLOW"):
        validate_layout_rectangles(
            [{"id": "a", "x0": 1, "y0": 1, "x1": 31, "y1": 5}],
            canvas_width_px=30,
            canvas_height_px=10,
        )


def test_tick_label_gate_rejects_data_intrusion_and_touching():
    data_rectangles = [
        {"id": "panel-a-data", "axis_id": "panel-a", "x0": 100, "y0": 100, "x1": 280, "y1": 190}
    ]
    receipt = validate_tick_label_data_clearance(
        [
            {"id": "x-tick", "axis_id": "panel-a", "x0": 120, "y0": 70, "x1": 160, "y1": 90},
            {"id": "y-tick", "axis_id": "panel-a", "x0": 50, "y0": 120, "x1": 90, "y1": 140},
        ],
        data_rectangles,
        canvas_width_px=300,
        canvas_height_px=200,
        minimum_clearance_px=1,
    )
    assert receipt["status"] == "PASS"
    assert receipt["tick_label_rectangle_count"] == 2
    assert receipt["axis_ids"] == ["panel-a"]

    with pytest.raises(FigurePolicyError, match="FIGURE_LAYOUT_TICK_DATA_INTRUSION"):
        validate_tick_label_data_clearance(
            [{"id": "intruding", "axis_id": "panel-a", "x0": 120, "y0": 90, "x1": 160, "y1": 110}],
            data_rectangles,
            canvas_width_px=300,
            canvas_height_px=200,
        )
    with pytest.raises(FigurePolicyError, match="FIGURE_LAYOUT_TICK_DATA_INTRUSION"):
        validate_tick_label_data_clearance(
            [{"id": "touching", "axis_id": "panel-a", "x0": 120, "y0": 80, "x1": 160, "y1": 100}],
            data_rectangles,
            canvas_width_px=300,
            canvas_height_px=200,
        )


def test_tick_label_gate_fails_closed_on_unbound_axis():
    with pytest.raises(FigurePolicyError, match="FIGURE_LAYOUT_TICK_AXIS_UNBOUND"):
        validate_tick_label_data_clearance(
            [{"id": "x-tick", "axis_id": "missing", "x0": 10, "y0": 10, "x1": 20, "y1": 20}],
            [{"id": "panel-a-data", "axis_id": "panel-a", "x0": 100, "y0": 100, "x1": 280, "y1": 190}],
            canvas_width_px=300,
            canvas_height_px=200,
        )
    with pytest.raises(FigurePolicyError, match="FIGURE_LAYOUT_CLEARANCE_INVALID"):
        validate_tick_label_data_clearance(
            [],
            [{"id": "panel-a-data", "axis_id": "panel-a", "x0": 100, "y0": 100, "x1": 280, "y1": 190}],
            canvas_width_px=300,
            canvas_height_px=200,
            minimum_clearance_px=-1,
        )
