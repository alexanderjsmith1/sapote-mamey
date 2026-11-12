"""tools/cohort_enzyme_catalog.py: family rule, smCOG naming, BLASTp values and top hits, four-part identity,
sequence groups from cluster output, refusals. Synthetic packages only."""
import csv
import hashlib
import json
from pathlib import Path

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import cohort_enzyme_catalog as cec  # noqa: E402

KS1 = "biosynthetic (rule-based-clusters) T1PKS: PKS_KS biosynthetic-additional (smcogs) SMCOG1022: Beta-ketoacyl synthase mod_KS (E-value: 1e-50, bitscore: 160, seeds: 1, tool: rule-based-clusters)"
KS2 = "biosynthetic-additional (smcogs) SMCOG1022: Beta-ketoacyl synthase hyb_KS (E-value: 1e-40, bitscore: 120, seeds: 1)"
P450 = "biosynthetic-additional (smcogs) SMCOG1007: cytochrome P450 p450 (E-value: 1e-30, bitscore: 90, seeds: 1)"


def cds(tag, gf="", doms=(), aa=300):
    return dict(locus_tag=tag, contig="c", start=1, end=aa * 3, strand=1, aa_length=aa, product="",
                sec_met_domains=list(doms), gene_functions=gf, gene_kind="", tta_codons=0, has_translation=True)


def package(root: Path, strain: str, bgcs: dict, inventory: bool = True):
    pkg = root / strain / "package"
    pkg.mkdir(parents=True)
    lines = [json.dumps({"schema_version": "gene_context/1.0"})]
    lines += [json.dumps({"bgc_id": b, "cds": c}) for b, c in bgcs.items()]
    (pkg / f"{strain}_gene_context.jsonl").write_text("\n".join(lines) + "\n")
    if inventory:
        rows = ["BGC_ID,Contig,antiSMASH_Region,Products"]
        rows += [f"{b},NODE_{i}_length_5000_cov_10,region001,T1PKS" for i, b in enumerate(bgcs, 1)]
        (pkg / f"{strain}_2_inventory.csv").write_text("\n".join(rows) + "\n")
    with open(pkg / f"{strain}_proteins.faa", "w") as fh:
        for b, cs in bgcs.items():
            for c in cs:
                fh.write(f">{c['locus_tag']} bgc={b}\nMSTNPKLLV\n")
    return f"{strain}/package/{strain}_gene_context.jsonl"


@pytest.fixture
def cohort(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    g1 = package(root, "X-1", {"BGC001": [cds("a1", KS1, ["PKS_KS", "PKS_AT"]), cds("a2", P450, ["p450"]),
                                          cds("a3", "", ["Condensation", "AMP-binding"]), cds("a4")]})
    g2 = package(root, "X-2", {"BGC001": [cds("b1", KS2, ["PKS_KS"]), cds("b2", "", ["Abhydrolase_1"])]})
    gt = root / "genomes.tsv"
    gt.write_text(f"strain\tgenus\tblock\tgene_context\nX-1\tGenusA\tB1\t{g1}\nX-2\tGenusB\tB2\t{g2}\n")
    res = root / "res"
    res.mkdir()
    (res / "a1.csv").write_text("strain,gene,hit_rank,subject_acc,subject_organism,subject_def,pct_identity\n"
                                "X-1,a1,1,WP_1,Streptomyces sp. Q,polyketide synthase [Streptomyces sp. Q],61.0\n"
                                "X-1,a1,2,WP_2,Other sp.,x,60.0\n")
    gv = root / "GENE_VALUES.tsv"
    gv.write_text("strain\tgene\tchannel\ttop1_identity\ttop10_mean_identity\thits_used\tranks_from_disk\tsource_file\n"
                  "X-1\ta1\tncbi_clustered_nr\t61\t55.5\t10\t\tres/a1.csv\n"
                  "X-1\ta1\tncbi_nr\t62\t58.25\t10\t\tres/a1.csv\n"
                  "X-2\tb1\tncbi_clustered_nr\t90\t88.0\t10\t\t\n")
    return root, gt, gv


def read(p):
    return list(csv.DictReader(open(p), delimiter="\t"))


def test_family_rule_smcog_name_subtype_and_category(cohort):
    root, gt, gv = cohort
    info = cec.build(gt, root, root / "out", gv)
    g = {r["locus_tag"]: r for r in read(root / "out" / "ENZYME_GENES.tsv")}
    # the subtype token after the shared smCOG name is split off, so both KS genes share one family
    assert g["a1"]["family"] == g["b1"]["family"] == "SMCOG1022: Beta-ketoacyl synthase"
    assert (g["a1"]["smcog_subtype_token"], g["b1"]["smcog_subtype_token"]) == ("mod_KS", "hyb_KS")
    assert g["a1"]["category"] == "PKS-core"
    # no smCOG: first domain with a named category
    assert g["a3"]["family"] == "Condensation" and g["a3"]["category"] == "NRPS-core"
    assert g["a4"]["family"] == cec.NO_CALL_FAMILY and g["a4"]["category"] == "no call"
    assert info["genes"] == 6 and info["no_call_genes"] == 1 and info["identity_holds"] == 0


def test_smcog_name_drops_a_trailing_domain_token_shared_by_every_occurrence():
    gf = "transport (smcogs) SMCOG1146: sugar transferase Bac_transf (E-value: 1e-40, bitscore: 120, seeds: 1)"
    names = cec.smcog_names([(gf, ["Bac_transf"]), (gf, ["Bac_transf", "CoA_binding_3"])])
    assert names == {"SMCOG1146": "sugar transferase"}
    fam, cat, sub = cec.classify(dict(gene_functions=gf, sec_met_domains=["Bac_transf"]), names)
    assert (fam, sub) == ("SMCOG1146: sugar transferase", "Bac_transf")
    # a domain word is kept when cutting it would leave the name ending in a comma
    terd = "other (smcogs) SMCOG1296: tellurium resistance protein, TerD (E-value: 1)"
    assert cec.smcog_names([(terd, ["TerD"])]) == {"SMCOG1296": "tellurium resistance protein, TerD"}
    # a name word that is not a domain on these genes is kept
    assert cec.smcog_names([("x (smcogs) SMCOG1297: Pullulanase, type I (E-value: 1)", ["Alpha-amylase"])]) == {"SMCOG1297": "Pullulanase, type I"}


def test_blastp_takes_highest_database_value_and_reads_rank1_hit(cohort):
    root, gt, gv = cohort
    cec.build(gt, root, root / "out", gv)
    g = {r["locus_tag"]: r for r in read(root / "out" / "ENZYME_GENES.tsv")}
    assert g["a1"]["blastp_top10_mean"] == "58.25"
    assert (g["a1"]["top_hit_acc"], g["a1"]["top_hit_organism"], g["a1"]["top_hit_pct"]) == ("WP_1", "Streptomyces sp. Q", "61.0")
    assert g["b1"]["blastp_top10_mean"] == "88.0" and g["b1"]["top_hit_acc"] == ""  # no source file: blank, not invented
    assert g["a2"]["blastp_top10_mean"] == ""  # no value: blank


def test_top_hit_falls_back_to_another_source_and_alias(cohort):
    root, gt, gv = cohort
    # b1 gets two rows with the same value: the first names a missing file under a label root, the second a real file
    (root / "repo").mkdir()
    (root / "repo" / "b1.csv").write_text("strain,gene,hit_rank,subject_acc,subject_organism,subject_def,pct_identity\n"
                                          "X-2,b1,1,WP_9,Streptomyces sp. Z,ThiF [Streptomyces sp. Z],88.0\n")
    gv2 = root / "gv2.tsv"
    gv2.write_text(gv.read_text().replace("X-2\tb1\tncbi_clustered_nr\t90\t88.0\t10\t\t\n",
                   "X-2\tb1\tncbi_clustered_nr\t90\t88.0\t10\t\tLABEL ROOT/b1.csv\n"))
    cec.build(gt, root, root / "o1", gv2)
    g = {r["locus_tag"]: r for r in read(root / "o1" / "ENZYME_GENES.tsv")}
    assert g["b1"]["top_hit_acc"] == ""  # only a missing file: blank, not invented
    info = cec.build(gt, root, root / "o2", gv2, source_aliases=[("LABEL ROOT", "repo")])
    g = {r["locus_tag"]: r for r in read(root / "o2" / "ENZYME_GENES.tsv")}
    assert g["b1"]["top_hit_acc"] == "WP_9" and info["genes_with_blastp_but_no_top_hit"] == 0
    with open(gv2, "a") as fh:  # a second, readable source for a1 under a missing first one is also used
        fh.write("X-1\ta1\tncbi_clustered_nr\t61\t58.25\t10\t\tMISSING/a1.csv\n")
    info = cec.build(gt, root, root / "o3", gv2)
    g = {r["locus_tag"]: r for r in read(root / "o3" / "ENZYME_GENES.tsv")}
    assert g["a1"]["top_hit_acc"] == "WP_1"


def test_a_file_holding_another_genes_query_gives_no_hit_and_no_value(cohort):
    root, gt, gv = cohort
    res = root / "res"
    (res / "other.csv").write_text("strain,gene,hit_rank,subject_acc,subject_organism,subject_def,pct_identity\n"
                                   "X-2,ctg999_1,1,WP_FAKE,Example species,example,99\n")
    (res / "alias.csv").write_text("strain,gene,hit_rank,subject_acc,subject_organism,subject_def,pct_identity\n"
                                   "X-1,X-1__BGC001__a3 aa=300,1,WP_A3,Streptomyces sp. A,a3 hit,77\n")
    gv2 = root / "gv_mis.tsv"
    gv2.write_text(gv.read_text() +
                   "X-2\tb2\tncbi_clustered_nr\t99\t95.0\t10\t\tres/other.csv\n"   # only another gene's query
                   "X-1\ta3\tncbi_clustered_nr\t80\t77.0\t10\t\tres/alias.csv\n"   # proven alias
                   "X-1\ta1\tncbi_nr\t99\t96.0\t10\t\tres/other.csv\n")             # higher value, wrong query
    info = cec.build(gt, root, root / "om", gv2)
    g = {r["locus_tag"]: r for r in read(root / "om" / "ENZYME_GENES.tsv")}
    assert g["b2"]["blastp_top10_mean"] == "" and g["b2"]["top_hit_acc"] == ""
    assert g["b2"]["blastp_hold"] == "source query is ctg999_1, not this gene"
    assert (g["a3"]["blastp_top10_mean"], g["a3"]["top_hit_acc"], g["a3"]["blastp_hold"]) == ("77.0", "WP_A3", "")
    # a1's 96.0 row names a file without a1, so a1 keeps its own file's value and hit
    assert (g["a1"]["blastp_top10_mean"], g["a1"]["top_hit_acc"]) == ("58.25", "WP_1")
    assert info["genes_blastp_held_query_mismatch"] == 1
    assert cec.proven_alias("X-1__a3", "X-1", "a3") and not cec.proven_alias("X-2__a3", "X-1", "a3")
    assert not cec.proven_alias("X-1__xx__a3", "X-1", "a3")


def test_query_index_binds_an_old_query_name_by_protein_hash(cohort):
    root, gt, gv = cohort
    res = root / "res"
    (res / "old.csv").write_text("strain,gene,hit_rank,subject_acc,subject_organism,subject_def,pct_identity\n"
                                 "X-2,old_7,1,WP_OLD,Streptomyces sp. O,old hit,93\n")
    gv2 = root / "gv_q.tsv"
    gv2.write_text(gv.read_text() + "X-2\tb2\tncbi_clustered_nr\t93\t91.0\t10\t\tres/old.csv\n")
    seq = [ln.strip() for ln in (root / "X-2" / "package" / "X-2_proteins.faa").read_text().split(">") if ln.startswith("b2")]
    h = hashlib.sha256("".join(seq[0].splitlines()[1:]).encode()).hexdigest()
    qi = root / "qi.tsv"
    qi.write_text("strain\tgene\tsource_file\tprotein_sha256\tquery_aa_length\tbinding_evidence\n"
                  f"X-2\told_7\tres/old.csv\t{h}\t9\tledger_sha\n")
    cec.build(gt, root, root / "q0", gv2)
    assert {r["locus_tag"]: r for r in read(root / "q0" / "ENZYME_GENES.tsv")}["b2"]["blastp_hold"].startswith("source query is old_7")
    info = cec.build(gt, root, root / "q1", gv2, query_index=qi)
    g = {r["locus_tag"]: r for r in read(root / "q1" / "ENZYME_GENES.tsv")}
    assert (g["b2"]["blastp_top10_mean"], g["b2"]["top_hit_acc"], g["b2"]["blastp_hold"]) == ("91.0", "WP_OLD", "")
    assert info["genes_bound_by_sequence_alias"] == 1
    qi.write_text(qi.read_text().replace("ledger_sha", "none"))  # unbound rows are not used
    info = cec.build(gt, root, root / "q2", gv2, query_index=qi)
    assert info["genes_blastp_held_query_mismatch"] == 1


def test_cluster_and_realign_inputs_must_agree(cohort):
    root, gt, gv = cohort
    base = "centroid\tmember\nX-1|a1\tX-1|a1\nX-1|a1\tX-2|b1\nX-1|a2\tX-1|a2\n"
    (root / "c_dup.tsv").write_text(base + "X-1|a2\tX-2|b1\n")
    with pytest.raises(cec.CatalogError, match="listed again"):
        cec.read_clusters(root / "c_dup.tsv")
    (root / "c_self.tsv").write_text("X-1|a1\tX-2|b1\n")
    with pytest.raises(cec.CatalogError, match="not listed as their own member"):
        cec.read_clusters(root / "c_self.tsv")
    (root / "c_ok.tsv").write_text(base)
    (root / "r_stray.tsv").write_text("X-1|a2\tX-2|b1\t42\t290\t300\t300\t96\t98\t1e-9\t50\n")
    with pytest.raises(cec.CatalogError, match="not its cluster's"):
        cec.build(gt, root, root / "os", gv, root / "c_ok.tsv", root / "r_stray.tsv")
    (root / "r_conf.tsv").write_text("X-1|a1\tX-2|b1\t71\t290\t300\t300\t96\t98\t1e-9\t50\n"
                                     "X-1|a1\tX-2|b1\t42\t290\t300\t300\t96\t60\t1e-9\t50\n")
    with pytest.raises(cec.CatalogError, match="different values"):
        cec.read_realign(root / "r_conf.tsv")


def test_a_comma_in_the_shared_source_text_is_kept_not_invented():
    rec = [("smcog SMCOG1059: acetyl-CoA carboxylase, carboxyl transferase, alpha (E-value: 1)", []),
           ("smcog SMCOG1059: acetyl-CoA carboxylase, carboxyl transferase, beta (E-value: 1)", [])]
    names = cec.smcog_names(rec)
    assert names["SMCOG1059"].endswith("transferase,")


def test_excluded_contigs_are_left_out_of_tables_and_fasta(cohort):
    root, gt, gv = cohort
    ex = root / "ex.tsv"
    ex.write_text("strain\tcontig\treason\nX-2\tNODE_1_length_5000_cov_10\tlow coverage\n")
    info = cec.build(gt, root, root / "out", gv, exclude_contigs=ex)
    g = {r["locus_tag"] for r in read(root / "out" / "ENZYME_GENES.tsv")}
    assert g == {"a1", "a2", "a3", "a4"} and info["excluded_genes_by_strain"] == {"X-2": 2}
    assert info["excluded_contigs_matched"] == 1 and info["excluded_contigs_unmatched"] == []
    ex2 = root / "ex2.tsv"  # a typo, a trailing space and a strain not in the run
    ex2.write_text("strain\tcontig\nX-2\tNODE_1_length_5000_cov_10 \nX-1\tNODE_9_typo\nZ-9\tNODE_1\n")
    info2 = cec.build(gt, root, root / "out2", gv, exclude_contigs=ex2)
    assert info2["excluded_genes_by_strain"] == {"X-2": 2} and info2["excluded_contigs_matched"] == 1
    assert info2["excluded_contigs_unmatched"] == ["X-1\tNODE_9_typo", "Z-9\tNODE_1"]
    assert info2["excluded_strains_not_in_run"] == ["Z-9"]
    n = cec.emit_fasta(cec.read_genomes(gt, root), root / "f.faa", cec.read_excluded(ex))
    text = (root / "f.faa").read_text()
    assert n == 4 and "X-2|" not in text and text.count(">") == 4
    extra = root / "X-1" / "package" / "X-1_proteins.faa"
    extra.write_text(extra.read_text() + ">orphan bgc=none\nMSTNPKLLV\n")
    with pytest.raises(cec.CatalogError, match="in no gene_context record"):
        cec.emit_fasta(cec.read_genomes(gt, root), root / "f2.faa", cec.read_excluded(ex))
    with pytest.raises(cec.CatalogError, match="--exclude-contigs not found"):
        cec.read_excluded(root / "none.tsv")


def test_category_overrides_move_and_split(cohort, tmp_path):
    root, gt, gv = cohort
    ov = root / "ov.tsv"
    ov.write_text("family\taction\ttarget_category\n"
                  "SMCOG1007: cytochrome P450\tmove_family\tother\n"
                  "SMCOG1022: Beta-ketoacyl synthase\tsplit_context\tother\n"
                  "Not_in_run\tmove_family\tother\n")
    info = cec.build(gt, root, root / "out", gv, category_overrides=ov)
    g = {r["locus_tag"]: r for r in read(root / "out" / "ENZYME_GENES.tsv")}
    assert (g["a2"]["category"], g["a2"]["category_before_override"], g["a2"]["override"]) == ("other", "tailoring-oxidoreduction", "move_family")
    # KS genes sit in T1PKS regions (not broad calls), so split_context keeps them
    assert g["a1"]["category"] == "PKS-core" and g["a1"]["override"] == ""
    assert info["genes_moved_by_override"] == {"move_family": 1} and info["override_families_not_in_run"] == ["Not_in_run"]
    for bad, msg in (("F\tdrop\tother\n", "action"), ("F\tmove_family\tnowhere\n", "target_category"),
                     ("F\tmove_family\tother\nF\tsplit_context\tother\n", "listed twice")):
        b = root / "bad.tsv"
        b.write_text("family\taction\ttarget_category\n" + bad)
        with pytest.raises(cec.CatalogError, match=msg):
            cec.read_overrides(b)
    assert cec.broad_only("saccharide; fatty_acid") and not cec.broad_only("T1PKS; saccharide") and not cec.broad_only("")


def test_identity_is_four_part_plus_locus_and_missing_inventory_is_a_hold(cohort, tmp_path):
    root, gt, gv = cohort
    cec.build(gt, root, root / "out", gv)
    g = {r["locus_tag"]: r for r in read(root / "out" / "ENZYME_GENES.tsv")}
    assert g["a1"]["gene_identity"] == "X-1 / NODE_1_length_5000_cov_10 / region001 / BGC001 / a1"
    (root / "X-2" / "package" / "X-2_2_inventory.csv").unlink()
    info = cec.build(gt, root, root / "out2", gv)
    g = {r["locus_tag"]: r for r in read(root / "out2" / "ENZYME_GENES.tsv")}
    assert g["b1"]["gene_identity"] == "X-2 / ? / ? / BGC001 / b1" and info["identity_holds"] == 1


def test_family_summary_and_blocks(cohort):
    root, gt, gv = cohort
    cec.build(gt, root, root / "out", gv)
    f = {r["family"]: r for r in read(root / "out" / "ENZYME_FAMILY_SUMMARY.tsv")}
    ks = f["SMCOG1022: Beta-ketoacyl synthase"]
    assert (ks["genes"], ks["genomes"], ks["genes_with_blastp"], ks["median_blastp"]) == ("2", "2", "2", "73.1")
    assert ks["most_distant_gene"].endswith("/ a1 (300 aa)") and ks["subtype_tokens"] == "mod_KS 1; hyb_KS 1"
    assert (root / "out" / "ENZYME_CATEGORY_BY_BLOCK.tsv").is_file()


def test_specific_groups_from_cluster_output(cohort):
    root, gt, gv = cohort
    n = cec.emit_fasta(cec.read_genomes(gt, root), root / "pooled.faa")
    assert n == 6 and ">X-1|a1\n" in (root / "pooled.faa").read_text()
    (root / "cl.tsv").write_text("centroid\tmember\nX-1|a1\tX-1|a1\nX-1|a1\tX-2|b1\nX-1|a2\tX-1|a2\n"
                                 "X-1|a3\tX-1|a3\nX-1|a4\tX-1|a4\nX-2|b2\tX-2|b2\n")
    (root / "ra.tsv").write_text("X-1|a1\tX-2|b1\t71.5\t290\t300\t300\t96.7\t98.0\t1e-100\t400\n")
    info = cec.build(gt, root, root / "out", gv, root / "cl.tsv", root / "ra.tsv", "diamond cluster --approx-id 50")
    gs = read(root / "out" / "SPECIFIC_GROUPS.tsv")
    # fixture proteins all share one sequence, so later centroids carry -2, -3 suffixes
    assert gs[0]["group"].split("-")[0] == "G" + hashlib.sha256(b"MSTNPKLLV").hexdigest()[:10]
    assert gs[0]["group_rank"] == "1" and gs[0]["strains"] == "2" and gs[0]["members"] == "2"
    assert len({g["group"] for g in gs}) == len(gs)
    assert gs[0]["family"] == "SMCOG1022: Beta-ketoacyl synthase" and gs[0]["min_pct_id_to_centroid"] == "71.5"
    ms = [m for m in read(root / "out" / "SPECIFIC_MEMBERS.tsv") if m["group"] == gs[0]["group"]]
    assert {m["is_centroid"] for m in ms} == {"True", "False"}
    assert info["specific"]["groups"] == 5 and info["specific"]["groups_in_2plus_strains"] == 1
    assert info["specific"]["clusters"]["settings"] == "diamond cluster --approx-id 50"


def test_group_ids_are_stable_across_builds_and_crosswalk(cohort):
    root, gt, gv = cohort
    # distinct sequences so every centroid has its own hash
    for st_, tags in (("X-1", ("a1", "a2", "a3", "a4")), ("X-2", ("b1", "b2"))):
        faa = root / st_ / "package" / f"{st_}_proteins.faa"
        faa.write_text("".join(f">{t} bgc=BGC001\nM{t.upper()}KLV\n" for t in tags))
    (root / "cl.tsv").write_text("centroid\tmember\nX-1|a1\tX-1|a1\nX-1|a1\tX-2|b1\nX-1|a2\tX-1|a2\n"
                                 "X-1|a3\tX-1|a3\nX-1|a4\tX-1|a4\nX-2|b2\tX-2|b2\n")
    cec.build(gt, root, root / "o1", gv, root / "cl.tsv")
    # second build: same groups, different cluster file order, plus a crosswalk from the first build
    (root / "cl2.tsv").write_text("X-2|b2\tX-2|b2\nX-1|a4\tX-1|a4\nX-1|a1\tX-2|b1\nX-1|a1\tX-1|a1\nX-1|a3\tX-1|a3\nX-1|a2\tX-1|a2\n")
    info = cec.build(gt, root, root / "o2", gv, root / "cl2.tsv", previous_members=root / "o1" / "SPECIFIC_MEMBERS.tsv")
    g1 = {r["centroid"]: r["group"] for r in read(root / "o1" / "SPECIFIC_GROUPS.tsv")}
    g2 = {r["centroid"]: r["group"] for r in read(root / "o2" / "SPECIFIC_GROUPS.tsv")}
    assert g1 == g2 and g1["X-1|a1"] == "G" + hashlib.sha256(b"MA1KLV").hexdigest()[:10]
    xw = read(root / "o2" / "GROUP_CROSSWALK.tsv")
    assert all(r["previous_group"] == r["current_group"] for r in xw) and info["specific"]["crosswalk"]["exact_same_membership"] == 5


def test_cds_shared_by_two_regions_keeps_both_identities(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    shared = cds("s1", P450, ["p450"])
    g = package(root, "Y-1", {"BGC001": [cds("y1"), shared], "BGC002": [shared, cds("y2")]})
    (root / "g.tsv").write_text(f"strain\tgene_context\nY-1\t{g}\n")
    (root / "cl.tsv").write_text("Y-1|y1\tY-1|y1\nY-1|s1\tY-1|s1\nY-1|y2\tY-1|y2\n")
    info = cec.build(root / "g.tsv", root, root / "out", clusters=root / "cl.tsv")
    assert info["genes"] == 4 and info["specific"]["genes_in_two_or_more_regions"] == 1
    assert info["specific"]["genes_not_in_any_group"] == 0
    ms = [m["gene_identity"] for m in read(root / "out" / "SPECIFIC_MEMBERS.tsv") if m["gene_identity"].endswith("/ s1")]
    assert sorted(m.split(" / ")[3] for m in ms) == ["BGC001", "BGC002"]
    assert not (root / "out" / "ENZYME_CATEGORY_BY_BLOCK.tsv").exists()  # no block column: no block table


def test_refusals(cohort, monkeypatch):
    root, gt, gv = cohort
    (root / "bad.tsv").write_text("centroid\tmember\nX-1|a1\tX-1|a1\nX-1|a1\tX-9|zz\n")
    with pytest.raises(cec.CatalogError, match="not genes of this run"):
        cec.build(gt, root, root / "o1", gv, root / "bad.tsv")
    cec.build(gt, root, root / "o2", gv)
    with pytest.raises(cec.CatalogError, match="already holds"):
        cec.build(gt, root, root / "o2", gv)
    dup = root / "dup.tsv"
    dup.write_text(gt.read_text() + gt.read_text().splitlines()[1] + "\n")
    with pytest.raises(cec.CatalogError, match="more than once"):
        cec.read_genomes(dup, root)
    monkeypatch.setattr(cec, "hard_excluded", lambda: {"X-2"})
    with pytest.raises(cec.CatalogError, match="hard-excluded"):
        cec.read_genomes(gt, root)


def test_cli_exit_codes_and_quiet_success(cohort, capsys):
    root, gt, gv = cohort
    for argv in (["--genomes", str(gt), "--root", str(root)],
                 ["--genomes", str(gt), "--root", str(root), "--out", str(root / "o"), "--realign", str(gv)]):
        with pytest.raises(SystemExit) as e:
            cec.main(argv)
        assert e.value.code == 2 and "REFUSED" in capsys.readouterr().err
    assert cec.main(["--genomes", str(gt), "--root", str(root), "--out", str(root / "o"), "--gene-values", str(gv)]) == 0
    out = capsys.readouterr()
    assert out.out == "" and (root / "o" / "RUN_INFO.json").is_file()
