"""tools/protein_pcoa_render.py --label-ids (card 018c0f08_455_pcoa_label_ids_locus_pages): label exactly the listed points,
every one of them, with the given text; without the option the existing label rules are unchanged.
Synthetic strains only (tools/test_synthetic_ids.txt)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("protein_pcoa_render", ROOT / "tools" / "protein_pcoa_render.py")
ppr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ppr)

BG = [(i / 10, j / 10) for i in range(5) for j in range(5)]
PTS = [dict(x=x, y=y, strain="SYNTHETIC_REFERENCE_010", pid=pid, row=dict(id=f"i{k}", origin="SYNTHETIC_REFERENCE_010__N1.region001.gbk"))
       for k, (x, y, pid) in enumerate([(2.0, 2.0, 50.0), (0.2, 0.2, 99.0), (0.21, 0.2, 99.0), (1.5, 0.1, 80.0)])]


def test_label_ids_labels_every_listed_point_and_nothing_else():
    ppr.LABEL_IDS.clear(); ppr.LABEL_IDS.update({"i1": "80", "i2": "80", "i3": "123"})
    try:
        groups, texts, _thr, numbered = ppr.choose_labels(PTS, BG)
    finally:
        ppr.LABEL_IDS.clear()
    assert [PTS[g[0]]["row"]["id"] for g in groups] == ["i1", "i2", "i3"]   # two domains of one gene both labeled
    assert texts == ["80", "80", "123"] and all(len(g) == 1 for g in groups) and numbered is False


def test_without_label_ids_the_distance_rule_is_unchanged():
    ppr.LABEL_IDS.clear()
    groups, texts, _thr, _n = ppr.choose_labels(PTS, BG)
    assert all(PTS[g[0]]["row"]["id"] != "i1" for g in groups)   # a point inside the reference cloud is not an outlier


def test_cli_accepts_label_ids():
    import argparse, contextlib, io
    with contextlib.redirect_stdout(io.StringIO()) as out:
        try:
            ppr.main(["--help"])
        except SystemExit:
            pass
    assert "--label-ids" in out.getvalue()


def test_group_text_uses_the_listed_text_in_grid_and_page_modes():
    ppr.LABEL_IDS.clear(); ppr.LABEL_IDS.update({"i3": "123"})
    try:
        assert ppr._group_text(PTS, [3], {"SYNTHETIC_REFERENCE_010": "S010"}) == "123"
        assert ppr._group_text(PTS, [0], {"SYNTHETIC_REFERENCE_010": "S010"}) == "S010"   # unlisted point: strain rule as before
    finally:
        ppr.LABEL_IDS.clear()
