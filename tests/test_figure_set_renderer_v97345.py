"""v9.7.345 next-cut candidate: first 20 governed Codex figure sets."""

from __future__ import annotations

import json
import sys
from xml.etree import ElementTree as ET

import pytest

from mamey.figure_policy import FigurePolicyError
from mamey.figure_policy import CAPTION_METHOD_SCHEMA
from mamey.interactive_figures.figure_set_renderer import IMPLEMENTED_IDS, render_tranche
from mamey.interactive_figures.figure_set_registry import GLOBAL_CLAIM_CEILING, PROFILE


def _widget_data():
    strains = {}
    for index, sid in enumerate(("SYN-1", "SYN-2", "SYN-3", "SYN-4"), 1):
        strains[sid] = {
            "governance": "GOVERNED" if sid != "SYN-4" else "AUDIT_ONLY_QUARANTINED",
            "bgcRows": 10 + index,
            "uniquePhysicalGenes": 1000 + index * 50,
            "machineryGenes": 300 + index * 15,
            "classes": {
                "PKS": {"total": 5 + index, "edge": index, "full": 3, "interior": 1},
                "NRPS": {"total": 4 + index, "edge": 1, "full": 2, "interior": 1},
                "RiPP": {"total": 2 + index, "edge": 1, "full": 1, "interior": index - 1},
            },
            "machinery": {
                "Biosynthetic core": [200 + index, 300 + index, 1200 + index],
                "Biosynthetic additional": [250 + index, 350 + index],
                "Resistance": [400 + index], "Transport": [300 + index],
                "Regulatory": [150 + index],
            },
            "hostContext": {"group": ("BEE", "ATTINE_ANT", "UNRESOLVED", "BEE")[index - 1]},
        }
    return {"meta": {"sourceRelease": "synthetic-test"}, "strains": strains}


def test_tranche_renders_20_svg_data_and_caption_sets(tmp_path):
    source = tmp_path / "widget.json"
    source.write_text(json.dumps(_widget_data()), encoding="utf-8")
    out = tmp_path / "out"
    receipt = render_tranche(source, out)
    assert receipt["status"] == "PASS"
    assert receipt["implemented_count"] == 20
    assert receipt["caption_schema_version"] == CAPTION_METHOD_SCHEMA
    assert tuple(receipt["implemented_ids"]) == IMPLEMENTED_IDS
    assert receipt["governed_strains"] == 3
    assert receipt["all_packaged_strains"] == 4
    assert receipt["native_svg_rasterization"]["svg_render_path"] == "DIRECT_DETERMINISTIC_SVG"
    assert receipt["machine_checks"]
    assert all(check["status"] == "PASS" for check in receipt["machine_checks"])
    assert len(receipt["preflight_receipts"]) == 20
    assert len(receipt["caption_validation_receipts"]) == 20
    assert len(receipt["genus_validation_receipts"]) == 20
    assert all(item["status"] == "PASS" for item in receipt["preflight_receipts"])
    fs047 = next(item for item in receipt["preflight_receipts"] if item["figure_set_id"] == "FS047")
    assert fs047["allow_all_zero"] is True
    assert "display ceiling" in fs047["all_zero_meaning"]
    assert all(item["status"] == "PASS" for item in receipt["caption_validation_receipts"].values())
    assert all(item["scope"] == "NOT_APPLICABLE" for item in receipt["genus_validation_receipts"].values())
    assert len(list((out / "figures").glob("*.svg"))) == 20
    assert len(list((out / "data").glob("*.csv"))) == 20
    assert len(list((out / "text").glob("*.md"))) == 20
    for svg in (out / "figures").glob("*.svg"):
        ET.parse(svg)
    assert (out / "OPEN_FIGURE_SET_TRANCHE_1.html").exists()
    assert (out / "TRANCHE_1_QA_RECEIPT.json").exists()
    caption_text = (out / "text" / "FS001_CAPTION_METHODS.md").read_text(encoding="utf-8")
    for label in (
        "Caption schema", "Figure question", "Source and release", "Source bindings", "Unit of analysis",
        "Inclusion, exclusion, and roles", "Denominators", "Per-group denominators", "Typed missingness",
        "Benchmark sensitivity", "Transformation and counting rule", "Visual grammar", "Statistics and uncertainty",
        "Comparison group", "Genus control", "Contradictions and limitations", "Interpretation boundary",
    ):
        assert f"**{label}.**" in caption_text
    assert f"**Caption schema.** {CAPTION_METHOD_SCHEMA}" in caption_text
    assert "study_strains=3" in caption_text
    assert "plotted_rows=3" in caption_text
    assert "grouping=class" in caption_text


def test_receipt_names_available_cairosvg_path(tmp_path, monkeypatch):
    class WorkingCairoSVG:
        @staticmethod
        def svg2png(**_kwargs):
            return b"\x89PNG\r\n\x1a\nsynthetic"

    monkeypatch.setitem(sys.modules, "cairosvg", WorkingCairoSVG)
    source = tmp_path / "widget.json"
    source.write_text(json.dumps(_widget_data()), encoding="utf-8")
    receipt = render_tranche(source, tmp_path / "out")
    assert receipt["native_svg_rasterization"] == {
        "state": "AVAILABLE_CAIROSVG",
        "svg_render_path": "DIRECT_DETERMINISTIC_SVG",
        "png_pair_path": "CAIROSVG",
        "error_type": "",
    }


def test_receipt_names_svg_only_path_when_native_cairo_fails(tmp_path, monkeypatch):
    class BrokenCairoSVG:
        @staticmethod
        def svg2png(**_kwargs):
            raise OSError("native cairo unavailable")

    monkeypatch.setitem(sys.modules, "cairosvg", BrokenCairoSVG)
    source = tmp_path / "widget.json"
    source.write_text(json.dumps(_widget_data()), encoding="utf-8")
    out = tmp_path / "out"
    receipt = render_tranche(source, out)
    assert receipt["status"] == "PASS"
    assert receipt["native_svg_rasterization"] == {
        "state": "NATIVE_SVG_UNAVAILABLE",
        "svg_render_path": "DIRECT_DETERMINISTIC_SVG",
        "png_pair_path": "NOT_EMITTED",
        "error_type": "OSError",
    }
    assert len(list((out / "figures").glob("*.svg"))) == 20


def test_svg_canvas_has_no_governance_or_claim_footer(tmp_path):
    source = tmp_path / "widget.json"
    source.write_text(json.dumps(_widget_data()), encoding="utf-8")
    out = tmp_path / "out"
    render_tranche(source, out)
    for svg_path in (out / "figures").glob("*.svg"):
        text = svg_path.read_text(encoding="utf-8")
        assert GLOBAL_CLAIM_CEILING not in text
        assert PROFILE not in text
    caption = (out / "text" / "FS001_CAPTION_METHODS.md").read_text(encoding="utf-8")
    assert GLOBAL_CLAIM_CEILING in caption
    review_html = (out / "OPEN_FIGURE_SET_TRANCHE_1.html").read_text(encoding="utf-8")
    assert '<div class="caption"><strong>Caption.</strong>' in review_html


def test_one_strain_scatter_refuses_before_output_creation(tmp_path):
    payload = _widget_data()
    payload["strains"] = {"SYN-1": payload["strains"]["SYN-1"]}
    source = tmp_path / "widget.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "out"
    with pytest.raises(FigurePolicyError, match="FIGURE_SCATTER_TOO_FEW_POINTS"):
        render_tranche(source, out)
    assert not out.exists()


def test_incomplete_caption_contract_refuses_before_output_creation(tmp_path, monkeypatch):
    from mamey.interactive_figures import figure_set_renderer as renderer

    original = renderer.build_registry

    def broken_registry():
        rows = original()
        rows[0] = {**rows[0], "scientific_question": ""}
        return rows

    monkeypatch.setattr(renderer, "build_registry", broken_registry)
    source = tmp_path / "widget.json"
    source.write_text(json.dumps(_widget_data()), encoding="utf-8")
    out = tmp_path / "out"
    # Other full-suite modules deliberately reload mamey.figure_policy, so use
    # the stable ValueError base rather than depending on class identity.
    with pytest.raises(ValueError, match="FIGURE_CAPTION_METHODS_INCOMPLETE"):
        renderer.render_tranche(source, out)
    assert not out.exists()


def test_strain_scatter_embeds_adjacent_labels(tmp_path):
    source = tmp_path / "widget.json"
    source.write_text(json.dumps(_widget_data()), encoding="utf-8")
    out = tmp_path / "out"
    render_tranche(source, out)
    for figure_id in ("FS002", "FS010", "FS042", "FS050"):
        svg = (out / "figures" / f"{figure_id}.svg").read_text(encoding="utf-8")
        for sid in ("SYN-1", "SYN-2", "SYN-3"):
            assert sid in svg


def test_all_zero_state_heatmap_requires_explicit_registered_semantics(tmp_path, monkeypatch):
    from mamey.interactive_figures import figure_set_renderer as renderer

    original = renderer.build_charts

    def missing_contract(payload, all_ids, governed):
        charts = original(payload, all_ids, governed)
        index = next(i for i, chart in enumerate(charts) if chart.figure_id == "FS054")
        chart = charts[index]
        rows = [{**row, "state": "OBSERVED_ZERO", "value": 0} for row in chart.rows]
        config = {key: value for key, value in chart.config.items() if not key.startswith("all_zero_")}
        charts[index] = renderer.Chart(chart.figure_id, chart.kind, chart.title, chart.subtitle, rows, config)
        return charts

    monkeypatch.setattr(renderer, "build_charts", missing_contract)
    source = tmp_path / "widget.json"
    source.write_text(json.dumps(_widget_data()), encoding="utf-8")
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="FIGURE_ALL_ZERO_SEMANTICS_INVALID"):
        renderer.render_tranche(source, out)
    assert not out.exists()


def test_external_benchmark_is_default_off_and_opt_in_comparison_only(tmp_path):
    payload = _widget_data()
    benchmark = dict(payload["strains"]["SYN-1"])
    benchmark["cohort_role"] = "EXTERNAL_BENCHMARK"
    benchmark["include_by_default"] = False
    benchmark["classes"] = {"BENCH_ONLY": {"total": 7, "edge": 0, "full": 7, "interior": 0}}
    payload["strains"]["SYN-BENCHMARK-1"] = benchmark
    source = tmp_path / "widget.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    default_out = tmp_path / "default"
    default_receipt = render_tranche(source, default_out)
    assert default_receipt["governed_strains"] == 3
    assert default_receipt["all_packaged_strains"] == 4
    assert default_receipt["source_strains"] == 5
    assert default_receipt["external_benchmarks"] == {
        "available": ["SYN-BENCHMARK-1"], "selected": [], "default_off": True,
    }
    assert not any(
        "SYN-BENCHMARK-1" in path.read_text(encoding="utf-8")
        for path in (default_out / "figures").glob("*.svg")
    )
    default_rows = (default_out / "data" / "FS015_data.csv").read_text(encoding="utf-8")
    assert "BENCH_ONLY" not in default_rows

    selected_out = tmp_path / "selected"
    selected_receipt = render_tranche(
        source, selected_out, external_benchmark_ids=["SYN-BENCHMARK-1"]
    )
    assert selected_receipt["governed_strains"] == 3
    assert selected_receipt["all_packaged_strains"] == 5
    assert selected_receipt["external_benchmarks"]["selected"] == ["SYN-BENCHMARK-1"]
    selected_rows = (selected_out / "data" / "FS015_data.csv").read_text(encoding="utf-8")
    assert "BENCH_ONLY,0,7" in selected_rows
    caption = (selected_out / "text" / "FS015_CAPTION_METHODS.md").read_text(encoding="utf-8")
    assert "External benchmarks never enter study n or percentages" in caption
    assert "available=1 (SYN-BENCHMARK-1); selected=1 (SYN-BENCHMARK-1); default_off=true" in caption
    host_caption = (selected_out / "text" / "FS005_CAPTION_METHODS.md").read_text(encoding="utf-8")
    assert "grouping=host" in host_caption
    assert "BEE(rows=1; strains=1; memberships=6)" in host_caption


def test_external_benchmark_contract_refuses_default_on_and_unknown_selection(tmp_path):
    payload = _widget_data()
    benchmark = dict(payload["strains"]["SYN-1"])
    benchmark["cohort_role"] = "EXTERNAL_BENCHMARK"
    benchmark["include_by_default"] = True
    payload["strains"]["SYN-BENCHMARK-1"] = benchmark
    source = tmp_path / "widget.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="FIGURE_EXTERNAL_BENCHMARK_DEFAULT_ON"):
        render_tranche(source, tmp_path / "default-on")
    assert not (tmp_path / "default-on").exists()

    source.write_text(json.dumps(_widget_data()), encoding="utf-8")
    with pytest.raises(ValueError, match="FIGURE_EXTERNAL_BENCHMARK_SELECTION_INVALID"):
        render_tranche(source, tmp_path / "unknown", external_benchmark_ids=["SYN-BENCHMARK-1"])


def test_rate_denominator_contracts_bind_every_current_percentage_or_rate_family():
    from mamey.interactive_figures import figure_set_renderer as renderer

    payload = _widget_data()
    charts = {
        chart.figure_id: chart
        for chart in renderer.build_charts(payload, ["SYN-1", "SYN-2", "SYN-3", "SYN-4"], ["SYN-1", "SYN-2", "SYN-3"])
    }
    expected = {
        "FS001": ("memberships", "BGC-class memberships"),
        "FS002": ("pk_memberships", "PKS class memberships"),
        "FS003": ("n", "BGC-class memberships"),
        "FS005": ("memberships", "PKS class memberships"),
        "FS007": ("memberships", "PKS class memberships"),
        "FS041": ("role_genes", "deduplicated machinery-role genes"),
        "FS047": ("genes", "deduplicated machinery-role genes"),
        "FS050": ("unique_physical_genes", "unique physical CDS"),
        "FS053": ("unique_physical_genes", "unique physical CDS"),
    }
    for figure_id, (field, unit) in expected.items():
        chart = charts[figure_id]
        summary = renderer._group_denominator_summary(chart)
        assert f"denominator_field={field}" in summary
        assert f"denominator_unit={unit}" in summary
        assert all(field in row for row in chart.rows)
    assert "pk_memberships=" in renderer._group_denominator_summary(charts["FS002"])
    assert "unique_physical_genes=" in renderer._group_denominator_summary(charts["FS050"])

    fs002 = charts["FS002"]
    missing_contract = renderer.Chart(
        fs002.figure_id, fs002.kind, fs002.title, fs002.subtitle, fs002.rows,
        {key: value for key, value in fs002.config.items() if not key.startswith("rate_denominator_")},
    )
    with pytest.raises(ValueError, match="FIGURE_CAPTION_RATE_DENOMINATOR_CONTRACT_MISSING"):
        renderer._group_denominator_summary(missing_contract)

    fs050 = charts["FS050"]
    missing_field = renderer.Chart(
        fs050.figure_id, fs050.kind, fs050.title, fs050.subtitle,
        [{key: value for key, value in row.items() if key != "unique_physical_genes"} for row in fs050.rows],
        fs050.config,
    )
    with pytest.raises(ValueError, match="FIGURE_CAPTION_RATE_DENOMINATOR_FIELD_MISSING"):
        renderer._group_denominator_summary(missing_field)


def test_typed_missingness_counts_partial_state_coverage_against_all_rows():
    from mamey.interactive_figures import figure_set_renderer as renderer

    chart = renderer.Chart(
        "GEN-MIXED", "bar", "Generic", "Generic rows",
        [{"role": "A", "state": "POPULATED", "value": 1}, {"role": "A", "value": 2}],
        {},
    )
    summary = renderer._typed_missingness_summary(chart)
    assert "plotted_rows=2" in summary
    assert "typed_rows=1" in summary
    assert "rows_missing_state_key=1" in summary
    assert "state=POPULATED: 1" in summary


def test_contradictory_benchmark_caption_refuses_before_output_creation(tmp_path, monkeypatch):
    from mamey.interactive_figures import figure_set_renderer as renderer

    original = renderer._caption_metadata

    def contradictory(*args, **kwargs):
        metadata = original(*args, **kwargs)
        metadata["benchmark_sensitivity"] = (
            "available=1; selected=0; default_off=false; benchmark pooled into study n and percentages"
        )
        return metadata

    monkeypatch.setattr(renderer, "_caption_metadata", contradictory)
    source = tmp_path / "widget.json"
    source.write_text(json.dumps(_widget_data()), encoding="utf-8")
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="FIGURE_CAPTION_BENCHMARK_SENSITIVITY_INVALID"):
        renderer.render_tranche(source, out)
    assert not out.exists()
    assert not (tmp_path / "unknown").exists()


def test_shared_loader_preserves_four_value_contract(tmp_path):
    from mamey.interactive_figures.figure_set_renderer import _load

    source = tmp_path / "widget.json"
    source.write_text(json.dumps(_widget_data()), encoding="utf-8")
    loaded = _load(source)
    assert len(loaded) == 4
    _, _, all_ids, governed = loaded
    assert all_ids == ["SYN-1", "SYN-2", "SYN-3", "SYN-4"]
    assert governed == ["SYN-1", "SYN-2", "SYN-3"]


def test_cli_parser_registers_render_command():
    from mamey.cli import build_parser

    args = build_parser().parse_args([
        "codex-figure-sets", "--widget-data", "widget.json", "--outdir", "figures"
    ])
    assert args.command == "codex-figure-sets"
