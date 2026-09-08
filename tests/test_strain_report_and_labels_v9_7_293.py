"""test_strain_report_and_labels_v9_7_293.py -- self-contained tests for the .293 deliverables."""
import os, tempfile, importlib.util, sys

HERE = os.path.dirname(__file__)
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, "..", "tools", name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

labels = load("bigscape_figure_labels")
report = load("strain_bigscape_report")


def test_labels_type_strain_vs_mibig_distinct():
    # a cohort type strain -> 'type strain', never bare 'reference'
    assert labels.category_of("Streptomyces venezuelae type strain") == labels.TYPE_STRAIN
    assert labels.category_of("GCA_008639165") == labels.TYPE_STRAIN
    # a MIBiG cluster -> MIBiG reference, a DIFFERENT category
    assert labels.category_of("BGC0001773.gbk") == labels.MIBIG
    assert labels.category_of("anything", is_mibig=True) == labels.MIBIG
    assert labels.TYPE_STRAIN != labels.MIBIG
    assert labels.STYLE[labels.TYPE_STRAIN]["color"] != labels.STYLE[labels.MIBIG]["color"]
    # host habitats unaffected
    assert labels.category_of("attine ant") == "attine"
    assert labels.category_of("bee host") == "bee/wasp"
    # bare 'reference' is guarded
    try:
        labels.assert_not_bare_reference("Reference")
        assert False, "should have raised"
    except ValueError:
        pass
    print("PASS test_labels_type_strain_vs_mibig_distinct")


def test_strain_report_from_tsv():
    d = tempfile.mkdtemp()
    per = os.path.join(d, "per_bgc.tsv")
    with open(per, "w") as fh:
        fh.write("strain\tlocator\tantismash_class\tfamily_status\tMIBiG_family_anchors\tnearest_MIBiG\tnearest_distance\n")
        # two known (one antifungal, on a small fragmented contig), one novel on a big contig
        fh.write("AS-X\tNODE_1_length_6000_cov_10.region001\tT1PKS\tKNOWN\tBGC1 (selvamicin)\tBGC1 (selvamicin)\t0.42\n")
        fh.write("AS-X\tNODE_2_length_40000_cov_10.region001\tNRPS\tKNOWN\tBGC2 (actinomycin)\tBGC2 (actinomycin)\t0.55\n")
        fh.write("AS-X\tNODE_3_length_50000_cov_10.region001\tT1PKS\tnovel\t\t\t1.000\n")
    nov = os.path.join(d, "novel.tsv")
    with open(nov, "w") as fh:
        fh.write("family_id\trun_id\tnormalized_cutoff\tqualified_family_id\tgcf_namespace\tclass\tn_strains\thabitats\tstrains\n")
        fh.write("fam999\t1\t0.5\tbigscape-gcf:v1/run/1/cutoff/0.5/family/fam999\trun_id=1;cutoff=0.5\tT1PKS\t4\tAttine:2\tAS-X,AS-Y,AS-Z,AS-W\n")
    shr = os.path.join(d, "sharing.tsv")
    with open(shr, "w") as fh:
        fh.write("strain_a\tstrain_b\tshared_GCF_families\tgenus_a\tgenus_b\thabitat_a\thabitat_b\n")
        fh.write("AS-X\tAS-Y\t12\tStreptomyces\tStreptomyces\tattine\tattine\n")
    uniq = os.path.join(d, "uniqueness.tsv")
    with open(uniq, "w") as fh:
        fh.write("strain\ttotal_family_BGCs\tunique_BGCs\tshared_BGCs\tstrain_exclusive_families\n")
        fh.write("AS-X\t10\t7\t3\t7\n")
    out = os.path.join(d, "AS-X_bigscape_report.md")
    argv = sys.argv[:]
    sys.argv = ["x", "--strain", "AS-X", "--per-bgc", per, "--novel", nov, "--sharing", shr,
                "--uniqueness", uniq, "--genus", "Streptomyces", "--habitat", "attine", "--out", out]
    try:
        report.main()
    finally:
        sys.argv = argv
    txt = open(out).read()
    assert "AS-X carries **3 BGC regions**" in txt
    assert "2 anchor to a characterized MIBiG cluster (KNOWN), 1 have no analog" in txt
    assert "under 15 kb" in txt and "1 of 3" in txt          # the 6 kb contig flagged
    assert "selvamicin" in txt and "antifungal" in txt        # antifungal flag applied
    assert "fam999" in txt                                     # novel family included
    assert "AS-Y: 12 shared families" in txt                  # neighbour included
    assert "7 are strain-unique" in txt and "70%" in txt      # uniqueness section
    assert "Capacity-level" in txt                            # discipline caveat present
    assert "produces" not in txt.lower()                      # no production claim
    print("PASS test_strain_report_from_tsv")


if __name__ == "__main__":
    test_labels_type_strain_vs_mibig_distinct()
    test_strain_report_from_tsv()
