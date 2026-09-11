"""v9.7.48 — lower-priority backlog: B-2 (release in intake.json), B-3 (composition figure companion CSV),
F-6 (degenerate organism string normalization)."""
import csv
import os

from mamey.cohort_resolver import normalize_taxonomy


# ---- F-6: degenerate-organism normalization -------------------------------
def test_f6_degenerate_taxonomy_becomes_sp():
    # the AS GBKs carry `ORGANISM  .` -> a "." organism must not propagate
    for bad in (".", "", "   ", "...", "  . "):
        assert normalize_taxonomy(bad) == "sp."


def test_f6_real_binomial_unchanged():
    for good in ("Streptomyces sp.", "Pseudonocardia sp.", "Amycolatopsis orientalis",
                 "Candidatus Saccharibacteria"):
        assert normalize_taxonomy(good) == good


# ---- B-3: composition figure writes its companion data CSV -----------------
def test_b3_fig_composition_emits_data_csv(tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mamey.render_brief import fig_composition
    rows = [
        {"products": "NRPS", "boundary": "Interior"},
        {"products": "NRPS;saccharide", "boundary": "Edge"},
        {"products": "terpene", "boundary": "Full-contig"},
        {"products": "saccharide", "boundary": "Interior"},
    ]
    png = str(tmp_path / "S_8b_fig_composition.png")
    fig = fig_composition(rows, png, plt)
    plt.close(fig)
    csv_path = png.replace(".png", "_data.csv")
    assert os.path.exists(csv_path)
    # Item-18 fix: figure data CSVs now have a # provenance row at row 0;
    # read with skiprows=1 semantics.
    with open(csv_path, newline="") as _fcsv:
        _rows = list(csv.reader(_fcsv))
    _headers = _rows[1] if (_rows and _rows[0] and _rows[0][0] == "# provenance") else _rows[0]
    _data = _rows[2:] if (_rows and _rows[0] and _rows[0][0] == "# provenance") else _rows[1:]
    recs = [dict(zip(_headers, row)) for row in _data]
    panels = {r["panel"] for r in recs}
    assert "product_class" in panels and "boundary" in panels
    # all product classes captured (NRPS counted twice, saccharide twice)
    prod = {r["category"]: int(r["count"]) for r in recs if r["panel"] == "product_class"}
    assert prod.get("NRPS") == 2 and prod.get("saccharide") == 2
    bnd = {r["category"]: int(r["count"]) for r in recs if r["panel"] == "boundary"}
    assert bnd == {"Interior": 2, "Edge": 1, "Full-contig": 1}


# ---- B-2: resolve_release feeds the intake tag ----------------------------
def test_b2_release_resolution_for_intake():
    # the value stamped into intake.json is the same resolver result used elsewhere
    from mamey.dedup_and_guard import resolve_release
    assert resolve_release("ST-100", None)[0] in ("PUBLIC", "PRIVATE")
    # a public SID label resolves PUBLIC; the intake tag mirrors it
    assert resolve_release("SID8375", "PUBLIC")[0] == "PUBLIC"
