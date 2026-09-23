"""Missing summaries must survive through plotted rows and SVG marks."""
from xml.etree import ElementTree as ET
import pytest
from mamey.interactive_figures.figure_set_renderer import Chart, render_svg
from mamey.interactive_figures.figure_set_renderer_tranche5 import METRICS, _build_metric_charts

NS = {"s": "http://www.w3.org/2000/svg"}

def fixture(code):
    rows, memberships, strains = [], [], {}
    for sid, value, state in [("SYNTH_EMPTY", "", "MISSING"), ("SYNTH_ZERO", 0, "OBSERVED_ZERO"), ("SYNTH_VALUE", 8, "POPULATED")]:
        identity = dict(strain=sid, contig="synthetic_contig_1", region="region001", bgc_id="synthetic_locus")
        rows.append(dict(identity, family=code, governance="GOVERNED", host_group="bee", boundary="Interior", products="test", value=value, state=state, ab_auto=value, af_auto=value, lead_excluded=False))
        memberships.append(dict(identity, product_class=sid))
        strains[sid] = {"host": "bee", "host_group": "bee"}
    return rows, memberships, strains

@pytest.mark.parametrize("code", [m.code for m in METRICS if m.code != "ACT"])
def test_missing_summaries_are_null_and_measured_zero_is_retained(code):
    rows, members, strains = fixture(code)
    metric = next(m for m in METRICS if m.code == code)
    charts = _build_metric_charts(metric, rows, members, strains, list(strains))
    scatter = charts[1]
    assert scatter.rows[0]["y_value"] is None
    assert scatter.rows[1]["y_value"] == 0
    heat = charts[2]
    assert all(r["value"] is None for r in heat.rows if r["class"] == "SYNTH_EMPTY")
    assert all(r["value"] == 0 for r in heat.rows if r["class"] == "SYNTH_ZERO")
    paired = charts[6]
    empty = next(r for r in paired.rows if r["class"] == "SYNTH_EMPTY")
    assert empty["governed"] is None and empty["all_packaged"] is None
    assert next(r for r in charts[3].rows if r["boundary"] == "Edge")["median"] is None
    for chart in charts:
        ET.fromstring(render_svg(chart))
    svg = ET.fromstring(render_svg(scatter))
    marks = svg.findall(".//s:circle", NS)
    assert len(marks) == 2
    assert "SYNTH_EMPTY" in "".join(svg.itertext())
    assert "not plotted" in "".join(svg.itertext())


def test_paired_missing_arm_has_no_false_zero_or_connector():
    chart = Chart("TEST", "paired_dot", "Missing arm", "", [{"class": "test", "a": None, "b": 5}], {"category": "class", "a": "a", "b": "b", "a_label": "A", "b_label": "B"})
    svg = ET.fromstring(render_svg(chart))
    assert len(svg.findall(".//s:line", NS)) == 0
    # One data mark and two legend marks.
    assert len(svg.findall(".//s:circle", NS)) == 3
    assert "A: missing" in "".join(svg.itertext())


def test_empty_range_draws_label_without_measurement():
    chart = Chart("TEST", "dot_range", "Missing range", "", [{"group": "test", "lo": None, "mid": None, "hi": None}], {"category": "group", "low": "lo", "mid": "mid", "high": "hi", "x_label": "value"})
    svg = ET.fromstring(render_svg(chart))
    assert not svg.findall(".//s:circle", NS)
    assert "missing" in "".join(svg.itertext())


def test_declared_missing_state_suppresses_stale_routing_numbers():
    rows, members, strains = fixture("PRI")
    rows[0].update(ab_auto=99, af_auto=99)
    charts = _build_metric_charts(next(m for m in METRICS if m.code == "PRI"), rows, members, strains, list(strains))
    assert charts[1].rows[0]["x_value"] is None
    assert charts[1].rows[0]["y_value"] is None


def test_null_summary_round_trips_to_blank_csv_without_losing_zero(tmp_path):
    import csv
    from mamey.interactive_figures.figure_set_renderer import _write_rows
    rows, members, strains = fixture("LEN")
    chart = _build_metric_charts(next(m for m in METRICS if m.code == "LEN"), rows, members, strains, list(strains))[1]
    out = tmp_path / "data.csv"
    _write_rows(out, chart.rows)
    with out.open() as stream:
        saved = list(csv.DictReader(stream))
    assert saved[0]["y_value"] == ""
    assert float(saved[1]["y_value"]) == 0
