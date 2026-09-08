"""Mobile-element / ICE demotion (#28) — synthetic-fixture tests for both halves.

(a) source layer: the HGT guard scans GENE-level annotations, so an ICE that antiSMASH mis-types as a
    biosynthetic class (e.g. "lanthipeptide-class-v", the WAC_01438 BGC032 pattern) is still recognized as
    mobile-dominant. A lone incidental flanking transposase is NOT dominant.
(b) scoring layer: a mobile-dominant region with no corroborated class evidence is demoted on AB/AF and
    dropped from corrected lead rank; a corroborated CCTT trigger exempts it (CCTT-veto discipline).

End-to-end acceptance on the real WAC_01438/WAC_01420 antiSMASH inputs remains gated on those genomes; these
fixtures exercise the logic directly.
"""
from types import SimpleNamespace
from mamey.models import BGCRecord, CDSFeature
from mamey.source_scans import resistance_tier_classification
from mamey.scoring import triage_bgcs


def _bgc(bgc_id="BGC032", contig="contig_1", start=10000, end=30000, products=("lanthipeptide-class-v",)):
    return BGCRecord(bgc_id=bgc_id, contig=contig, region_number=1, start=start, end=end,
                     contig_length=200000, products=list(products), mibig_hits=[],
                     protocluster_breakdown={}, notes="")


def _cds(product, start, end, contig="contig_1", locus_tag="cds"):
    return CDSFeature(contig=contig, start=start, end=end, strand=1, locus_tag=locus_tag, product=product)


def _rt(bgcs, cds):
    return resistance_tier_classification(bgcs, {"bgc_coupling": {}}, {"bgc_coupling": {}}, cds)["per_bgc"]


# ---- part (a): gene-level detection -------------------------------------------------------------

def test_ice_mistyped_as_lanthipeptide_is_mobile_dominant():
    bgc = _bgc(products=("lanthipeptide-class-v",))  # antiSMASH mis-call; the genes tell the real story
    cds = [_cds("phage integrase", 11000, 12000),
           _cds("FtsK/SpoIIIE family DNA translocase", 13000, 15000),
           _cds("plasmid replication initiator protein RepA", 16000, 17000)]
    rec = _rt([bgc], cds)["BGC032"]
    assert rec["mobile_dominant"] is True
    assert rec["hgt_guard"] == "MOBILE_CONTEXT_POSSIBLE"
    assert {"integrase", "conjugation", "rep_initiator"} <= set(rec["mobile_families"])


def test_single_incidental_transposase_is_not_dominant():
    bgc = _bgc(bgc_id="BGC044", products=("NRPS",))  # genuine cluster with one IS element nearby
    cds = [_cds("IS5 family transposase", 9000, 9500)]
    rec = _rt([bgc], cds)["BGC044"]
    assert rec["mobile_dominant"] is False
    assert rec["mobile_families"] == ["transposase"]  # detected, but a single family is not dominant


def test_no_mobile_genes_is_clean():
    bgc = _bgc(bgc_id="BGC044", products=("NRPS",))
    cds = [_cds("non-ribosomal peptide synthetase", 11000, 20000),
           _cds("MbtH-like protein", 21000, 21300)]
    rec = _rt([bgc], cds)["BGC044"]
    assert rec["mobile_dominant"] is False
    assert rec["hgt_guard"] == "NO_MOBILE_CONTEXT_SOURCE_DERIVED"
    assert rec["mobile_families"] == []


# ---- part (b): scoring demotion -----------------------------------------------------------------

def _scans(bgc_id, *, mobile_dominant, mobile_families, triggers=()):
    return SimpleNamespace(
        cctt={"per_bgc": {bgc_id: list(triggers)}, "context_uncorroborated_by_bgc": {}},
        resistance_tiers={"per_bgc": {bgc_id: {"tier": "NULL_NO_SOURCE_DERIVED_RESISTANCE",
                                               "mobile_dominant": mobile_dominant,
                                               "mobile_families": list(mobile_families)}}},
        primary_metabolism={"per_bgc": {}},
        misanchor_guards={"per_bgc": {}},
    )


def test_mobile_dominant_uncorroborated_is_demoted():
    bgc = _bgc(products=("lanthipeptide-class-v", "RiPP-like"))
    scans = _scans("BGC032", mobile_dominant=True, mobile_families=["integrase", "conjugation", "rep_initiator"])
    rec = {r.bgc_id: r for r in triage_bgcs([bgc], rggmci=None, scans=scans)}["BGC032"]
    assert rec.mobile_element_flag == "conjugation,integrase,rep_initiator"
    assert rec.ab_score <= 25.0 and rec.af_score <= 20.0     # AB/AF credit stripped to floor
    assert rec.corrected_rank is None                         # dropped from corrected lead rank


def test_mobile_dominant_but_corroborated_is_exempt():
    bgc = _bgc(products=("lanthipeptide-class-v",))
    # a corroborated CCTT class trigger means the region IS independently class-typed -> not demoted
    scans = _scans("BGC032", mobile_dominant=True, mobile_families=["integrase", "conjugation"],
                   triggers=["T43-LAN_lanthipeptide"])
    rec = {r.bgc_id: r for r in triage_bgcs([bgc], rggmci=None, scans=scans)}["BGC032"]
    assert rec.mobile_element_flag == ""
    assert rec.corrected_rank is not None


def test_clean_bgc_unaffected_by_guard():
    bgc = _bgc(bgc_id="BGC044", products=("NRPS",))
    scans = _scans("BGC044", mobile_dominant=False, mobile_families=[])
    rec = {r.bgc_id: r for r in triage_bgcs([bgc], rggmci=None, scans=scans)}["BGC044"]
    assert rec.mobile_element_flag == ""
    assert rec.corrected_rank is not None


# ---- BC2-407: rescue_bonus must respect the mobile-element floor, same as primary_flag ------------
# rescue_bonus (scoring.py) already exempted primary_flag ("flagged primary/pigment regions are not
# biosynthetic fragments to rescue") but never checked mobile_flag -- so a HIGH_RG_GMCI_RESCUE pairing
# could add its +8 back on top of the mobile guard's own ab<=25/af<=20 floor, directly contradicting
# the guard's own rationale text ("AB/AF credit suppressed") the moment rescue applied. No existing
# test exercised this combination -- every fixture above calls triage_bgcs with rggmci=None.

def test_mobile_dominant_uncorroborated_rescue_bonus_does_not_undo_the_floor():
    bgc = _bgc(products=("lanthipeptide-class-v",))
    scans = _scans("BGC032", mobile_dominant=True, mobile_families=["integrase", "conjugation"])
    rggmci = {"ranked_pairs": [{"bgc_a": "BGC032", "bgc_b": "BGC099", "pair": "BGC032+BGC099",
                                "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
                                "functional_rescue_class": "COMPLEMENTARY"}]}
    rec_no_rescue = {r.bgc_id: r for r in triage_bgcs([bgc], rggmci=None, scans=scans)}["BGC032"]
    rec_rescued = {r.bgc_id: r for r in triage_bgcs([bgc], rggmci=rggmci, scans=scans)}["BGC032"]
    # The mobile-element floor (ab<=25.0, af<=20.0) must hold regardless of RG-GMCI support.
    assert rec_rescued.ab_score <= 25.0 and rec_rescued.af_score <= 20.0
    # And the rescue must genuinely be a no-op on score, not merely "still under the floor by luck" --
    # the demoted region scores identically whether or not RG-GMCI ever saw it.
    assert (rec_rescued.ab_score, rec_rescued.af_score, rec_rescued.novelty_score) == (
        rec_no_rescue.ab_score, rec_no_rescue.af_score, rec_no_rescue.novelty_score)
    # The RG-GMCI pairing is still surfaced in the rationale for transparency -- this is a score-credit
    # guard, not a visibility suppression; a reviewer should still see the pairing existed.
    assert "RG-GMCI=HIGH_RG_GMCI_RESCUE via BGC032+BGC099" in rec_rescued.rationale
    assert rec_rescued.corrected_rank is None  # still excluded, same as before


# ---- #28 follow-up (v9.7.35): corroboration <-> mobile COMPOSITION -------------------------------
# Real case: WAC_01438 BGC032 (NZ_CP029601.1 region032). A mobile-dominant ICE that antiSMASH labels
# "lanthipeptide-class-v", so its T43-LAN trigger is label-CORROBORATED and (pre-fix) exempted the region
# from the mobile demotion -- but the lanthionine cyclase is ABSENT (architecture class confidence LOW).
# Pre-fix this impostor held rank-1 over the genuine flagship BGC044. The corroboration guard and the
# mobile guard must COMPOSE: a GATED class-defining trigger on a mobile-dominant region whose defining
# enzyme is absent is uncorroborated -> diagnostic bonus stripped, tier1_diag no longer set, demotion fires.

def test_28_mobile_dominant_class_trigger_enzyme_absent_is_demoted():
    """BGC032 pattern: mobile + T43-LAN label-corroborated + arch LOW (no cyclase) -> NOW demoted."""
    bgc = _bgc(products=("lanthipeptide-class-v", "RiPP"))
    bgc.architecture_class_confidence = "LOW"
    scans = _scans("BGC032", mobile_dominant=True,
                   mobile_families=["integrase", "conjugation", "rep_initiator"],
                   triggers=["T43-LAN_lanthipeptide"])
    rec = {r.bgc_id: r for r in triage_bgcs([bgc], rggmci=None, scans=scans)}["BGC032"]
    assert rec.mobile_element_flag != ""          # demotion FIRES (guards compose)
    assert rec.ab_score <= 25.0                   # T43-LAN diagnostic bonus stripped + AB floored
    assert rec.corrected_rank is None             # dropped from corrected lead rank


def test_28_mobile_dominant_class_trigger_enzyme_present_is_exempt():
    """Same mobile context + class trigger, but defining enzyme present (arch HIGH) -> still exempt."""
    bgc = _bgc(products=("lanthipeptide-class-v",))
    bgc.architecture_class_confidence = "HIGH"
    scans = _scans("BGC032", mobile_dominant=True, mobile_families=["integrase", "conjugation"],
                   triggers=["T43-LAN_lanthipeptide"])
    rec = {r.bgc_id: r for r in triage_bgcs([bgc], rggmci=None, scans=scans)}["BGC032"]
    assert rec.mobile_element_flag == ""          # enzyme present -> corroborated -> exempt
    assert rec.corrected_rank is not None


def test_28_promiscuous_trigger_on_mobile_low_arch_is_untouched():
    """BGC001 pattern: mobile + T43-HAL (PROMISCUOUS, never gated) + arch LOW -> NOT demoted by #28 path."""
    bgc = _bgc(bgc_id="BGC001", products=("NRPS", "halogenated"))
    bgc.architecture_class_confidence = "LOW"
    scans = _scans("BGC001", mobile_dominant=True, mobile_families=["integrase", "transposase"],
                   triggers=["T43-HAL_halogenase"])
    rec = {r.bgc_id: r for r in triage_bgcs([bgc], rggmci=None, scans=scans)}["BGC001"]
    assert rec.mobile_element_flag == ""


# ---- PC-12 (v9.7.37): domain/context-evidence corroboration on the RESISTANCE axis ---------------
# Real case: WAC_01438 BGC032. #28 fixed the CLASS path (uncorroborated T43-LAN no longer exempts the
# mobile demotion), but the region ALSO carries a T1 self-protection tier (APH_AAC) that independently
# kept tier1_diag/tier1_floor True -- so post-#28 the impostor was still a rank-3 Medium lead. The APH_AAC
# is NOT class-concordant with the cluster's product (class_concordant_groups == []) and the region is
# mobile-dominant: it is horizontally-acquired ICE cargo, not self-protection. PC-12 makes BOTH consumers
# of the T1 signal cargo-aware, so a non-concordant T1 on a mobile background no longer establishes a
# tier-1 diagnostic. The #28 fixture never modeled the resistance path; these tests close that gap.

def _scans_rt(bgc_id, *, tier, mobile_dominant, concordant, groups, triggers=()):
    return SimpleNamespace(
        cctt={"per_bgc": {bgc_id: list(triggers)}, "context_uncorroborated_by_bgc": {}},
        resistance_tiers={"per_bgc": {bgc_id: {
            "tier": tier,
            "mobile_dominant": mobile_dominant,
            "mobile_families": ["integrase", "conjugation", "transposase"],
            "resistance_groups": list(groups),
            "class_concordant_groups": list(concordant),
        }}},
        primary_metabolism={"per_bgc": {}},
        misanchor_guards={"per_bgc": {}},
    )


def test_pc12_mobile_t1_resistance_nonconcordant_is_cargo_demoted():
    """Mobile-dominant ICE + T1 self-protection whose group is NOT class-concordant -> cargo -> floored."""
    bgc = _bgc(products=("lanthipeptide-class-v", "RiPP"))
    bgc.architecture_class_confidence = "LOW"   # cyclase absent (so the class path is already uncorroborated)
    scans = _scans_rt("BGC032", tier="T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED",
                      mobile_dominant=True, concordant=[], groups=["APH_AAC"],
                      triggers=["T43-LAN_lanthipeptide"])
    rec = {r.bgc_id: r for r in triage_bgcs([bgc], rggmci=None, scans=scans)}["BGC032"]
    assert rec.mobile_element_flag != ""        # mobile demotion now fires on the resistance path too
    assert rec.ab_score <= 25.0                 # AB floored
    # AQUARIUS_01: class-gated bottom — the cargo is a specialized RiPP/lanthipeptide, so its bottom
    # label is 'Low', not 'Inventory'. The guarded property holds: it is NOT floated to Medium by the
    # cargo T1, and stays below the lead board.
    assert rec.lead_tier == "Low"               # NOT floated to Medium by the cargo T1 (tier1_floor cargo-aware)
    assert rec.corrected_rank is None           # dropped off the lead board


def test_pc12_mobile_t1_resistance_concordant_is_genuine_self_protection():
    """Over-reach guard: SAME mobile T1 tier, but the resistance IS class-concordant (genuine self-
    protection, e.g. an aminoglycoside cluster's own APH) -> tier-1 status retained, NOT demoted."""
    bgc = _bgc(products=("aminoglycoside",))
    scans = _scans_rt("BGC032", tier="T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED",
                      mobile_dominant=True, concordant=["aminoglycoside"], groups=["APH_AAC"])
    rec = {r.bgc_id: r for r in triage_bgcs([bgc], rggmci=None, scans=scans)}["BGC032"]
    assert rec.corrected_rank is not None       # concordant self-resistance keeps its lead status


def test_pc12_nonmobile_t1_resistance_untouched():
    """Conservative scope: a non-concordant T1 on a NON-mobile region is outside PC-12 -> unaffected."""
    bgc = _bgc(bgc_id="BGC044", products=("NRPS",))
    scans = _scans_rt("BGC044", tier="T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED",
                      mobile_dominant=False, concordant=[], groups=["APH_AAC"])
    rec = {r.bgc_id: r for r in triage_bgcs([bgc], rggmci=None, scans=scans)}["BGC044"]
    assert rec.corrected_rank is not None       # non-mobile T1 still establishes tier-1
