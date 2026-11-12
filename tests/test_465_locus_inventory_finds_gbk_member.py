"""9.7.465: build_modeb_locus_inventory.py finds the whole-assembly GenBank member of a ZIP itself.

Fail-before on sealed 9.7.464: without --gbk-member the tool raised "ZIP requires an explicit whole-assembly member",
so a caller had to guess the member's name, and a guess of <strain>.gbk fails for members named <strain>_first.gbk or
<folder>/<strain>_new.gbk. Pass-after: it takes the one GenBank member that is not a region file, not antiSMASH's
input/ copy and not a macOS resource fork, records how it chose it, and refuses (naming the candidates, writing
nothing) when there is none or more than one. A given --gbk-member is used as given.
"""
import csv
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
if "mamey" not in sys.modules:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_modeb_locus_inventory as T   # noqa: E402

STRAIN, CONTIG = "SYNTHETIC_REFERENCE", "NODE_1_length_900_cov_10.0"


def _gbk_text():
    pytest.importorskip("Bio.SeqIO")
    import io
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqFeature import FeatureLocation, SeqFeature
    from Bio.SeqRecord import SeqRecord
    rec = SeqRecord(Seq("ATG" + "GCT" * 98 + "TAA"), id=CONTIG, name=CONTIG, annotations={"molecule_type": "DNA"})
    rec.features.append(SeqFeature(FeatureLocation(0, 300, strand=1), type="CDS",
                                   qualifiers={"locus_tag": ["ctg1_1"], "translation": ["M" + "A" * 98]}))
    buf = io.StringIO()
    SeqIO.write(rec, buf, "genbank")
    return buf.getvalue()


def _zip(path, members):
    with zipfile.ZipFile(path, "w") as z:
        for name, text in members.items():
            z.writestr(name, text)
    return path


def _package(tmp):
    pkg = tmp / "package"
    pkg.mkdir()
    with open(pkg / f"{STRAIN}_cds_table.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["strain", "contig", "locus_tag", "start", "end", "strand", "length_aa", "region", "bgc_id"])
        w.writerow([STRAIN, CONTIG, "ctg1_1", 1, 300, 1, 99, "region001", "BGC001"])
    return pkg


def test_the_filter_keeps_only_the_whole_assembly_member(tmp_path):
    z = _zip(tmp_path / "a.zip", {f"{STRAIN}_first.gbk": "x", f"{CONTIG}.region001.gbk": "x",
                                  f"input/{STRAIN}.gbk": "x", "__MACOSX/folder/._x.gbk": "x",
                                  f"folder/._{STRAIN}.gbk": "x", "notes.txt": "x"})
    assert T.whole_assembly_members(z) == [f"{STRAIN}_first.gbk"]
    assert T.choose_member(z, None) == (f"{STRAIN}_first.gbk", "the only whole-assembly GenBank member")
    assert T.choose_member(z, "given.gbk") == ("given.gbk", "given")


@pytest.mark.parametrize("members,code", [
    ({"a.gbk": "x", "b/b.gbk": "x"}, "GBK_MEMBER_AMBIGUOUS"),
    ({f"{CONTIG}.region001.gbk": "x"}, "GBK_MEMBER_NOT_FOUND"),
])
def test_none_or_several_members_is_refused_before_any_write(tmp_path, members, code):
    z = _zip(tmp_path / "a.zip", members)
    out = tmp_path / "inv.json"
    with pytest.raises(ValueError, match=code):
        T.export(z, None, _package(tmp_path), STRAIN, out)
    assert not out.exists()


def test_export_finds_a_member_with_another_name_and_records_how(tmp_path):
    z = _zip(tmp_path / "a.zip", {f"{STRAIN}_new (Loose)/{STRAIN}_new.gbk": _gbk_text(),
                                  f"input/{STRAIN}.gbk": _gbk_text()})
    out = tmp_path / "inv.json"
    T.export(z, None, _package(tmp_path), STRAIN, out)
    src = json.loads(out.read_text())["assembly_source"]
    assert src["gbk_member"] == f"{STRAIN}_new (Loose)/{STRAIN}_new.gbk"
    assert src["gbk_member_selection"] == "the only whole-assembly GenBank member"
