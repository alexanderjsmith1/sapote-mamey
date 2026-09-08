"""v9.7.408 — governance-sensitivity panels (FS167 / FS175 family) must compare equal locus eligibility.

Codex hostile audit 2026-09-04, Q3, confirmed in the sealed .407 engine: `_build_metric_charts` drops
`lead_excluded` rows from the governed arm for PRI/NOV (v9.7.374) but built `all_family` from the raw
rows, so the "all packaged" arm kept standing-rule / primary-metabolism loci the governed arm had
excluded. Same roster, different eligibility: a zero-delta panel was not evidence of anything and a
non-zero delta was an artefact. Contract now: identical eligibility on both arms; with the whole roster
governed, the two medians are equal."""
from __future__ import annotations

from mamey.interactive_figures.figure_set_renderer_tranche5 import METRICS, _build_metric_charts

PRI = next(m for m in METRICS if m.code == "PRI")


def _row(strain, bgc, value, excluded=False):
    return {"family": "PRI", "strain": strain, "governance": "GOVERNED", "host_group": "bee",
            "bgc_id": bgc, "boundary": "complete", "products": "nrps", "value": value,
            "state": "POPULATED", "ab_auto": value, "af_auto": value, "lead_excluded": excluded}


def _fixture():
    strains = ["S1", "S2"]
    rows = [_row("S1", "BGC001", 1.0), _row("S1", "BGC002", 2.0), _row("S2", "BGC001", 3.0),
            # a primary-metabolism-flagged locus with an outlying prior: excluded from leads
            _row("S2", "BGC009", 99.0, excluded=True)]
    memberships = [{"strain": r["strain"], "bgc_id": r["bgc_id"], "product_class": "NRPS"} for r in rows]
    strain_records = {s: {"strain": s, "host_group": "bee", "host": "bee"} for s in strains}
    return rows, memberships, strain_records, strains


def _sensitivity_chart(charts):
    hits = [c for c in charts if "governance sensitivity" in c.title]
    assert len(hits) == 1, [c.title for c in charts]
    return hits[0]


def test_whole_roster_governed_gives_equal_arms():
    rows, memberships, strain_records, strains = _fixture()
    chart = _sensitivity_chart(_build_metric_charts(PRI, rows, memberships, strain_records, strains))
    for r in chart.rows:
        assert r["governed"] == r["all_packaged"], (
            f"class {r['class']}: governed {r['governed']} vs all_packaged {r['all_packaged']} — the arms "
            "differ in locus eligibility, not cohort membership (Codex Q3)")


def test_excluded_locus_is_out_of_both_arms():
    rows, memberships, strain_records, strains = _fixture()
    chart = _sensitivity_chart(_build_metric_charts(PRI, rows, memberships, strain_records, strains))
    nrps = next(r for r in chart.rows if r["class"] == "NRPS")
    assert nrps["all_packaged"] == 2.0, "median of 1,2,3 — the 99.0 excluded locus must not be in the all-packaged arm"
