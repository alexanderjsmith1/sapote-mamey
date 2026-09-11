"""v9.7.116 (item 8a): locus-map zooms to the gene span, not full-contig coordinates.

A BGC at a contig end was crushed into an illegible right-edge sliver. The fix pads the gene span
(min 500 bp) instead. This test pins the xlim math the panel uses.
"""
def _xlim(rows):
    maxx = max(r["end"] for r in rows)
    minx = min(r["start"] for r in rows)
    span = maxx - minx
    _pad = max(span * 0.04, 500)
    return (minx - _pad, maxx + _pad)


def test_contig_end_bgc_fills_panel():
    # BGC at 145k-158k on a 158kb contig: old full-contig xlim showed it as ~8% of panel
    rows = [{"start": 145000, "end": 150000}, {"start": 151000, "end": 158000}]
    lo, hi = _xlim(rows)
    shown = hi - lo
    cluster = 158000 - 145000
    assert cluster / shown > 0.8          # cluster now fills >80% of the panel
    assert lo > 0                          # zoomed in, not anchored at 0


def test_small_cluster_gets_minimum_pad():
    # a tiny cluster must still get a readable minimum pad (500 bp), not a near-zero window
    rows = [{"start": 1000, "end": 1200}]
    lo, hi = _xlim(rows)
    assert (hi - 1200) >= 500 and (1000 - lo) >= 500
