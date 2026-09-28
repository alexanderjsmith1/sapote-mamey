"""RG-GMCI must be able to call a glycosylated pathway split across contigs.

The known case is a glycosylated angucycline: the core sits in one region and its deoxy-aminosugar cassette,
labelled only "saccharide" by antiSMASH, in another. Two rules blocked it:
  - one shared reference gene (a sugar gene family present twice in the reference cluster) made every shared
    reference read as paralogy;
  - the product-class gate sets "saccharide" aside, so a sugar-only fragment could not hold HIGH.
These tests use synthetic inputs of the same shape as that case.
"""
import zipfile

from mamey import rggmci as R
from mamey.models import BGCRecord


def tiling(n_a_only, n_b_only, n_shared):
    shared = [f"S{i}" for i in range(n_shared)]
    a = [f"A{i}" for i in range(n_a_only)] + shared
    b = [f"B{i}" for i in range(n_b_only)] + shared
    return R._subject_tiling(a, b)["subject_tiling_class"]


def test_a_few_shared_genes_do_not_veto_a_complementary_split():
    assert tiling(11, 8, 2) == "COMPLEMENTARY_DISJOINT"     # mayamycin-shaped: 2 of 21 genes shared
    assert tiling(4, 8, 0) == "COMPLEMENTARY_DISJOINT"      # indolocarbazole-shaped: none shared


def test_two_copies_of_one_core_stay_paralogy():
    assert tiling(4, 2, 4) == "OVERLAPPING_SUBJECTS"        # desferrioxamine-shaped: 4 of 10 shared
    assert tiling(20, 20, 3) == "OVERLAPPING_SUBJECTS"      # more than two shared genes
    assert tiling(1, 20, 1) == "OVERLAPPING_SUBJECTS"       # each side needs two genes of its own


def bgc(bid, products, gbk=""):
    return BGCRecord(bid, f"ctg_{bid}", 1, 1, 10000, 12000, products=products, source_gbk=gbk)


def test_sugar_arm_needs_a_glycosyltransferase_on_the_backbone_side():
    arm, core = bgc("BGC014", ["saccharide"]), bgc("BGC004", ["T2PKS", "phenazine"])
    assert R._sugar_arm_pair(arm, core, {"BGC004"})
    assert not R._sugar_arm_pair(arm, core, set())                       # no glycosyltransferase: no restore
    assert not R._sugar_arm_pair(arm, bgc("BGC009", ["fatty_acid"]), {"BGC009"})   # not a backbone class
    assert not R._sugar_arm_pair(bgc("BGC015", ["saccharide", "T1PKS"]), core, {"BGC004"})   # not sugar-only


def test_glycosyltransferase_scan_reads_each_region_file(tmp_path):
    z = tmp_path / "g.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("c1.region001.gbk", '     CDS  1..9\n                     /gene_functions="biosynthetic-additional '
                                        '(smcogs) SMCOG1062: glycosyltransferase"\n')
        zf.writestr("c2.region001.gbk", '     CDS  1..9\n                     /product="NRPS"\n')
    bgcs = [bgc("BGC001", ["T2PKS"], "c1.region001.gbk"), bgc("BGC002", ["NRPS"], "c2.region001.gbk")]
    assert R._glycosyltransferase_bgcs(z, bgcs) == {"BGC001"}
