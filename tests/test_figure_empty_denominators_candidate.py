"""Empty cohorts do not define medians or percentages."""
from pathlib import Path
from xml.etree import ElementTree as ET
from mamey.interactive_figures import figure_set_renderer_tranche3 as t3
from mamey.interactive_figures import figure_set_renderer_tranche5 as t5
from mamey.interactive_figures.figure_set_renderer import render_svg


def test_tranche3_empty_medians_are_not_zero(monkeypatch):
    monkeypatch.setattr(t3, "_read", lambda path: [])
    charts = {c.figure_id: c for c in t3.build_charts_3({"strains": {"SYNTH_EMPTY": {"host": "bee"}}}, ["SYNTH_EMPTY"], ["SYNTH_EMPTY"], Path("unused"))}
    for key, field in [("FS098", "median_distinct_accessions"), ("FS106", "median_kcb_score"), ("FS114", "median_distinct_domains")]:
        assert charts[key].rows[0][field] is None
        ET.fromstring(render_svg(charts[key]))
    for row in charts["FS117"].rows:
        assert row["median"] is None and row["q1"] is None and row["q3"] is None
    ET.fromstring(render_svg(charts["FS117"]))


def test_no_channel_rows_are_not_zero_percent_complete(monkeypatch):
    channels = [{"strain": "SYNTH_ZERO", "channel_group": "test", "channel": "test", "state": "PENDING"}, {"strain": "SYNTH_PASS", "channel_group": "test", "channel": "test", "state": "PASS"}]
    members = [dict(strain=s, contig="synthetic_contig_1", region="region001", bgc_id="synthetic_locus", product_class=s) for s in ("SYNTH_EMPTY", "SYNTH_ZERO", "SYNTH_PASS")]
    monkeypatch.setattr(t5, "_read", lambda path: channels if path.name == "EVIDENCE_CHANNEL_STATES.csv" else [])
    strains = {r["strain"]: {"host": "bee"} for r in members}
    charts = {c.figure_id: c for c in t5._evidence_charts(Path("unused"), members, strains, list(strains))}
    values = {r["class"]: r["value"] for r in charts["FS195"].rows}
    assert values == {"SYNTH_EMPTY": None, "SYNTH_ZERO": 0.0, "SYNTH_PASS": 100.0}
    # Missing cohort member must not depress the median from 50 to zero.
    measured = [r for r in charts["FS197"].rows if r["median"] is not None]
    assert len(measured) == 1 and measured[0]["median"] == 50.0
    for chart in charts.values():
        ET.fromstring(render_svg(chart))


def test_active_site_zero_denominator_remains_missing():
    charts = t5._build_active_site_charts([], [], [], {"SYNTH_EMPTY": {"host": "bee"}}, ["SYNTH_EMPTY"])
    assert charts[1].rows[0]["structurally_unavailable_pct"] is None
    for chart in charts[3:5]:
        assert all(row["percent"] is None for row in chart.rows)
        ET.fromstring(render_svg(chart))
