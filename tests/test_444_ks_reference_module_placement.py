"""KS placement on a reference cluster's module order (mamey.ks_phylogeny, tools/ks_module_placement.py).

Shared-reference homology cannot separate the pieces of a giant modular PKS broken over many contigs; KS phylogeny with
the reference's own module KS can. In public genome SID8382 (WGS WWFZ01), KS domains on ten contigs sat one-to-one
beside neomediomycin B module KS. Alex, 2026-09-27: build it into this cut as an additive evidence layer.
"""
import csv
import importlib.util
from pathlib import Path

import pytest

from mamey import ks_phylogeny as kp

ROOT = Path(__file__).resolve().parents[1]


def _gbk(n_ks, seq="MKTAYIAKQRQISFVKSHFSRQ"):
    lines = ["LOCUS       REF1                   900 bp    DNA     linear   UNK 01-JAN-1980",
             "FEATURES             Location/Qualifiers"]
    for i in range(n_ks):
        lines += [f"     aSDomain        {i * 100 + 1}..{i * 100 + 90}", '                     /aSDomain="PKS_KS"',
                  f'                     /domain_id="ks{i}"', f'                     /translation="{seq}{"A" * i}"']
        lines += [f"     aSDomain        {i * 100 + 91}..{i * 100 + 99}", '                     /aSDomain="PKS_AT"',
                  f'                     /translation="{seq}"']
    return "\n".join(lines + ["ORIGIN", "//"]) + "\n"


def test_reference_ks_are_numbered_along_the_record(tmp_path):
    g = tmp_path / "BGC0000001.gbk"
    g.write_text(_gbk(3))
    tips = kp.reference_module_ks(g)
    assert [t["tip"] for t in tips] == ["MIBiG__BGC0000001_KS01", "MIBiG__BGC0000001_KS02", "MIBiG__BGC0000001_KS03"]
    assert [t["module"] for t in tips] == [1, 2, 3]
    assert tips[2]["translation"].endswith("AA")


# q1 beside module 1 (placed); q2+q3 share module 2 (placed, a duplicate); q4-q6 share module 3 (family);
# q7 sits with modules 4 and 5 (ambiguous); q8 only under a weak split (unplaced)
TREE = ("((q1:0.1,MIBiG__R_KS01:0.1)100:0.2,((q2:0.1,q3:0.1)60:0.1,MIBiG__R_KS02:0.1)97:0.2,"
        "((q4:0.1,q5:0.1,q6:0.1)50:0.1,MIBiG__R_KS03:0.1)99:0.2,(q7:0.1,(MIBiG__R_KS04:0.1,MIBiG__R_KS05:0.1)40:0.1)90:0.2,"
        "(q8:0.1,MIBiG__S_KS01:0.1)30:0.3);")


def _by_query(tree):
    return {r["query"]: r for r in kp.place_on_reference_modules(tree)}


def test_placement_verdicts():
    r = _by_query(TREE)
    assert (r["q1"]["verdict"], r["q1"]["reference"], r["q1"]["module"]) == (kp.PLACED, "R", 1)
    assert (r["q2"]["verdict"], r["q2"]["module"], r["q2"]["query_tips_in_split"]) == (kp.PLACED, 2, 2)
    assert r["q4"]["verdict"] == kp.FAMILY and r["q4"]["module"] == 3
    assert r["q7"]["verdict"] == kp.AMBIGUOUS
    assert r["q7"]["reference_tips_in_split"] == "MIBiG__R_KS04; MIBiG__R_KS05"
    assert r["q8"]["verdict"] in (kp.UNPLACED, kp.AMBIGUOUS)   # only weak splits around it
    assert r["q8"]["module"] == ""


def test_placement_does_not_depend_on_where_the_tree_is_rooted():
    rerooted = ("(q1:0.1,MIBiG__R_KS01:0.1,(((q2:0.1,q3:0.1)60:0.1,MIBiG__R_KS02:0.1)97:0.2,"
                "((q4:0.1,q5:0.1,q6:0.1)50:0.1,MIBiG__R_KS03:0.1)99:0.2,"
                "(q7:0.1,(MIBiG__R_KS04:0.1,MIBiG__R_KS05:0.1)40:0.1)90:0.2,(q8:0.1,MIBiG__S_KS01:0.1)30:0.3)100:0.2);")
    a, b = _by_query(TREE), _by_query(rerooted)
    for q in ("q1", "q2", "q3", "q4", "q7"):
        assert (a[q]["verdict"], a[q]["module"]) == (b[q]["verdict"], b[q]["module"]), q


def test_iqtree_labels_and_quoted_names_are_read():
    tree = "(('iso__NODE_1__region001__t1__ks1':0.1,MIBiG__R_KS07:0.1)95.3/100:0.2,x:0.1,y:0.2);"
    r = _by_query(tree)
    assert r["iso__NODE_1__region001__t1__ks1"]["module"] == 7


def test_the_tool_writes_inputs_and_places(tmp_path):
    spec = importlib.util.spec_from_file_location("ks_module_placement", ROOT / "tools/ks_module_placement.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    gbks = tmp_path / "gbks"
    gbks.mkdir()
    (gbks / "TST-1_NODE_5_region001.gbk").write_text(_gbk(2, seq="MSEQVENCEQUERYKS"))
    ref = tmp_path / "BGC0000009.gbk"
    ref.write_text(_gbk(3))
    assert tool.main(["inputs", "--gbk-dir", str(gbks), "--reference", str(ref), "--out", str(tmp_path / "o")]) == 0
    faa = (tmp_path / "o" / "ks_with_references.faa").read_text()
    assert faa.count(">TST-1__NODE_5__region001") == 2 and faa.count(">MIBiG__BGC0000009_KS") == 3
    assert "iqtree3" in (tmp_path / "o" / "COMMANDS.txt").read_text()
    (tmp_path / "t.treefile").write_text(TREE)
    assert tool.main(["place", "--tree", str(tmp_path / "t.treefile"), "--out", str(tmp_path / "p.tsv")]) == 0
    rows = list(csv.DictReader(open(tmp_path / "p.tsv"), delimiter="\t"))
    assert {r["query"] for r in rows} == {f"q{i}" for i in range(1, 9)}


def test_mixed_isolates_are_still_refused(tmp_path):
    gbks = tmp_path / "gbks"
    gbks.mkdir()
    (gbks / "TST-1_NODE_5_region001.gbk").write_text(_gbk(1))
    (gbks / "TST-2_NODE_5_region001.gbk").write_text(_gbk(1))
    with pytest.raises(ValueError, match="STRAIN-INTERNAL"):
        kp.extract_module_core_domains(gbks, classes=("PKS_KS",))
