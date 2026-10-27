"""tools/protein_pcoa_render.py --label-regions (card 455_pcoa_labels_by_region_alias): an outlier group is
labelled by its region alias (one region 'BGC013 x3', two 'BGC004, BGC013', three or more '3 loci x3'); without the
option the strain label is unchanged. Synthetic strains only."""
import contextlib
import importlib.util
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("protein_pcoa_render_ra", ROOT / "tools" / "protein_pcoa_render.py")
ppr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ppr)

S = "SYNTHETIC_REFERENCE_010"


def _pts(origins):
    return [dict(x=0.0, y=0.0, strain=S, pid=50.0, row=dict(id=f"i{k}", origin=o)) for k, o in enumerate(origins)]


def test_three_label_forms():
    ppr.REGION_LABELS.clear()
    ppr.REGION_LABELS.update({"r1.gbk": "BGC013", "r2.gbk": "BGC004", "r3.gbk": "BGC020"})
    try:
        assert ppr._group_text(_pts(["r1.gbk"] * 3), [0, 1, 2]) == "BGC013 x3"
        assert ppr._group_text(_pts(["r1.gbk", "r2.gbk"]), [0, 1]) == "BGC004, BGC013"
        assert ppr._group_text(_pts(["r1.gbk", "r2.gbk", "r3.gbk"]), [0, 1, 2]) == "3 loci x3"
    finally:
        ppr.REGION_LABELS.clear()


def test_without_the_option_labels_read_the_strain():
    ppr.REGION_LABELS.clear()
    assert ppr._group_text(_pts(["r1.gbk"] * 2), [0, 1]) == f"{S} x2"
    assert ppr._group_text(_pts(["r1.gbk"]), [0], {S: "S010"}) == "S010"


def test_cli_offers_label_regions():
    with contextlib.redirect_stdout(io.StringIO()) as out:
        try:
            ppr.main(["--help"])
        except SystemExit:
            pass
    assert "--label-regions" in out.getvalue()
