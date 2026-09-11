"""Tests for the HMM<->BLASTp division of labour: HMM does intrinsic structure (ordered domains,
module grammar, orphan rescue) and adjudicates BLASTp-vs-antiSMASH disagreements. Pure-logic
tests use synthetic HMM-hit dicts, so they run with or without pyhmmer/the HMM db installed."""
from mamey import hmm_blastp_adjudicate as adj


def test_adjudicate_supports_blastp_on_bgc006_esterase():
    # the ctg12_71 case: antiSMASH said Beta-lactamase, BLASTp said esterase; the α/β-hydrolase
    # domain signature settles it FOR BLASTp.
    hits = {"ctg12_71": [(10, "Abhydrolase_6", 120.5), (200, "Esterase", 88.0)]}
    r = adj.adjudicate(hits, "ctg12_71", "Beta-lactamase", "EstA serine hydrolase esterase")
    assert r["verdict"] == "SUPPORTS_BLASTP"
    assert r["supporting"]


def test_adjudicate_supports_antismash_when_fold_present():
    hits = {"g2": [(5, "Beta-lactamase_2", 90.0)]}
    r = adj.adjudicate(hits, "g2", "Beta-lactamase", "hypothetical protein")
    assert r["verdict"] == "SUPPORTS_ANTISMASH"


def test_adjudicate_insufficient_without_hmm_hits():
    r = adj.adjudicate({}, "g3", "p450", "cytochrome P450")
    assert r["verdict"] == "INSUFFICIENT"


def test_module_architecture_single_module_flag():
    arch = adj.module_architecture({"g": [(0, "PKS_KS", 210.0), (300, "Ketoacyl-synt_C", 57.0)]}, "g")
    assert arch["ks_modules"] == 1
    assert arch["single_module"] is True
    assert arch["domain_order"] == ["PKS_KS", "Ketoacyl-synt_C"]


def test_orphan_rescue_reports_hmm_family_where_blastp_empty():
    resc = adj.orphan_rescue({"ctg4_35": [(0, "Thiopeptide_F_RRE", 45.0)]}, {"ctg4_35": False})
    assert len(resc) == 1 and resc[0]["hmm_family"] == "Thiopeptide_F_RRE"


def test_orphan_rescue_skips_genes_with_blastp_hit():
    resc = adj.orphan_rescue({"g": [(0, "SomeDomain", 50.0)]}, {"g": True})
    assert resc == []


def test_walk_domains_degrades_without_db(monkeypatch):
    # no HMM db resolvable -> clean reason, no raise
    monkeypatch.setattr(adj, "resolve_hmm_db", lambda package_dir=None: None)
    hits, genes, reason = adj.walk_domains("/whatever.gbk")
    assert hits == {} and genes == [] and "HMM database" in reason


def test_adjudicate_no_signature_dict_when_neither_call_recognized():
    # v9.7.232 item-2: before the patch this fell through to AMBIGUOUS, indistinguishable from a
    # real disagreement. "widget polymerase" is deliberately not any dictionary entry.
    hits = {"g": [(0, "Some_Domain", 99.0)]}
    r = adj.adjudicate(hits, "g", "widget polymerase", "widget polymerase-like protein")
    assert r["verdict"] == "NO_SIGNATURE_DICT"


def test_adjudicate_lanthipeptide_terms_now_recognized():
    # v9.7.232 item-2: AS-705 BGC025 ctg275_6 case -- previously fell to AMBIGUOUS/NO_SIGNATURE_DICT.
    hits = {"ctg275_6": [(0, "PCMT", 50.0)]}
    r = adj.adjudicate(hits, "ctg275_6", "Lant_dehydr_C,PCMT",
                        "methyltransferase, FxLD system [Streptomyces sp.]")
    assert r["verdict"] == "SUPPORTS_BLASTP"


def test_adjudicate_abc_transporter_terms_now_recognized():
    hits = {"ctg2_19": [(0, "ABC_tran", 120.0)]}
    r = adj.adjudicate(hits, "ctg2_19", "transport",
                        "ABC transporter ATP-binding protein [Streptomyces sp.]")
    assert r["verdict"] == "SUPPORTS_BLASTP"


def test_adjudicate_still_insufficient_before_dict_check():
    # empty hits must still short-circuit to INSUFFICIENT, not NO_SIGNATURE_DICT -- these are
    # different failure modes (no HMM evidence at all, vs. HMM evidence the dictionary can't read).
    r = adj.adjudicate({}, "g", "widget polymerase", "widget polymerase-like protein")
    assert r["verdict"] == "INSUFFICIENT"


def test_orphan_rescue_backward_compatible_without_as_domains():
    # original behaviour must be byte-identical when as_domains is omitted.
    resc = adj.orphan_rescue({"ctg4_35": [(0, "Thiopeptide_F_RRE", 45.0)]}, {"ctg4_35": False})
    assert len(resc) == 1 and resc[0]["hmm_family"] == "Thiopeptide_F_RRE"
    resc2 = adj.orphan_rescue({"g": [(0, "SomeDomain", 50.0)]}, {"g": True})
    assert resc2 == []


def test_orphan_rescue_widened_trigger_on_missing_antismash_domain():
    # v9.7.232 item-1: BLASTp hit present, but antiSMASH left the domain field blank (typical for
    # a transport/regulatory gene) -- must now be rescued when as_domains is supplied.
    hits = {"g": [(0, "ABC_tran", 120.0)]}
    resc = adj.orphan_rescue(hits, {"g": True}, as_domains={"g": False})
    assert len(resc) == 1 and resc[0]["hmm_family"] == "ABC_tran"
    assert "antiSMASH" in resc[0]["note"]


def test_orphan_rescue_skips_when_both_channels_present():
    hits = {"g": [(0, "ABC_tran", 120.0)]}
    resc = adj.orphan_rescue(hits, {"g": True}, as_domains={"g": True})
    assert resc == []


def test_region_module_census_flags_true_trap():
    # a region labelled T1PKS with only ONE KS-like domain region-wide is a genuine trap candidate.
    genes = [{"lt": "g1", "hmm_domains": [(0, "PKS_KS", 200.0)]},
             {"lt": "g2", "hmm_domains": [(0, "ABC_tran", 90.0)]}]
    r = adj.region_module_census(genes, "PKS; T1PKS")
    assert r["trap_suspect"] is True
    assert r["n_ks_domains"] == 1


def test_region_module_census_does_not_flag_normal_single_module_nrps():
    # this is exactly the case my retracted gene-level check got wrong: a standalone
    # Condensation+AMP-binding NRPS gene is normal, single-protein biology.
    genes = [{"lt": "g1", "hmm_domains": [(0, "Condensation", 150.0), (300, "AMP-binding", 140.0)]}]
    r = adj.region_module_census(genes, "NRPS-like")
    assert r["expects_multi_module"] is False
    assert r["trap_suspect"] is False


def test_region_module_census_true_multi_module_region_not_flagged():
    genes = [{"lt": "g1", "hmm_domains": [(0, "PKS_KS", 200.0)]},
             {"lt": "g2", "hmm_domains": [(0, "PKS_KS", 190.0)]},
             {"lt": "g3", "hmm_domains": [(0, "Condensation", 100.0)]}]
    r = adj.region_module_census(genes, "PKS; T1PKS")
    assert r["trap_suspect"] is False
    assert r["n_ks_domains"] == 2


def test_adjudicate_helix_turn_helix_catches_gere():
    # v9.7.232 follow-up: AS-705 BGC028 ctg2_27 case -- "helix-turn-helix" token entry only had
    # "hth_", so a real GerE-family HTH domain (LuxR-type response regulator) fell through to
    # AMBIGUOUS despite being a textbook HTH signature. Caught during re-verification, not the
    # original patch pass.
    hits = {"ctg2_27": [(0, "GerE", 27.5)]}
    r = adj.adjudicate(hits, "ctg2_27", "(no antiSMASH call)",
                        "helix-turn-helix domain-containing protein [Streptomyces sp.]")
    assert r["verdict"] == "SUPPORTS_BLASTP"


def test_walk_domains_default_resolution_extracts_path_from_dict(monkeypatch, tmp_path):
    """item-1 (v9.7.207): resolve_hmm_db() returns a dict {path, ...}; walk_domains must extract
    'path' rather than hand the dict to the pyhmmer loader (was AttributeError 'dict' … 'readable').
    Covers the default-resolution path, which had no test."""
    import pytest
    pytest.importorskip("pyhmmer")
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    from Bio import SeqIO
    # minimal region GBK: one CDS with a translation
    rec = SeqRecord(Seq("ATG" + "GCT" * 60 + "TAA"), id="ctg1", name="ctg1", annotations={"molecule_type": "DNA"})
    rec.features.append(SeqFeature(FeatureLocation(0, 183), type="CDS",
                                   qualifiers={"locus_tag": ["ctg1_1"], "translation": ["M" + "A" * 60 + "*"]}))
    gbk = tmp_path / "region.gbk"; SeqIO.write(rec, str(gbk), "genbank")
    # resolve_hmm_db returns the real dict shape, pointing at the shipped scanner HMM
    from mamey.hmm_blastp_adjudicate import resolve_hmm_db as _real
    monkeypatch.setattr(adj, "resolve_hmm_db", lambda package_dir=None: _real())
    hits, genes, reason = adj.walk_domains(str(gbk))  # NO hmm_file -> default resolution (the bug path)
    # the dict-AttributeError signature must be gone; default resolution succeeds (reason empty)
    assert "readable" not in reason and "'dict'" not in reason, reason
    assert reason == "" or "HMM database" in reason  # scanned, or a clean db-absent degrade — never a crash
