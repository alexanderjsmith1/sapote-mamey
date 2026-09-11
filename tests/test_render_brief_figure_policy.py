"""render_brief figure migration (W1–W3, W13): the landscape renderer must obey the shared figure policy
and conserve all rows in the data CSV.

This is the conformance test the migration was missing — if the renderer stops calling omit_saccharides, or
silently caps rows out of the CSV, this fails. Guards against the policy/renderer drift the audits flagged.
"""
import csv
import pytest
from mamey.render_brief import _setup_mpl, fig_landscape


def _prov_read(path):
    """Read a figure data CSV, skipping the # provenance row at row 0 (Item-18)."""
    import csv as _csv
    with open(path, newline="") as f:
        rows = list(_csv.reader(f))
    if rows and rows[0] and rows[0][0] == "# provenance":
        headers, data = rows[1], rows[2:]
    else:
        headers, data = rows[0], rows[1:]
    return [dict(zip(headers, row)) for row in data]



def _row(bid, products, ab=50, tier="High"):
    return {"rank": bid[-1], "bgc_id": bid, "contig": "c1", "region": f"r{bid[-1]}", "products": products,
            "boundary": "Interior", "arch": "A", "ab": ab, "af": 20, "novelty": 30, "lead_tier": tier,
            "kcb_top": "", "kcb_score": "", "cctt": ""}


def test_pure_saccharide_omitted_from_figure_but_kept_in_csv(tmp_path):
    plt = _setup_mpl()
    rows = [_row("BGC001", "NRPS"), _row("BGC002", "saccharide", tier="Medium")]
    png = str(tmp_path / "land.png")
    fig_landscape(rows, png, "TestStrain", plt)
    out = {r["bgc_id"]: r for r in _prov_read(png.replace(".png", "_data.csv"))}
    assert len(out) == 2, "all rows must be conserved in the data CSV"
    # pure saccharide: flagged + NOT shown (policy applied)
    assert out["BGC002"]["suppressed_saccharide_only"] == "True"
    assert out["BGC002"]["shown_in_figure"] == "False"
    # non-saccharide: shown + not flagged
    assert out["BGC001"]["suppressed_saccharide_only"] == "False"
    assert out["BGC001"]["shown_in_figure"] == "True"


def test_saccharide_with_real_class_is_not_suppressed(tmp_path):
    plt = _setup_mpl()
    rows = [_row("BGC001", "NRPS; saccharide")]   # tailoring saccharide arm on a real class -> kept
    png = str(tmp_path / "land.png")
    fig_landscape(rows, png, "S", plt)
    out = {r["bgc_id"]: r for r in _prov_read(png.replace(".png", "_data.csv"))}
    assert out["BGC001"]["suppressed_saccharide_only"] == "False"
    assert out["BGC001"]["shown_in_figure"] == "True"


def test_cap_conserves_all_rows_in_csv(tmp_path):
    plt = _setup_mpl()
    rows = [_row(f"BGC{i:03d}", "NRPS", ab=100 - i) for i in range(1, 51)]   # 50 non-saccharide leads
    png = str(tmp_path / "land.png")
    fig_landscape(rows, png, "S", plt)
    out = list(_prov_read(png.replace(".png", "_data.csv")))
    assert len(out) == 50, "the CSV must carry ALL rows, not the 40-row figure cap"
    shown = [r for r in out if r["shown_in_figure"] == "True"]
    assert len(shown) == 40, "the figure caps at 40 but the CSV does not"
