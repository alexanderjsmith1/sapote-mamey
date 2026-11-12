"""tools/enzyme_family_context.py: reaction text and its source, region classes, best MIBiG hit, MIBiG organism,
refusals. Needs tools/cohort_enzyme_catalog.py output. Synthetic packages only."""
import csv
import json

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import cohort_enzyme_catalog as cec  # noqa: E402
import enzyme_family_context as efc  # noqa: E402

KS = "biosynthetic-additional (smcogs) SMCOG1022: Beta-ketoacyl synthase mod_KS (E-value: 1e-50, bitscore: 160, seeds: 1)"
KS2 = "biosynthetic-additional (smcogs) SMCOG1022: Beta-ketoacyl synthase hyb_KS (E-value: 1e-40, bitscore: 120, seeds: 1)"
PUL = "other (smcogs) SMCOG1297: Pullulanase, type I (E-value: 1e-80, bitscore: 260, seeds: 1)"


def cds(tag, gf="", doms=()):
    return dict(locus_tag=tag, aa_length=300, sec_met_domains=list(doms), gene_functions=gf, gene_kind="")


def make(root, strain, recs, products, mibig_rows=(), hmm_rows=()):
    pkg = root / strain / "package"
    pkg.mkdir(parents=True)
    lines = [json.dumps({"schema_version": "gene_context/1.0"})] + [json.dumps({"bgc_id": b, "cds": c}) for b, c in recs.items()]
    (pkg / f"{strain}_gene_context.jsonl").write_text("\n".join(lines) + "\n")
    with open(pkg / f"{strain}_2_inventory.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Contig", "antiSMASH_Region", "Products"])
        for i, b in enumerate(recs, 1):
            w.writerow([b, f"NODE_{i}", "region001", products[b]])
    with open(pkg / f"{strain}_3_mibig_per_gene.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["strain", "bgc_id", "query_gene", "mibig_accession", "mibig_compound", "pct_identity", "pct_coverage",
                    "blast_score"])
        w.writerows(r if len(r) == 8 else [r[0], "BGC001"] + list(r[1:]) for r in mibig_rows)
    with open(pkg / f"{strain}_3_antismash_hmm.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["domain_name", "description"])
        w.writerows(hmm_rows)
    return f"{strain}/package/{strain}_gene_context.jsonl"


@pytest.fixture
def run(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    g1 = make(root, "Z-1", {"BGC001": [cds("k1", KS, ["PKS_KS"]), cds("p1", PUL, ["Alpha-amylase", "CBM_48"]),
                                       cds("d1", "", ["MysteryDom"]), cds("n1")]},
              {"BGC001": "T1PKS; saccharide"},
              mibig_rows=[["Z-1", "k1", "BGC0000001", "compound one", "70", "95", "300"],
                          ["Z-1", "k1", "BGC0000002", "compound two", "80", "40", "120"],
                          ["Z-1", "p1", "BGC0000804", "acarviostatin", "65", "90", "500"]],
              hmm_rows=[["MysteryDom", "A domain described only by antiSMASH"]])
    g2 = make(root, "Z-2", {"BGC001": [cds("k2", KS2, ["PKS_KS"])]}, {"BGC001": "T1PKS"},
              mibig_rows=[["Z-2", "k2", "BGC0000001", "compound one", "60", "90", "250"]])
    gt = root / "genomes.tsv"
    gt.write_text(f"strain\tgene_context\nZ-1\t{g1}\nZ-2\t{g2}\n")
    hmm = root / "Pfam-A.hmm"
    hmm.write_text("HMMER3/f\nNAME  Alpha-amylase\nACC   PF00128.1\nDESC  Alpha amylase, catalytic domain\n//\n"
                   "NAME  CBM_48\nACC   PF02922.1\nDESC  Carbohydrate-binding module 48\n//\n")
    cec.build(gt, root, root / "cat")
    return root, gt, hmm


def ctx(root):
    return {r["family"]: r for r in csv.DictReader(open(root / "cat" / "FAMILY_CONTEXT.tsv"), delimiter="\t")}


def test_shipped_reference_covers_its_rows_and_is_marked_citation_needed():
    ref = efc.load_smcog_reference()
    assert len(ref) == 272 and all(r["citation_status"] == "citation_needed" for r in ref.values())
    assert ref["SMCOG1297"]["ec_class"] == "EC 3.2.1.41" and "α-1,6" in ref["SMCOG1297"]["reaction_or_function"]
    assert all(r["reaction_or_function"] and r["usual_role"] for r in ref.values())


def test_reaction_text_and_its_source(run):
    root, gt, hmm = run
    info = efc.build(root / "cat", gt, root, pfam_hmm=hmm)
    c = ctx(root)
    pul = c["SMCOG1297: Pullulanase, type I"]
    assert pul["ec_class"] == "EC 3.2.1.41" and pul["reaction_source"] == "smCOG reference (citation_needed)"
    assert pul["genes_by_category"] == f"{pul['category']} 1"
    assert "Alpha-amylase (1): Alpha amylase, catalytic domain" in pul["main_domains"]
    assert c["MysteryDom"]["reaction_or_function"] == "A domain described only by antiSMASH"
    assert c["MysteryDom"]["reaction_source"] == "antiSMASH description"
    assert c[cec.NO_CALL_FAMILY]["reaction_or_function"] == ""
    assert info["smcog_ids_without_reference"] == []


def test_products_from_region_classes_and_best_mibig_hit(run):
    root, gt, hmm = run
    efc.build(root / "cat", gt, root, pfam_hmm=hmm)
    ks = ctx(root)["SMCOG1022: Beta-ketoacyl synthase"]
    assert ks["region_product_classes"].startswith("T1PKS 2")
    # best per gene is by blast_score: k1's best is compound one (300) not compound two (120)
    assert ks["mibig_compounds"] == "compound one [BGC0000001] 2 genes, median 65%" and ks["genes_with_mibig_hit"] == "2"
    g = list(csv.DictReader(open(root / "cat" / "GENE_MIBIG_BEST.tsv"), delimiter="\t"))
    assert len(g) == 3 and {r["mibig_accession"] for r in g} == {"BGC0000001", "BGC0000804"}


def test_mibig_organism_is_shown_when_an_index_is_given(run):
    root, gt, hmm = run
    idx = root / "mibig_index.json"
    idx.write_text(json.dumps({"entries": [{"accession": "BGC0000001", "taxonomy": {"name": "Nocardia example"}}]}))
    info = efc.build(root / "cat", gt, root, mibig_index=idx)
    ks = ctx(root)["SMCOG1022: Beta-ketoacyl synthase"]
    assert ks["mibig_compounds"] == "compound one [BGC0000001, Nocardia example] 2 genes, median 65%"
    g = {r["mibig_accession"]: r for r in csv.DictReader(open(root / "cat" / "GENE_MIBIG_BEST.tsv"), delimiter="\t")}
    assert g["BGC0000001"]["mibig_organism"] == "Nocardia example" and g["BGC0000804"]["mibig_organism"] == ""
    assert info["mibig_organisms_loaded"] == 1
    with pytest.raises(cec.CatalogError, match="--mibig-index not found"):
        efc.build(root / "cat", gt, root, out=root / "o4", mibig_index=root / "none.json")


def test_without_pfam_file_domain_families_fall_back(run):
    root, gt, hmm = run
    info = efc.build(root / "cat", gt, root)
    assert info["pfam_names_loaded"] == 0
    assert ctx(root)["SMCOG1297: Pullulanase, type I"]["main_domains"].startswith("Alpha-amylase (1)")


def test_mibig_hit_is_bound_to_its_own_bgc(tmp_path):
    # the same locus tag in two BGCs: the BGC002 hit must not be lent to the BGC001 gene; a row with no bgc_id is unused
    root = tmp_path / "ws"
    root.mkdir()
    g = make(root, "Y-1", {"BGC001": [cds("t1", KS, ["PKS_KS"])], "BGC002": [cds("t1", KS, ["PKS_KS"])]},
             {"BGC001": "T1PKS", "BGC002": "T1PKS"},
             mibig_rows=[["Y-1", "BGC002", "t1", "BGC0000009", "other region", "90", "90", "900"],
                         ["Y-1", "", "t1", "BGC0000008", "no region", "99", "99", "999"]])
    gt = root / "genomes.tsv"
    gt.write_text(f"strain\tgene_context\nY-1\t{g}\n")
    cat = root / "cat"
    cec.build(gt, root, cat)
    info = efc.build(cat, gt, root)
    hits = list(csv.DictReader(open(cat / "GENE_MIBIG_BEST.tsv"), delimiter="\t"))
    assert [(h["gene_identity"].split(" / ")[3], h["mibig_accession"]) for h in hits] == [("BGC002", "BGC0000009")]
    assert info["mibig_input_gaps"] == {"Y-1": {"rows_without_bgc_id": 1}}


def test_refusals(run, tmp_path):
    root, gt, hmm = run
    with pytest.raises(cec.CatalogError, match="run tools/cohort_enzyme_catalog.py first"):
        efc.build(tmp_path / "nowhere", gt, root)
    efc.build(root / "cat", gt, root)
    with pytest.raises(cec.CatalogError, match="already exists"):
        efc.build(root / "cat", gt, root)
    with pytest.raises(cec.CatalogError, match="--pfam-hmm not found"):
        efc.build(root / "cat", gt, root, out=root / "o2", pfam_hmm=root / "missing.hmm")
    one = root / "one.tsv"
    one.write_text(gt.read_text().splitlines()[0] + "\n" + gt.read_text().splitlines()[1] + "\n")
    with pytest.raises(cec.CatalogError, match="strains not in"):
        efc.build(root / "cat", one, root, out=root / "o3")
    with pytest.raises(SystemExit) as e:
        efc.main(["--catalog", str(tmp_path / "nowhere"), "--genomes", str(gt), "--root", str(root)])
    assert e.value.code == 2
