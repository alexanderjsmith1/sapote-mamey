"""Regression tests for the v9.7.240 patch set (AS-421 Mode B / BLASTp campaign).

Five defects, all found while authoring Mode B cards for AS-421
(Streptosporangium sp., Bombus sp., 46 regions, MODERATE assembly):

  P1  modeb_template_emitter._over_merge_facts matched predicted_polymers.csv on
      the bare contig only, so every BGC sharing a contig with an over-merged
      region inherited a false OVER-MERGED banner (7 of 13 banners wrong).
  P2  authored_verify aliased single_protocluster_count (count of /kind="single"
      cand_clusters) onto ctx["protocluster_count"] (count of protocluster
      features). BGC041: 1 vs 3. modeb_structure_gate then raised FACT_MISMATCH
      against correct cards and passed incorrect ones.
  P3  UMED_PATTERNS used bare substrings and space-separated domain names, so
      `lant` matched `lanthipeptide` and `peptidase s9` never matched
      `Peptidase_S9`.
  P4  bgc_blastp_panel: --isolate-giants exploded whole BGC groups into
      singletons; the one_best scope hardcoded proteins_per_file=1000000.
  P5  blastp_online never populated BlastpHit.antismash_domains, so the CSV
      column was empty, reconcile() could only return REVIEW, and
      cluster_coherence saw zero core genes.

Hermetic: no network, no antiSMASH ZIP, no sealed package. Fixtures are built
in tmp_path from the minimum fields each unit reads.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# P1 — over-merge banner must match (contig, region), not contig alone
# ---------------------------------------------------------------------------

_POLYMER_HEADER = [
    "record_id", "region_number", "sc_number", "predicted_polymer",
    "predicted_smiles", "docking_used", "n_protoclusters", "candidate_kind",
    "over_merge_flag",
]

_YES = "YES (region likely >=2 BGCs; split before product claims)"


def _write_polymers(pkg: Path, strain: str, rows: list[dict]) -> None:
    with (pkg / f"{strain}_predicted_polymers.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_POLYMER_HEADER)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in _POLYMER_HEADER})


def _pkg(tmp_path: Path, strain: str = "AS-421") -> Path:
    pkg = tmp_path / strain / "package"
    pkg.mkdir(parents=True)
    # _strain_prefix() resolves the {strain}_predicted_polymers.csv filename from here
    (pkg / "manifest_short.json").write_text(json.dumps({"strain_id": strain}))
    return pkg


def test_p1_over_merge_banner_is_region_scoped(tmp_path):
    """NODE_2 region001 is over-merged; region003 (BGC018) is not.

    Pre-patch, BGC018 inherited region001's banner because only the contig was
    compared. Reproduces the AS-421 BGC018 false banner exactly.
    """
    from mamey import modeb_template_emitter as emit

    strain = "AS-421"
    pkg = _pkg(tmp_path, strain)
    contig = "NODE_2_length_553361_cov_80.858698"
    _write_polymers(pkg, strain, [
        {"record_id": contig, "region_number": "1", "n_protoclusters": "2",
         "candidate_kind": "neighbouring|single", "over_merge_flag": _YES},
        {"record_id": contig, "region_number": "2", "n_protoclusters": "1",
         "candidate_kind": "single", "over_merge_flag": "no"},
    ])

    over_merged = {"node": "NODE_2_length_553361_cov_80", "contig": contig, "region": "region001"}
    clean_row = {"node": "NODE_2_length_553361_cov_80", "contig": contig, "region": "region002"}
    # region003 has no polymer row at all (lanthipeptide region)
    no_row = {"node": "NODE_2_length_553361_cov_80", "contig": contig, "region": "region003"}

    assert emit._over_merge_facts(pkg, over_merged) == {
        "over_merge": True, "n_protoclusters": "2", "candidate_kind": "neighbouring|single"}
    assert emit._over_merge_facts(pkg, clean_row) == {}, "region002 is kind=single; must not inherit region001's banner"
    assert emit._over_merge_facts(pkg, no_row) == {}, "region003 has no polymer row; honest-blank, not inherited"


def test_p1_manifest_fallback_covers_regions_without_polymer_rows(tmp_path):
    """predicted_polymers.csv carries rows only for NRPS/PKS-bearing regions.

    A lanthipeptide+terpene merge would be invisible there. The manifest's
    protocluster_count (P2) is authoritative for every region.
    """
    from mamey import modeb_template_emitter as emit

    strain = "AS-421"
    pkg = _pkg(tmp_path, strain)
    _write_polymers(pkg, strain, [])  # no rows at all

    facts = {"node": "NODE_9_length_297282_cov_79", "contig": "NODE_9_length_297282_cov_79.143329",
             "region": "region001", "manifest_protocluster_count": 3}
    assert emit._over_merge_facts(pkg, facts) == {
        "over_merge": True, "n_protoclusters": 3, "candidate_kind": "?"}

    facts["manifest_protocluster_count"] = 1
    assert emit._over_merge_facts(pkg, facts) == {}


def test_p1_region_label_parsing():
    from mamey.modeb_template_emitter import _region_number
    assert _region_number("region002") == 2
    assert _region_number("region2") == 2
    assert _region_number("2") == 2
    assert _region_number("") is None
    assert _region_number(None) is None


# ---------------------------------------------------------------------------
# P2 — protocluster_count is not single_protocluster_count
# ---------------------------------------------------------------------------

def test_p2_bgcrecord_carries_a_distinct_protocluster_count():
    from mamey.models import BGCRecord
    fields = BGCRecord.__dataclass_fields__
    assert "protocluster_count" in fields, "P2: BGCRecord must expose the true protocluster count"
    assert "single_protocluster_count" in fields, "the cand_cluster count stays; it is a different number"


def test_p2_authored_verify_reads_protocluster_count_not_single(tmp_path, monkeypatch):
    """AS-421 BGC041: 3 protoclusters, 1 single-kind cand_cluster.

    Pre-patch the gate context said 1. A card correctly stating '3 protoclusters'
    then drew a FACT_MISMATCH, and a card stating '1' passed.
    """
    from mamey import authored_verify

    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({
        "strain_id": "AS-421",
        "bgcs": [{
            "bgc_id": "BGC041",
            "single_protocluster_count": 1,
            "protocluster_count": 3,
            "edge_status": "Interior",
        }],
    }))

    ctx = authored_verify._bgc_context_from_package(str(pkg), "BGC041")
    assert ctx is not None
    assert ctx.get("protocluster_count") == 3, (
        f"expected the antiSMASH protocluster count (3), got {ctx.get('protocluster_count')!r} "
        "— single_protocluster_count (1) is a different quantity")


# ---------------------------------------------------------------------------
# P3 — UMED pattern boundaries
# ---------------------------------------------------------------------------

@dataclass
class _CDS:
    contig: str = "NODE_13_length_203942_cov_78.201687"
    start: int = 0
    end: int = 100
    strand: int = 1
    locus_tag: str = "ctg13_x"
    product: str = ""
    translation: str = ""
    nucleotide_seq: str = ""
    qualifiers: dict = field(default_factory=dict)


def _umed_buckets(cds_list):
    from mamey.source_scans import _scan_patterns, UMED_PATTERNS
    res = _scan_patterns(cds_list, UMED_PATTERNS)
    return {k: [h["locus_tag"] for h in v] for k, v in res["hits"].items()}


def test_p3_lanthipeptide_genes_are_not_lanT_c39():
    """`lant` must not match `lanthipeptide` / `Lant_dehydr_N` / `Lanthipeptide_LanB_RRE`.

    AS-421 loci: ctg13_108 (44 aa RamS precursor), ctg13_111 (LanKC),
    ctg2_439 (LanB N-terminal half). None carries a C39 or a peptidase domain.
    """
    cds = [
        _CDS(locus_tag="ctg13_108", product="",
             qualifiers={"gene_functions": ["biosynthetic-additional (lanthipeptides) predicted lanthipeptide"]}),
        _CDS(locus_tag="ctg13_111", product="",
             qualifiers={"sec_met_domain": ["LANC_like", "Pkinase"],
                         "gene_functions": ["biosynthetic (rule-based-clusters) lanthipeptide-class-iii: micKC"]}),
        _CDS(locus_tag="ctg2_439", product="",
             qualifiers={"sec_met_domain": ["Lant_dehydr_N", "Lanthipeptide_LanB_RRE"]}),
    ]
    b = _umed_buckets(cds)
    assert b["LanT_C39_transporter_peptidase"] == [], (
        f"lanthipeptide machinery mis-bucketed as LanT/C39: {b['LanT_C39_transporter_peptidase']}")


def test_p3_lanB_dehydratase_is_not_lanT():
    """`Lant_dehydr_N` / `Lant_dehydr_C` are the LanB DEHYDRATASE, not a LanT.

    A guard that only rejects a trailing letter still lets `lant_dehydr_n` through;
    the trailing guard must reject `_` as well.
    """
    cds = [
        _CDS(locus_tag="ctg2_439", qualifiers={"sec_met_domain": ["Lant_dehydr_N", "Lanthipeptide_LanB_RRE"]}),
        _CDS(locus_tag="ctg2_441", qualifiers={"sec_met_domain": ["Lant_dehydr_C", "TIGR03891", "TIGR04364"]}),
    ]
    b = _umed_buckets(cds)
    assert b["LanT_C39_transporter_peptidase"] == [], b["LanT_C39_transporter_peptidase"]
    # ...but the RRE on ctg2_439 must still be seen (`_` is allowed BEFORE `rre`)
    assert b["RiPP_RRE"] == ["ctg2_439"]


def test_p3_real_lanT_still_matches():
    """The fix must not blind the bucket to an actual LanT."""
    cds = [
        _CDS(locus_tag="ctg9_1", product="lantibiotic ABC transporter LanT"),
        _CDS(locus_tag="ctg9_2", product="peptidase C39 family protein"),
        _CDS(locus_tag="ctg9_3", product="ABC transporter peptidase domain protein"),
    ]
    got = set(_umed_buckets(cds)["LanT_C39_transporter_peptidase"])
    assert got == {"ctg9_1", "ctg9_2", "ctg9_3"}, got


def test_p3_underscored_peptidase_domains_match():
    """antiSMASH writes `Peptidase_S9`, not `peptidase s9`.

    AS-421 ctg13_105 is the class-III leader-protease candidate and landed in no
    bucket pre-patch, while FlaP_AplP_S9_protease reported 0.
    """
    cds = [
        _CDS(locus_tag="ctg13_105", qualifiers={"sec_met_domain": ["Peptidase_S9", "Peptidase_S9_N"]}),
        _CDS(locus_tag="ctgX_1", qualifiers={"sec_met_domain": ["Peptidase_S8"]}),
    ]
    b = _umed_buckets(cds)
    assert "ctg13_105" in b["FlaP_AplP_S9_protease"]
    assert "ctgX_1" in b["LanP_S8_protease"]


def test_p3_rre_matches_across_underscore():
    """`\\brre\\b` fails on `Lanthipeptide_LanB_RRE` — `_` is a word character."""
    cds = [_CDS(locus_tag="ctg19_109", qualifiers={"sec_met_domain": ["Lanthipeptide_LanB_RRE"]})]
    assert "ctg19_109" in _umed_buckets(cds)["RiPP_RRE"]


def test_p3_no_false_positive_from_flap_endonuclease():
    """`flap` alone matched "flap endonuclease-1", a primary-metabolism DNA-repair gene."""
    cds = [_CDS(locus_tag="ctgY_1", product="flap endonuclease-1")]
    assert _umed_buckets(cds)["FlaP_AplP_S9_protease"] == []


def test_p3_untouched_buckets_keep_their_recall():
    """M16B / YcaO_TfuA / nucleoside_maturation are deliberately NOT re-guarded:
    `nik` and `m16` legitimately appear as prefixes (nikkomycin nikS, M16B)."""
    cds = [
        _CDS(locus_tag="a", qualifiers={"sec_met_domain": ["Peptidase_M16", "Peptidase_M16_C"]}),
        _CDS(locus_tag="b", product="YcaO-like protein"),
        _CDS(locus_tag="c", product="nikkomycin biosynthesis protein NikS"),
    ]
    b = _umed_buckets(cds)
    assert "a" in b["M16B_metalloprotease"]
    assert "b" in b["YcaO_TfuA_thioamide"]
    assert "c" in b["nucleoside_maturation"], "nik-prefix recall must survive the P3 patch"


# ---------------------------------------------------------------------------
# P4 — panel round packing
# ---------------------------------------------------------------------------

def _row(bgc, lt, aa):
    # assign_rounds sizes rounds with _residues(row) == len(row["sequence"])
    return {"bgc_id": bgc, "locus_tag": lt, "aa_len": aa, "sequence": "M" * aa, "slot": 1}


def test_p4a_isolate_giants_isolates_only_the_giant():
    """Pre-patch, one giant sent every protein of its BGC to a solo round."""
    from mamey.bgc_blastp_panel import assign_rounds
    rows = [_row("BGC007", "g_giant", 5129)] + [_row("BGC007", f"g{i}", 200) for i in range(6)]
    rounds = assign_rounds(rows, "AS-421", proteins_per_file=30, max_residues=85000,
                           giant_aa_threshold=2500, isolate_giants=True)
    sizes = sorted(len(r) for r in rounds)
    assert sizes == [1, 6], f"expected one solo giant + one packed round of 6, got {sizes}"
    solo = next(r for r in rounds if len(r) == 1)
    assert solo[0]["locus_tag"] == "g_giant"


def test_p4a_isolate_giants_no_giant_is_a_noop():
    from mamey.bgc_blastp_panel import assign_rounds
    rows = [_row("BGC001", f"g{i}", 300) for i in range(5)]
    rounds = assign_rounds(rows, "AS-421", proteins_per_file=30, max_residues=85000,
                           giant_aa_threshold=2500, isolate_giants=True)
    assert [len(r) for r in rounds] == [5]


def test_p4b_one_best_scope_honours_proteins_per_file(tmp_path):
    """AS-421: 46 BGCs -> one_best emitted a single 46-record file despite --proteins-per-file 30."""
    from mamey.bgc_blastp_panel import write_panel
    from mamey.models import BGCRecord, CDSFeature

    bgcs, cds = [], []
    for i in range(1, 47):
        contig = f"NODE_{i}_length_10000_cov_50.0"
        bgcs.append(BGCRecord(bgc_id=f"BGC{i:03d}", contig=contig, region_number=1,
                              start=0, end=9000, contig_length=10000,
                              antismash_region="region001", source_gbk=f"{contig}.region001.gbk",
                              node_id=f"NODE_{i}_length_10000_cov_50", products=["NRPS"],
                              mibig_hits=[], edge_status="Interior",
                              architecture_confidence="A", architecture_rationale=""))
        cds.append(CDSFeature(contig=contig, start=100, end=1000, strand=1,
                              locus_tag=f"ctg{i}_1", product="nonribosomal peptide synthetase",
                              translation="M" * 300))

    summary = write_panel(tmp_path, "AS-421", bgcs, cds,
                          genes_per_bgc=1, proteins_per_file=30, max_residues=85000,
                          first_pass_size=30, giant_aa_threshold=2500, isolate_giants=False)
    assert summary["one_best_unique_proteins"] == 46

    for faa in tmp_path.glob("*one_best*_for_BLASTP.faa"):
        n = faa.read_text().count(">")
        assert n <= 30, f"{faa.name} has {n} records; --proteins-per-file was 30"


# ---------------------------------------------------------------------------
# P5 — blastp-online must carry antiSMASH domains through
# ---------------------------------------------------------------------------

def test_p5_domains_of_strips_evalue_tail():
    from mamey.blastp_online import domains_of

    feat = _CDS(qualifiers={"sec_met_domain": [
        "PKS_KS (E-value: 6.2e-177, bitscore: 583.1, seeds: 2284, tool: rule-based-clusters)",
        "PKS_AT (E-value: 4.4e-90, bitscore: 293.9, seeds: 1685, tool: rule-based-clusters)",
        "PKS_KS (E-value: 1.0e-10, bitscore: 1.0, seeds: 1, tool: rule-based-clusters)",
    ]})
    assert domains_of(feat) == "PKS_KS; PKS_AT", "dedupe, order-preserving, no E-value tail"
    assert domains_of(_CDS()) == ""


def test_p5_reconcile_can_confirm_once_domains_are_present():
    """With an empty domain string reconcile() can only ever return REVIEW."""
    from mamey.blastp_online import reconcile

    hit = "type I polyketide synthase [Streptosporangium saharense]"
    assert reconcile("", hit) == "REVIEW"
    assert reconcile("PKS_KS; PKS_AT", hit) == "REVIEW"          # no shared >=4-char token
    assert reconcile("Thioesterase", "thioesterase domain-containing protein") == "CONFIRM"
    assert reconcile("Condensation", "condensation domain-containing protein") == "CONFIRM"
    assert reconcile("PKS_KS", "") == "NO_HIT"


def _hit(lt, aa, doms, hit_def, pid):
    from mamey.blastp_online import BlastpHit
    return BlastpHit(
        locus_tag=lt, aa_length=aa, antismash_domains=doms, blastp_top_def=hit_def,
        blastp_organism="Streptosporangium saharense", pct_identity=pid, query_coverage=100.0,
        top_hits=[{"hit_def": hit_def, "accession": "X", "organism": "Streptosporangium saharense",
                   "pct_identity": pid, "query_coverage": 100.0, "evalue": 0.0, "bitscore": 100.0}],
    )


def test_p5_cluster_coherence_sees_core_genes_when_domains_present():
    """n_core was always 0 because _is_core reads antismash_domains, which was never filled."""
    from mamey.blastp_online import cluster_coherence

    core_def = "NRPS/type I polyketide synthase [Streptosporangium saharense]"
    periph_def = "MFS transporter [Streptosporangium saharense]"

    blind = cluster_coherence([_hit("ctg6_206", 3116, "", core_def, 98.5),
                               _hit("ctg6_187", 428, "", periph_def, 96.7)])
    assert blind["identity_distribution"]["n_core"] == 0, "pre-condition: empty domains blind the core split"

    seeing = cluster_coherence([_hit("ctg6_206", 3116, "PKS_KS; AMP-binding", core_def, 98.5),
                                _hit("ctg6_187", 428, "MFS_3", periph_def, 96.7)])
    assert seeing["identity_distribution"]["n_core"] == 1
    assert seeing["identity_distribution"]["core_mean"] is not None


def test_p5_command_backfills_domains_into_the_csv(tmp_path, monkeypatch):
    """The real path: `mamey blastp-online` must write domains + a real agreement call.

    No network. run_batches_online is stubbed with the hit shape parse_blast_xml
    produces (antismash_domains=""), which is precisely the pre-patch defect.
    """
    from mamey import blastp_online as bo
    from mamey.models import CDSFeature

    feats = [
        CDSFeature(contig="NODE_6", start=201948, end=211298, strand=-1, locus_tag="ctg6_206",
                   product="", translation="M" * 50,
                   qualifiers={"sec_met_domain": [
                       "PKS_KS (E-value: 6.2e-177, bitscore: 583.1, seeds: 2284, tool: rule-based-clusters)",
                       "Thioesterase (E-value: 1.1e-10, bitscore: 34.0, seeds: 85, tool: rule-based-clusters)"]}),
        CDSFeature(contig="NODE_6", start=211392, end=212327, strand=-1, locus_tag="ctg6_207",
                   product="", translation="M" * 40,
                   qualifiers={"sec_met_domain": [
                       "FA_hydroxylase (E-value: 3.0e-09, bitscore: 27.0, seeds: 21, tool: rule-based-clusters)"]}),
    ]
    monkeypatch.setattr("mamey.parsers.extract_cds_features", lambda *_a, **_k: feats)

    class _Res:
        ok = True
        rid = "RID1"
        reason = ""
        def __init__(self, hits): self.hits = hits

    def _fake_batches(batches, **kw):
        hits = []
        for lt, seq in [(f.locus_tag, f.translation) for f in feats]:
            hd = {"ctg6_206": "thioesterase domain-containing protein [Streptosporangium saharense]",
                  "ctg6_207": "sterol desaturase family protein [Streptosporangium saharense]"}[lt]
            h = bo.BlastpHit(locus_tag=lt, aa_length=len(seq), antismash_domains="")  # as parse_blast_xml builds it
            h.blastp_top_def = hd
            h.blastp_organism = "Streptosporangium saharense"
            h.pct_identity, h.query_coverage, h.evalue, h.bitscore = 98.5, 100.0, 0.0, 500.0
            h.top_hits = [{"hit_def": hd, "accession": "X", "organism": "Streptosporangium saharense",
                           "pct_identity": 98.5, "query_coverage": 100.0, "evalue": 0.0, "bitscore": 500.0}]
            hits.append(h)
        return [_Res(hits)]

    monkeypatch.setattr(bo, "run_batches_online", _fake_batches)

    class _Args:
        package = "unused.zip"
        bgc = "BGC041"
        region = None
        database = "nr"
        evalue = "1e-5"
        batch_size = 10
        outdir = str(tmp_path)
    monkeypatch.setattr(bo, "_find_crosswalk", lambda _a: None)
    monkeypatch.setattr(bo, "_scope_feats", lambda *a, **k: feats)

    assert bo.blastp_online_command(_Args()) == 0

    rows = list(csv.DictReader((tmp_path / "BGC041_online_blastp.csv").open()))
    by = {r["locus_tag"]: r for r in rows}
    assert by["ctg6_206"]["antismash_domains"] == "PKS_KS; Thioesterase", "domains not backfilled into the CSV"
    assert by["ctg6_207"]["antismash_domains"] == "FA_hydroxylase"
    # `Thioesterase` appears in the hit def -> a real CONFIRM, not the constant REVIEW
    assert by["ctg6_206"]["agreement"] == "CONFIRM"
    assert by["ctg6_207"]["agreement"] == "REVIEW"

    reads = json.loads((tmp_path / "BGC041_cluster_reads.json").read_text())
    assert reads["coherence"]["identity_distribution"]["n_core"] == 1, (
        "cluster_coherence still blind: n_core must see the KS-bearing gene")
