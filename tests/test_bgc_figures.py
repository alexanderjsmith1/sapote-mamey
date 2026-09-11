"""Regression tests for tools/bgc_figures.py (per-BGC figure set + data CSVs)."""
import os, csv, tempfile, importlib.util
import pytest

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("bf", os.path.join(HERE, "..", "tools", "bgc_figures.py"))
bf = importlib.util.module_from_spec(spec); spec.loader.exec_module(bf)


def test_classify_roles():
    assert bf.classify("MFS_1", "MFS transporter") == "transport"
    assert bf.classify("", "NsdA family TPR-like regulatory") == "regulatory"
    assert bf.classify("LANC_like", "lanthionine synthetase C") == "core"
    assert bf.classify("LD_lanti_pre", "FxLD family lanthipeptide") == "core"   # RiPP precursor
    assert bf.classify("Radical_SAM", "B12-binding radical SAM protein") == "core"
    assert bf.classify("2OG-FeII_Oxy_3", "2OG-Fe(II) oxygenase") == "tailoring"
    assert bf.classify("", "hypothetical protein") == "other"
    print("PASS test_classify_roles")


def test_short_label():
    assert bf.short_label("MULTISPECIES: MFS transporter [unclassified Streptomyces]", "MFS_1", "ctg1") == "MFS transporter"
    # hypothetical falls back to antismash domain, else locus tag
    assert bf.short_label("hypothetical protein [Streptomyces]", "TruD", "ctg3") == "TruD"
    assert bf.short_label("hypothetical protein", "", "ctg9") == "ctg9"
    print("PASS test_short_label")


def _tiny_gbk(path):
    open(path, "w").write("""LOCUS       NODE_1_length_3000_cov_10          3000 bp    DNA     linear   BCT 01-JAN-2026
FEATURES             Location/Qualifiers
     CDS             1..600
                     /locus_tag="ctg1_1"
                     /translation="MAAA"
     CDS             complement(700..1500)
                     /locus_tag="ctg1_2"
                     /translation="MBBB"
     CDS             1600..3000
                     /locus_tag="ctg1_3"
                     /translation="MCCC"
ORIGIN
//
""")


def test_parse_gbk_and_fig1_csv():
    pytest.importorskip("dna_features_viewer")
    pytest.importorskip("matplotlib")
    d = tempfile.mkdtemp()
    gbk = os.path.join(d, "region.gbk"); _tiny_gbk(gbk)
    genes, length = bf.parse_gbk(gbk)
    assert len(genes) == 3 and length == 3000, (len(genes), length)
    assert genes[1]["strand"] == -1
    # panel supplies function + identity
    panel = os.path.join(d, "panel.csv")
    with open(panel, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["locus_tag", "aa_length", "antismash_domains", "blastp_top_def", "pct_identity", "evalue"])
        w.writerow(["ctg1_1", "200", "LANC_like", "lanthionine synthetase C", "90.0", "0.0"])
        w.writerow(["ctg1_2", "266", "MFS_1", "MFS transporter", "60.0", "1e-90"])
        w.writerow(["ctg1_3", "466", "", "hypothetical protein", "40.0", "1e-5"])
    blastp = bf.load_blastp(panel)
    p1 = os.path.join(d, "f1.png"); c1 = os.path.join(d, "f1.csv")
    bf.fig_locus(genes, blastp, "t", p1, c1)
    assert os.path.exists(p1) and os.path.exists(c1)
    rows = list(csv.DictReader(open(c1)))
    assert rows[0]["role"] == "core" and rows[1]["role"] == "transport"
    assert "marker" not in {r["role"] for r in rows}          # the 'marker' role is gone
    # fig3
    p3 = os.path.join(d, "f3.png"); c3 = os.path.join(d, "f3.csv")
    assert bf.fig_blastp(blastp, ["ctg1_1", "ctg1_2", "ctg1_3"], "t", p3, c3)
    r3 = list(csv.DictReader(open(c3)))
    assert r3[0]["function_label"] == "lanthionine synthetase C"   # named, not g1
    print("PASS test_parse_gbk_and_fig1_csv")


if __name__ == "__main__":
    test_classify_roles()
    test_short_label()
    test_parse_gbk_and_fig1_csv()
    print("ALL PASS")
