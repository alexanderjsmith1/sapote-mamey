"""A blank domain-count cell stays blank in the widget data, table, chart and CSV export.

Before this card `_domain_rows` turned a blank cell into 0, so a not-recorded count looked
like a measured zero and fed the row total.
"""
from __future__ import annotations

from mamey.widget_deliverable import _domain_rows, _domains_page

KEYS = ("PKS_KS", "PKS_AT", "PKS_KR", "PKS_DH", "NRPS_C", "NRPS_A", "NRPS_T_PCP", "TE_release")


def test_blank_cell_is_none_not_zero():
    row = _domain_rows([{"bgc_id": "BGC001", "PKS_KS": "", "PKS_AT": "2"}])[0]
    assert row["PKS_KS"] is None
    assert row["PKS_AT"] == 2
    assert row["blank_cells"] == ["PKS_KS"]


def test_total_is_withheld_when_any_cell_is_blank():
    row = _domain_rows([{"bgc_id": "BGC001", "PKS_KS": "", "PKS_AT": "2"}])[0]
    assert row["total"] is None
    assert row["total_recorded_cells_only"] == 2
    assert "PKS_KS" in row["blank_cells"]


def test_recorded_zero_stays_zero_and_full_rows_keep_a_total():
    full = {"bgc_id": "BGC002", **{key: "0" for key in KEYS}, "PKS_KS": "3"}
    row = _domain_rows([full])[0]
    assert row["PKS_AT"] == 0
    assert row["total"] == 3
    assert row["blank_cells"] == []


def test_rows_with_a_blank_total_sort_after_recorded_rows():
    full = {"bgc_id": "BGC002", **{key: "0" for key in KEYS}}
    rows = _domain_rows([{"bgc_id": "BGC001", "PKS_KS": "9", "PKS_AT": ""}, full])
    assert [r["bgc_id"] for r in rows] == ["BGC002", "BGC001"]


def test_page_script_draws_no_bar_and_a_blank_cell_for_a_missing_count():
    html = _domains_page({"meta": {"strain_id": "EXAMPLE", "release": "public", "taxonomy": "Streptomyces sp.", "source": "soil", "workflow_version": "x"}, "domains": [], "priority": [],
                          "domain_coverage": None})
    assert "blank (not recorded)" in html
    assert "cell(r.PKS_KS)" in html
    assert "(+b[k]||0)-(+a[k]||0)" in html  # recorded rows still sort by count


def test_a_column_the_sidecar_does_not_carry_withholds_the_total():
    row = _domain_rows([{"bgc_id": "BGC001", "PKS_KS": "4"}])[0]
    assert row["PKS_AT"] is None
    assert row["total"] is None
    assert row["total_recorded_cells_only"] == 4
    assert row["total_columns"] == ["PKS_KS"]
    assert "PKS_AT" in row["columns_not_in_sidecar"]
    assert row["blank_cells"] == []


def test_a_row_with_none_of_the_domain_columns_has_no_total():
    row = _domain_rows([{"bgc_id": "BGC001", "KS": "4", "AT": "2"}])[0]
    assert row["total"] is None
    assert row["total_columns"] == []
    assert len(row["columns_not_in_sidecar"]) == 8
