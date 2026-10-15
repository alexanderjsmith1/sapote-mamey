"""RG-GMCI reads /contig_edge from the region feature itself, not from the first feature that carries it (P300-153)."""
import zipfile

from mamey.models import BGCRecord
from mamey.rggmci import _contig_edge_bgcs


def _bgc(bid, edge, gbk):
    return BGCRecord(bgc_id=bid, contig=f"ctg{bid}", region_number=1, start=1, end=100, contig_length=100,
                     products=["NRPS"], edge_status=edge, source_gbk=gbk)


def _feature(kind, flag):
    qual = f'                     /contig_edge="{flag}"\n' if flag else ""
    return f"     {kind:<16}1..100\n{qual}                     /product=\"NRPS\"\n"


def _gbk(*features):
    return ("LOCUS       X 100 bp DNA\nFEATURES             Location/Qualifiers\n"
            + "".join(_feature(k, f) for k, f in features) + "ORIGIN\n//\n")


def _zip(tmp_path, files):
    z = tmp_path / "t.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    return z


def test_earlier_protocluster_flag_does_not_override_the_region(tmp_path):
    z = _zip(tmp_path, {
        # protocluster written first says False; the region says True -> edge region
        "a.gbk": _gbk(("protocluster", "False"), ("region", "True")),
        # cand_cluster written first says True; the region says False -> interior region
        "b.gbk": _gbk(("cand_cluster", "True"), ("region", "False")),
    })
    bgcs = [_bgc("A", "Interior", "a.gbk"), _bgc("B", "Edge", "b.gbk")]
    assert _contig_edge_bgcs(z, bgcs) == {"A"}


def test_flag_only_on_a_non_region_feature_falls_back_to_engine_status(tmp_path):
    z = _zip(tmp_path, {
        "c.gbk": _gbk(("protocluster", "True"), ("region", "")),
        "d.gbk": _gbk(("protocluster", "True"), ("region", "")),
    })
    bgcs = [_bgc("C", "Interior", "c.gbk"), _bgc("D", "Edge", "d.gbk")]
    assert _contig_edge_bgcs(z, bgcs) == {"D"}


def test_conflicting_region_features_fall_back_to_engine_status(tmp_path):
    z = _zip(tmp_path, {"e.gbk": _gbk(("region", "True"), ("region", "False"))})
    assert _contig_edge_bgcs(z, [_bgc("E", "Interior", "e.gbk")]) == set()
    assert _contig_edge_bgcs(z, [_bgc("E", "Edge", "e.gbk")]) == {"E"}


def test_region_first_layout_is_unchanged(tmp_path):
    z = _zip(tmp_path, {
        "f.gbk": _gbk(("region", "True"), ("cand_cluster", "True"), ("protocluster", "False")),
        "g.gbk": _gbk(("region", "False"), ("protocluster", "False")),
    })
    bgcs = [_bgc("F", "Interior", "f.gbk"), _bgc("G", "Edge", "g.gbk")]
    assert _contig_edge_bgcs(z, bgcs) == {"F"}
