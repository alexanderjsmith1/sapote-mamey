"""Cross-source pre-fill for §25 §40 §41 §44 §46 §47 and four-component template filenames.

Fixtures use AS-XXX and synthetic references. Each test pins one failure that a naive
implementation makes: substring class matching, a denominator that swallows nested reference
or excluded folders, a node-number join across assemblies, a placeholder genus, a manifest
provenance string printed as a host, and a filename without contig and region.
"""
from __future__ import annotations

import json
import pathlib
import re

from mamey import modeb_template_emitter as em

TRIAGE_HEADER = ("BGC_ID,Node_ID,Contig,antiSMASH_Region,Products,Boundary,Assembly_Locator,"
                 "Length_kb,Lead_tier_auto,Corrected_rank,KCB_top,Strain\n")
INV_HEADER = "BGC_ID,Contig,antiSMASH_Region,Products,KCB_top,Strain\n"


def _pkg(root: pathlib.Path, name: str, inv_rows: str, *, taxonomy="sp.", display=None,
         profile="loose") -> pathlib.Path:
    pkg = root / name / "package"
    pkg.mkdir(parents=True)
    (pkg / f"{name}_1_intake.json").write_text(json.dumps({
        "strain_id": name, "display_name": display or name.replace("_", " "),
        "taxonomy": taxonomy, "antismash_profile": profile}))
    (pkg / f"{name}_2_inventory.csv").write_text(INV_HEADER + inv_rows)
    return pkg


def _world(tmp_path: pathlib.Path):
    cohort = tmp_path / "cohort"
    focal = _pkg(cohort, "AS-XXX",
                 "BGC033,NODE_4_length_100_cov_5.1,region002,NRPS; thioamide-NRP,enteromycin,AS-XXX\n"
                 "BGC032,NODE_4_length_100_cov_5.1,region001,terpene,carotenoid,AS-XXX\n")
    (focal / "manifest.json").write_text(json.dumps({"strain_id": "AS-XXX", "taxonomy": "sp.",
                                                     "source": "cohort rebuild engine 1.9"}))
    (focal / "manifest_short.json").write_text(json.dumps({"strain_id": "AS-XXX"}))
    (focal / "AS-XXX_4_triage_board.csv").write_text(
        TRIAGE_HEADER
        + "BGC033,NODE_4,NODE_4_length_100_cov_5.1,region002,NRPS; thioamide-NRP,Interior,x,40,HIGH,1,enteromycin,AS-XXX\n"
        + "BGC032,NODE_4,NODE_4_length_100_cov_5.1,region001,terpene,Interior,x,20,LOW,9,carotenoid,AS-XXX\n"
        + "BGC040,NODE_9,,region001,NRPS,Edge,x,10,LOW,20,,AS-XXX\n")
    (focal / "AS-XXX_gene_context.jsonl").write_text(json.dumps({"bgc_id": "BGC033", "cds": [
        {"locus_tag": "c4_1", "start": 1, "end": 900, "aa_length": 300, "gene_kind": "biosynthetic",
         "sec_met_domains": ["Condensation"], "has_translation": True},
        {"locus_tag": "c4_2", "start": 1000, "end": 1600, "aa_length": 200, "gene_kind": "regulatory",
         "sec_met_domains": ["TetR_N"], "has_translation": True}]}) + "\n")
    (focal / "AS-XXX_4A2_ClusterBlast_per_gene.csv").write_text(
        "bgc_id,query_gene,subject_gene,pct_identity,reference,reference_source\n"
        "BGC033,c4_1,s1,90,NZ_REF1,Ref genome one\n"
        "BGC033,c4_2,s2,80,NZ_REF1,Ref genome one\n")
    _pkg(cohort, "AS-2", "BGC001,ctgA,region001,NRPS; thioamide-NRP; PKS,colibrimycin,AS-2\n")
    _pkg(cohort, "AS-3", "BGC001,ctgB,region001,NRPS-like; thioamide-NRP-like,x,AS-3\n")
    _pkg(cohort, "AS-EX", "BGC001,ctgC,region001,NRPS; thioamide-NRP,x,AS-EX\n")
    _pkg(cohort / "_variants_excluded", "AS-2b", "BGC001,ctgD,region001,NRPS; thioamide-NRP,x,AS-2b\n")
    _pkg(cohort / "REFERENCE", "Genusa_alpha_T1",
         "BGC005,NC_1.1,region005,NRPS; thioamide-NRP,maduropeptin,\n", display="Genusa alpha T1",
         profile="relaxed")
    _pkg(cohort / "REFERENCE", "Othergenus_beta", "BGC001,NC_2.1,region001,NRPS; thioamide-NRP,x,\n",
         display="Othergenus beta")
    meta = tmp_path / "meta.tsv"
    meta.write_text("strain\tgenus\thost\tlocation\texcluded\texclusion_reason\n"
                    "AS-XXX\tGenusa sp.\tbee\t\t\t\n"
                    "AS-2\tOthergenus sp.\tbee\t\t\t\n"
                    "AS-3\tGenusa sp.\tbee\t\t\t\n"
                    "AS-EX\tThirdgenus sp.\tbee\t\tY\tcontaminated\n"
                    "AS-9\tFourthgenus sp.\tbee or wasp\t\t\t\n")
    gbks = tmp_path / "gbks"
    gbks.mkdir()
    (gbks / "AS-XXX_NODE_4_length_999_cov_7.2.region002.gbk").write_text("")
    em._PACKAGE_SCAN_CACHE.clear()
    return focal, cohort, meta, gbks


def _sections(card: str) -> dict[int, str]:
    parts = re.split(r"(?m)^## §(\d+) ", card)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}


def _emit(tmp_path, **src):
    focal, cohort, meta, gbks = _world(tmp_path)
    sources = {"cohort_dir": str(cohort), "reference_dir": str(cohort / "REFERENCE"),
               "strain_metadata": str(meta), "bigscape_regions_dir": str(gbks)}
    sources.update(src)
    return _sections(em.emit_card_template(focal, "BGC033", sources=sources))


def test_prevalence_uses_exact_tokens_and_a_bounded_denominator(tmp_path):
    s44 = _emit(tmp_path)[44]
    # AS-XXX + AS-2 match; AS-3 has only -like tokens; AS-EX is excluded; nested folders never counted
    assert "**Numerator:** 2 loci in 2 of 3 packages." in s44
    assert "AS-EX (contaminated)" in s44
    assert "AS-2b" not in s44 and "Genusa alpha" not in s44
    assert "BGC033 (this locus)" in s44


def test_prevalence_without_cohort_is_a_named_hold(tmp_path):
    s44 = _emit(tmp_path, cohort_dir=None)[44]
    assert "--cohort-dir" in s44 and "not evidence of absence" in s44


def test_bigscape_refuses_a_node_number_join_across_assemblies(tmp_path):
    s40 = _emit(tmp_path)[40]
    assert "IDENTITY HOLD" in s40 and "different assembly" in s40
    assert "Region GBK bound" not in s40


def test_bigscape_binds_on_the_exact_full_contig(tmp_path):
    focal, cohort, meta, gbks = _world(tmp_path)
    (gbks / "AS-XXX_NODE_4_length_100_cov_5.1.region002.gbk").write_text("")
    s40 = _sections(em.emit_card_template(focal, "BGC033", sources={"bigscape_regions_dir": str(gbks)}))[40]
    assert "Region GBK bound on the exact full contig" in s40
    assert "NODE_4_length_100_cov_5.1.region002.gbk" in s40


def test_reference_genus_comes_from_metadata_not_the_placeholder_manifest(tmp_path):
    s46 = _emit(tmp_path)[46]
    assert "*Genusa* (from strain metadata)" in s46
    assert "Genusa alpha T1 | relaxed | 1" in s46
    assert "Othergenus beta" not in s46
    assert "Profile compatibility" in s46


def test_reference_genus_unresolved_without_metadata(tmp_path):
    s46 = _emit(tmp_path, strain_metadata=None)[46]
    assert "Genus unresolved" in s46


def test_host_match_uses_deposited_host_not_manifest_source(tmp_path):
    s47 = _emit(tmp_path)[47]
    assert "**Host (as deposited):** bee" in s47
    assert "cohort rebuild" not in s47
    assert "| AS-2 | Othergenus sp. | — | 1 |" in s47
    assert "| AS-EX | Thirdgenus sp. | contaminated | 1 |" in s47
    assert "AS-3 " not in s47          # same genus is not 'unrelated'
    assert "AS-9" not in s47           # 'bee or wasp' is not 'bee'


def test_neighbourhood_and_phylogeny_targets(tmp_path):
    secs = _emit(tmp_path)
    assert "| BGC032 | region001 | terpene |" in secs[25] or "NOT_APPLICABLE" in secs[25]
    assert "`c4_1` | biosynthetic" in secs[41]
    assert "c4_2" not in secs[41]


def test_neighbourhood_body_reads_clusterblast(tmp_path):
    focal, *_ = _world(tmp_path)
    facts = em._bgc_facts(focal, "BGC033")
    facts["_pkg"] = str(focal)
    body = em._body_25_neighbourhood(facts)
    assert "| BGC032 | region001 | terpene |" in body
    assert "| NZ_REF1 | Ref genome one | 2 of 2 | 90 |" in body


def test_batch_filenames_carry_all_four_identity_fields(tmp_path):
    focal, *_ = _world(tmp_path)
    res = em.emit_batch(focal, scope="all")
    out = pathlib.Path(res["out"])
    assert (out / "AS-XXX__NODE_4_length_100_cov_5.1__region002__BGC033_template.md").exists()
    assert res["identity_holds"] == ["BGC040"]
    assert (out / "BGC040__IDENTITY_HOLD_template.md").exists()
    assert "AS-XXX__NODE_4_length_100_cov_5.1__region002__BGC033_template.md" in (out / "_INDEX.md").read_text()


def test_modeb_round_follows_the_emitted_path(tmp_path):
    from mamey.modeb_round import run_round
    focal, *_ = _world(tmp_path)
    res = run_round(focal, top_n=1, scope="top")
    entry = res["entries"][0] if "entries" in res else res["cards"][0]
    assert entry["template"].endswith("__BGC033_template.md")
    assert "template file not found" not in " ".join(entry["scaffold_errors"])
