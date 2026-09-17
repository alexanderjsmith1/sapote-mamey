"""test_architecture_first.py — v2.2 with all regression + new path tests."""
import pytest
from mamey.architecture_first import (
    architecture_first_assessment as run,
    Concordance, PathwayType,
)

# === REGRESSION: v2 self-tests ===

def test_ptm_ipks_nrps():
    a,c,s = run([{'locus_tag':'g1','aa_length':'3100','sec_met_domains':'PKS_KS; AMP-binding; KR; ACP'},
                 {'locus_tag':'g2','aa_length':'450','sec_met_domains':'p450'}], "Interior","HSAF",2)
    assert s.product_class.startswith("PTM") and c.concordance == Concordance.CONCORDANT

def test_trans_at_vs_ptm_kcb_discordant():
    a,c,s = run([{'locus_tag':f'g{i}','aa_length':'1800','sec_met_domains':'PKS_KS; KR; ACP'} for i in range(5)]
                +[{'locus_tag':'at','aa_length':'400','sec_met_domains':'Acyl_transf_1'},
                  {'locus_tag':'fk','aa_length':'450','sec_met_domains':'FkbH'},
                  {'locus_tag':'n','aa_length':'1200','sec_met_domains':'AMP-binding; Condensation'}],
                "Interior","clifednamide A",3)
    assert 'trans-AT' in s.product_class and c.concordance == Concordance.DISCORDANT

def test_t2pks_size_based():
    a,c,s = run([{'locus_tag':'g1','aa_length':'420','sec_met_domains':'PKS_KS; ketoacyl-synt'},
                 {'locus_tag':'g2','aa_length':'415','sec_met_domains':'PKS_KS; Ketoacyl-synt_C'},
                 {'locus_tag':'g3','aa_length':'85','sec_met_domains':'PP-binding'},
                 {'locus_tag':'g4','aa_length':'270','sec_met_domains':'Polyketide_cyc'}],"Interior","chlortetracycline",2)
    assert s.product_class == "T2PKS (aromatic polyketide)"

def test_bactoprenol_primary_metab():
    a,c,s = run([{'locus_tag':'g1','aa_length':'355','sec_met_domains':'polyprenyl_synt'},
                 {'locus_tag':'g2','aa_length':'265','sec_met_domains':'PG_binding_1; YkuD'}],"Interior")
    assert s.product_class.startswith("primary metabolism")

def test_edge_downgrade():
    a,c,s = run([{'locus_tag':'g1','aa_length':'3100','sec_met_domains':'PKS_KS; AMP-binding; KR; ACP'},
                 {'locus_tag':'g2','aa_length':'450','sec_met_domains':'p450'}],"Edge","HSAF",2)
    assert a.confidence_raw == "HIGH" and a.confidence == "MEDIUM"

def test_unknown_strong_kcb_defers():
    a,c,s = run([{'locus_tag':'g1','aa_length':'200','sec_met_domains':'DUF1234'}],"Interior","erythromycin",1)
    assert c.concordance == Concordance.ARCHITECTURE_DEFERS

def test_pqq_tigr02109_is_pqq_not_mycofactocin():
    # v9.7.432: antiSMASH TIGR02109 = PQQ_syn_pqqE (AS-78 BGC010 ctg137_10, with PqqA/PqqD/PQQ Pfams)
    a,c,s = run([{'locus_tag':'g1','aa_length':'374','sec_met_domains':'Radical_SAM; TIGR02109'},
                 {'locus_tag':'g2','aa_length':'97','sec_met_domains':'PqqD'}],"Interior")
    assert s.product_class == PathwayType.PQQ.value
    assert a.has_tigr02109

def test_mycofactocin_tigr03962_not_ranthipeptide():
    # v9.7.432: AS-78 BGC047 — TIGR03962 (mycofact_rSAM, 9.4e-199) + SPASM + TIGR04085 on ctg87_19,
    # TIGR03967 + Mycofactocin_RRE on ctg87_20. Old rule returned ranthipeptide HIGH.
    a,c,s = run([{'locus_tag':'ctg87_19','aa_length':'413','sec_met_domains':'Radical_SAM; SPASM; TIGR03962; TIGR04085'},
                 {'locus_tag':'ctg87_20','aa_length':'107','sec_met_domains':'Mycofactocin_RRE; TIGR03967'},
                 {'locus_tag':'ctg87_12','aa_length':'510','sec_met_domains':'Glycos_transf_2; TIGR03965'},
                 {'locus_tag':'ctg87_15','aa_length':'239','sec_met_domains':'Creatininase; TIGR03964'}],"Edge")
    assert s.product_class == PathwayType.MYCOFACTOCIN.value
    assert a.has_tigr03962 and a.has_tigr03967 and a.has_mycofactocin_rre

def test_mycofactocin_mftb_rre_without_tigr03962():
    a,c,s = run([{'locus_tag':'g1','aa_length':'107','sec_met_domains':'Mycofactocin_RRE; TIGR03967'},
                 {'locus_tag':'g2','aa_length':'413','sec_met_domains':'Radical_SAM; SPASM'}],"Interior")
    assert s.product_class == PathwayType.MYCOFACTOCIN.value

def test_ranthipeptide_rsam_requires_ssf_marker():
    # SPASM alone (no SSF, no TIGR03962) must not be called ranthipeptide HIGH
    a,c,s = run([{'locus_tag':'g1','aa_length':'413','sec_met_domains':'Radical_SAM; SPASM; TIGR04085'}],"Interior")
    assert s.product_class != PathwayType.RANTHIPEPTIDE.value
    a,c,s = run([{'locus_tag':'g1','aa_length':'413','sec_met_domains':'Radical_SAM; SPASM'},
                 {'locus_tag':'g2','aa_length':'60','sec_met_domains':'SSF'}],"Interior")
    assert s.product_class == PathwayType.RANTHIPEPTIDE.value

def test_ni_siderophore():
    a,c,s = run([{'locus_tag':'g1','aa_length':'476','sec_met_domains':'IucA_IucC; FhuF'},
                 {'locus_tag':'g2','aa_length':'539','sec_met_domains':'IucA_IucC; FhuF'}],"Interior")
    assert s.product_class == "NIS siderophore"

# === v2.1 keyword additions ===

def test_tra_ks_trans_at():
    a,c,s = run([{'locus_tag':'g1','aa_length':'1800','sec_met_domains':'tra_KS; KR; ACP'},
                 {'locus_tag':'g2','aa_length':'1700','sec_met_domains':'tra_KS; DH; ACP'}],"Interior")
    assert 'trans-AT' in s.product_class and a.has_tra_ks

def test_pks_at_embedded_stays_cis():
    a,c,s = run([{'locus_tag':'g1','aa_length':'1800','sec_met_domains':'PKS_KS; PKS_AT; KR; ACP'},
                 {'locus_tag':'g2','aa_length':'1700','sec_met_domains':'PKS_KS; PKS_AT; ACP'}],"Interior")
    assert s.product_class == "cis-AT T1PKS"

def test_standalone_pks_at_trans():
    a,c,s = run([{'locus_tag':'g1','aa_length':'1800','sec_met_domains':'PKS_KS; KR; ACP'},
                 {'locus_tag':'g2','aa_length':'1700','sec_met_domains':'PKS_KS; ACP'},
                 {'locus_tag':'at','aa_length':'400','sec_met_domains':'PKS_AT'}],"Interior")
    assert 'trans-AT' in s.product_class and a.has_standalone_at

def test_faal_hybrid():
    a,c,s = run([{'locus_tag':'g1','aa_length':'1800','sec_met_domains':'PKS_KS; KR; ACP'},
                 {'locus_tag':'g2','aa_length':'1700','sec_met_domains':'PKS_KS; ACP'},
                 {'locus_tag':'g3','aa_length':'1600','sec_met_domains':'PKS_KS; KR'},
                 {'locus_tag':'fa','aa_length':'600','sec_met_domains':'FAAL'}],"Interior")
    assert any(g.has_amp for g in a.gene_classifications)

def test_t2ks_t2clf_t2pks():
    a,c,s = run([{'locus_tag':'g1','aa_length':'430','sec_met_domains':'t2ks'},
                 {'locus_tag':'g2','aa_length':'410','sec_met_domains':'t2clf'}],"Interior")
    assert s.product_class == "T2PKS (aromatic polyketide)" and a.has_t2pks

def test_indsynth_indolocarbazole():
    a,c,s = run([{'locus_tag':'g1','aa_length':'500','sec_met_domains':'IndSynth'},
                 {'locus_tag':'g2','aa_length':'300','sec_met_domains':'p450'}],"Interior","rebeccamycin",2)
    assert s.product_class == "indolocarbazole" and a.has_indsynth
    assert c.concordance == Concordance.CONCORDANT

def test_trna_pus_nucleoside():
    a,c,s = run([{'locus_tag':'g1','aa_length':'400','sec_met_domains':'tRNA_PUS'},
                 {'locus_tag':'g2','aa_length':'300','sec_met_domains':'Methyltransf_21'}],"Interior")
    assert s.product_class == "nucleoside" and a.has_trud

# === v2.2 fixes ===

def test_hybrid_threshold_two_megasynthases():
    """Fix 2: Two megasynthases (1 PKS + 1 NRPS) should classify as hybrid."""
    a,c,s = run([
        {'locus_tag':'g1','aa_length':'1800','sec_met_domains':'PKS_KS; KR; ACP'},
        {'locus_tag':'g2','aa_length':'1500','sec_met_domains':'AMP-binding; Condensation'},
    ],"Interior")
    assert 'hybrid' in s.product_class.lower() or 'PKS' in s.product_class

def test_terpene_priority_megasynthases_win():
    """Fix 1: Megasynthases + terpene cyclase → hybrid, not terpene."""
    a,c,s = run([
        {'locus_tag':'g1','aa_length':'1800','sec_met_domains':'PKS_KS; KR; ACP'},
        {'locus_tag':'g2','aa_length':'1500','sec_met_domains':'AMP-binding; Condensation'},
        {'locus_tag':'g3','aa_length':'354','sec_met_domains':'Terpene_syn_C_2'},
    ],"Interior")
    assert 'terpene' not in s.product_class.lower(), \
        f"Megasynthases present but classified as {s.product_class}"

def test_lassopeptide_wired():
    """Fix 3: Asn_synthase + Lasso_RRE should classify as lassopeptide."""
    a,c,s = run([
        {'locus_tag':'g1','aa_length':'399','sec_met_domains':'Asn_synthase'},
        {'locus_tag':'g2','aa_length':'83','sec_met_domains':'Stand_Alone_Lasso_RRE'},
        {'locus_tag':'g3','aa_length':'200','sec_met_domains':'Transglut_core3'},
    ],"Interior")
    assert s.product_class == "lassopeptide RiPP"

def test_ranthipeptide_radical_sam():
    # v9.7.432: this test previously fed TIGR03962 (which antiSMASH names mycofact_rSAM = MftC) and
    # asserted ranthipeptide. TIGR03962 now routes to mycofactocin; the YcaO-independent
    # ranthipeptide path is SPASM + SSF/SCIFF.
    a,c,s = run([
        {'locus_tag':'g1','aa_length':'450','sec_met_domains':'Radical_SAM; SPASM; TIGR04085'},
        {'locus_tag':'g2','aa_length':'55','sec_met_domains':'SSF'},
    ],"Interior")
    assert s.product_class == "ranthipeptide/SCIFF RiPP"
    # and the old input is now mycofactocin, never ranthipeptide
    a,c,s = run([
        {'locus_tag':'g1','aa_length':'450','sec_met_domains':'Radical_SAM; SPASM; TIGR03962'},
        {'locus_tag':'g2','aa_length':'80','sec_met_domains':'PqqD'},
    ],"Interior")
    assert s.product_class == PathwayType.MYCOFACTOCIN.value


@pytest.mark.parametrize("genes", [
    [
        {'locus_tag':'lasso1','aa_length':'399','sec_met_domains':'Asn_synthase'},
        {'locus_tag':'lasso2','aa_length':'83','sec_met_domains':'Stand_Alone_Lasso_RRE'},
    ],
    [{'locus_tag':'nuc1','aa_length':'400','sec_met_domains':'tRNA_PUS'}],
    [{'locus_tag':'hop1','aa_length':'620','sec_met_domains':'SQHop_cyclase'}],
    [{'locus_tag':'mft1','aa_length':'374','sec_met_domains':'Radical_SAM; TIGR02109'}],
])
def test_diagnostic_architecture_reasoning_is_capacity_not_product_identity(genes):
    architecture, _concordance, _summary = run(genes, "Interior")
    assert "class-level capacity hypothesis" in architecture.reasoning
    assert "not product identity" in architecture.reasoning

def test_faal_guard_no_false_nrps():
    """Fix 5: Standalone FAAL without KS or condensation → NOT classified as NRPS."""
    a,c,s = run([
        {'locus_tag':'g1','aa_length':'550','sec_met_domains':'FAAL'},
        {'locus_tag':'g2','aa_length':'200','sec_met_domains':'DUF1234'},
    ],"Interior")
    assert s.product_class != "NRPS", \
        f"Standalone FAAL should not trigger NRPS, got {s.product_class}"


# ── BH-CG-01 (v9.7.122) — APH word-boundary, no substring false positives ──────
def test_aph_no_false_positive_aphanizomenon():
    a, c, s = run([{"locus_tag": "g1", "aa_length": "300",
                    "sec_met_domains": "APHANIZOMENON_domain"}], "Interior")
    assert not a.has_aph
    assert not any("APH self-resistance" in m for m in a.diagnostic_markers)


def test_aph_no_false_positive_embedded_substring():
    a, c, s = run([{"locus_tag": "g1", "aa_length": "300",
                    "sec_met_domains": "xAPHx"}], "Interior")
    assert not a.has_aph


def test_aph_marker_appended_on_second_token():
    a, c, s = run([{"locus_tag": "g1", "aa_length": "300",
                    "sec_met_domains": "foo; APH"}], "Interior")
    assert a.has_aph
    assert any("APH self-resistance" in m for m in a.diagnostic_markers)
    # dedup: marker must appear exactly once
    assert sum("APH self-resistance" in m for m in a.diagnostic_markers) == 1
