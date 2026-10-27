"""tools/protein_pcoa_render.py --label-low-identity (card 455_pcoa_label_low_identity_ruling75, ruling 75):
only proteins below --label-below are labelled, one label per region, lowest identity first, at most --label-max per
panel, with the region's text and no count; without the option the distance rule is unchanged. Synthetic strains only.
The grid caption part of the card is not tested here: the .454 renderer has no grid mode (see REBASE_454.md)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("protein_pcoa_render_r75", ROOT / "tools" / "protein_pcoa_render.py")
ppr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ppr)

S = "SYNTHETIC_REFERENCE_010"
BG = [(i / 10, j / 10) for i in range(5) for j in range(5)]
# five low-identity regions (two proteins in r3), one region at exactly 70% and one at 99%
PTS = [dict(x=2.0 + k, y=2.0, strain=S, pid=pid, row=dict(id=f"i{k}", origin=o)) for k, (o, pid) in enumerate(
    [("r1.gbk", 60.0), ("r2.gbk", 40.0), ("r3.gbk", 55.0), ("r3.gbk", 30.0), ("r4.gbk", 65.0), ("r5.gbk", 50.0),
     ("r6.gbk", 70.0), ("r7.gbk", 99.0)])]
TEXT = {f"r{n}.gbk": f"NRPS (synthetic{n}-type)" for n in range(1, 8)}


def _set(max_labels=4):
    ppr.REGION_TEXT.clear(); ppr.REGION_TEXT.update(TEXT); ppr.LABEL_MAX[0] = max_labels


def _clear():
    ppr.REGION_TEXT.clear(); ppr.LABEL_MAX[0] = 4


def test_four_labels_lowest_identity_first_no_counts():
    _set()
    try:
        groups, texts, _thr, numbered = ppr.choose_labels(PTS, BG)
    finally:
        _clear()
    assert len(groups) == 4 and numbered is False
    assert texts == ["NRPS (synthetic3-type)", "NRPS (synthetic2-type)", "NRPS (synthetic5-type)", "NRPS (synthetic1-type)"]
    assert sorted(groups[0]) == [2, 3]                       # both r3 proteins share one label
    assert not any(" x" in t for t in texts)


def test_proteins_at_or_above_the_threshold_are_never_labelled():
    _set(max_labels=10)
    try:
        groups, texts, _thr, _n = ppr.choose_labels(PTS, BG)
    finally:
        _clear()
    labelled = {PTS[k]["row"]["origin"] for g in groups for k in g}
    assert "r6.gbk" not in labelled and "r7.gbk" not in labelled and len(groups) == 5


def test_without_the_option_the_distance_rule_is_unchanged():
    _clear()
    groups, texts, _thr, _n = ppr.choose_labels(PTS, BG)
    assert texts and all(t.startswith(S) for t in texts)     # strain labels, as before
