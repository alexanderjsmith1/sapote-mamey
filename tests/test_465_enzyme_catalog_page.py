"""tools/cohort_enzyme_catalog_page.py: embedded group and family data, escaping, options, refusals. Needs
tools/cohort_enzyme_catalog.py and tools/enzyme_family_context.py output. Synthetic packages only."""
import json
import re

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import cohort_enzyme_catalog as cec  # noqa: E402
import cohort_enzyme_catalog_page as ecp  # noqa: E402
import enzyme_family_context as efc  # noqa: E402

KS1 = "x (smcogs) SMCOG1022: Beta-ketoacyl synthase mod_KS (E-value: 1)"
KS2 = "x (smcogs) SMCOG1022: Beta-ketoacyl synthase hyb_KS (E-value: 1)"


def pkg(root, strain, cds_list):
    d = root / strain / "package"
    d.mkdir(parents=True)
    (d / f"{strain}_gene_context.jsonl").write_text(json.dumps({"schema_version": "x"}) + "\n" + json.dumps({"bgc_id": "BGC001", "cds": cds_list}) + "\n")
    (d / f"{strain}_2_inventory.csv").write_text("BGC_ID,Contig,antiSMASH_Region,Products\nBGC001,NODE_1,region001,T1PKS\n")
    (d / f"{strain}_proteins.faa").write_text("".join(f">{c['locus_tag']} bgc=BGC001\nM{c['locus_tag'].upper()}KLV\n" for c in cds_list))
    (d / f"{strain}_3_mibig_per_gene.csv").write_text("bgc_id,query_gene,mibig_accession,mibig_compound,pct_identity,pct_coverage,blast_score\n"
                                                     f"BGC001,{cds_list[0]['locus_tag']},BGC0000001,compound one,70,90,300\n")
    return f"{strain}/package/{strain}_gene_context.jsonl"


@pytest.fixture
def built(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    c = lambda t, gf, d: dict(locus_tag=t, aa_length=300, sec_met_domains=d, gene_functions=gf, gene_kind="")
    g1 = pkg(root, "W-1", [c("k1", KS1, ["PKS_KS"]), c("t1", "", ["ABC_tran"])])
    g2 = pkg(root, "W-2", [c("k2", KS2, ["PKS_KS"])])
    gt = root / "g.tsv"
    gt.write_text(f"strain\tgene_context\nW-1\t{g1}\nW-2\t{g2}\n")
    (root / "cl.tsv").write_text("centroid\tmember\nW-1|k1\tW-1|k1\nW-1|k1\tW-2|k2\nW-1|t1\tW-1|t1\n")
    cec.build(gt, root, root / "cat", clusters=root / "cl.tsv", cluster_settings="diamond cluster --approx-id 50")
    efc.build(root / "cat", gt, root)
    return root


def page_data(text, name):
    m = re.search(rf"const {name} = (.*?);\n", text)
    return json.loads(m.group(1).replace("<\\/", "</"))


def test_page_holds_multi_strain_biosynthetic_groups_and_all_families(built):
    root = built
    info = ecp.build(root / "cat", root / "p.html", title="Test <cohort>")
    t = (root / "p.html").read_text()
    assert "<title>Test &lt;cohort&gt;</title>" in t and "fonts.googleapis" not in t and "__" not in t.split("<script>")[0]
    groups, fams = page_data(t, "D"), page_data(t, "F")
    assert info["groups"] == 1 and len(groups) == 1 and groups[0][1] == "SMCOG1022: Beta-ketoacyl synthase" and groups[0][3] == 2
    member = groups[0][6][0]
    assert member[:5] == ["W-1", "NODE_1", "region001", "BGC001", "k1"] and member[13] == "compound one"
    assert groups[0][7] == "compound one [BGC0000001] 2 genes, median 70%"
    assert set(fams) == {"SMCOG1022: Beta-ketoacyl synthase", "ABC_tran"} and "diamond cluster --approx-id 50" in t


def test_options_and_refusals(built):
    root = built
    info = ecp.build(root / "cat", root / "all.html", min_strains=1, all_categories=True)
    assert info["groups"] == 2
    with pytest.raises(cec.CatalogError, match="already exists"):
        ecp.build(root / "cat", root / "all.html")
    (root / "cat" / "SPECIFIC_GROUPS.tsv").rename(root / "cat" / "moved.tsv")
    with pytest.raises(cec.CatalogError, match="SPECIFIC_GROUPS.tsv not found"):
        ecp.build(root / "cat", root / "x.html")
    with pytest.raises(SystemExit) as e:
        ecp.main(["--catalog", str(root / "cat"), "--out", str(root / "y.html"), "--min-strains", "0"])
    assert e.value.code == 2


def test_slot_names_inside_data_do_not_break_the_page():
    tpl = "<title>__TITLE__</title><p>__FOOTER__</p><script>const D = __DATA__;\nconst F = __FAMS__;</script>"
    out = ecp.fill_template(tpl, dict(TITLE="t __DATA__", FOOTER="f", DATA='["__FAMS__","__TITLE__"]', FAMS='["x"]'))
    assert out == ('<title>t __DATA__</title><p>f</p><script>const D = ["__FAMS__","__TITLE__"];\n'
                   'const F = ["x"];</script>')
    with pytest.raises(cec.CatalogError, match="template slots"):
        ecp.fill_template(tpl + "__DATA__", dict(TITLE="", FOOTER="", DATA="", FAMS=""))
