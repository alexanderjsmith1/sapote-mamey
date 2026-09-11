"""Regression: HSAF/PTM antifungal AF-scoring (v9.7.19 P1 fix).

Guards the headline engine fix from the bee-cohort feedback. Two coupled defects:

  1. KCB-blind T43-PTM. A dedicated HSAF/PTM antifungal cluster whose identity lives in the
     knownclusterblast neighbourhood (NOT the antiSMASH product label) must fire T43-PTM and clear the
     dedicated-antifungal AF threshold, WITHOUT inflating a generic NRPS/PKS. The CDS-only scan missed it;
     couple_kcb_ptm now also reads the per-region KCB anchor (Route A) and a LONE hybrid-KS architecture
     (Route B, KCB-name-independent, gated on mod_KS being ABSENT so generic hybrids do not trip it).

  2. Dead diagnostic layer (deeper root cause, found while fixing #1). The scorer reads cctt["per_bgc"],
     but run_source_scans only ever set cctt["bgc_coupling"] -> the AF/AB diagnostic-bonus layer (T43-NUC
     included) was DEAD in production; it fired only in tests that mocked per_bgc directly. run_source_scans
     now bridges per_bgc = bgc_coupling.

Survey cases (AS-XXX BGC020 + AS-XXX BGC066 / AS-XXX BGC015 / AS-XXX BGC048 / AS-XXX BGC020): all are
generic-NRPS/PKS-labelled clusters whose KCB neighbourhood names HSAF/maltophilin/xanthobaccin-class
compounds. The KCB anchor strings below are REPRESENTATIVE HSAF/PTM names modelling that documented pattern
(the per-strain raw KCB files are not in-tree); the test asserts engine BEHAVIOUR, not specific KCB strings.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mamey.models import BGCRecord, CDSFeature
from mamey.scoring import triage_bgcs, AF_DIAGNOSTIC_TRIGGERS
from mamey.source_scans import run_source_scans

# base AF floor (20) + diagnostic bonus (25). A generic NRPS/PKS sits at 38 (20 + nrps 8 + t1pks 10),
# so 45 cleanly separates a diagnostic-confirmed antifungal from a generic hybrid.
AF_DEDICATED_THRESHOLD = 45
PTM_TRIG = "T43-PTM_hsaf_tetramate"

# Generic antiSMASH hybrid label in every survey case; the antifungal identity is KCB-only.
# Keys are synthetic fixture labels (SURVEY-N|BGCnnn); the strain half is deliberately not a real
# ID. FIXED v9.7.308: was keyed "AS-XXX|BGCnnn" with BGC020 duplicated (5 written, 4 survived —
# the dihydromaltophilin entry was silently discarded), one of the three AS_SCRUB dup-key gate
# allowlist sites. The test only uses label.split("|")[1] (the BGCnnn) and the value, so distinct
# SURVEY-N prefixes remove the collision without changing what is exercised.
SURVEY = {
    "SURVEY-1|BGC020": "heat-stable antifungal factor (HSAF) / dihydromaltophilin biosynthetic gene cluster",
    "SURVEY-2|BGC066": "maltophilin / dihydromaltophilin polycyclic tetramate macrolactam cluster",
    "SURVEY-3|BGC015": "xanthobaccin A/B antifungal biosynthetic gene cluster",
    "SURVEY-4|BGC048": "frontalamide / alteramide polycyclic tetramate macrolactam",
    "SURVEY-5|BGC020": "ikarugamycin-class HSAF tetramic-acid antifungal cluster",
}


def _bgc(bid, products, kcb_top=None, ccp="UNRESOLVED"):
    return BGCRecord(bgc_id=bid, region_number=1, products=list(products), contig="NODE_1", start=1000,
                     end=20000, contig_length=200000, edge_status="Interior", architecture_confidence="A",
                     kcb_top=kcb_top, closest_candidate_kcb_product=ccp)


def _run(bgc, cds=None):
    ss = run_source_scans([bgc], cds or [], {"NODE_1": "A" * 200000})
    rec = triage_bgcs([bgc], scans=ss)[0]
    trig = ss.cctt["bgc_coupling"].get(bgc.bgc_id, [])
    return rec.af_score, trig, ss


def test_t43ptm_registered_as_af_diagnostic_trigger():
    assert "T43-PTM" in AF_DIAGNOSTIC_TRIGGERS


def test_survey_hsaf_clusters_fire_and_clear_threshold():
    """AS-XXX BGC020 + the four other survey BGCs: T43-PTM fires from the KCB anchor and AF clears 45."""
    for label, kcb in SURVEY.items():
        bid = label.split("|")[1]
        af, trig, ss = _run(_bgc(bid, ["NRPS,T1PKS"], kcb_top=kcb))
        assert PTM_TRIG in trig, f"{label}: T43-PTM did not fire (trig={trig})"
        assert ss.cctt["ptm_kcb_coupling"].get(bid) == "kcb_anchor", f"{label}: wrong route"
        assert af >= AF_DEDICATED_THRESHOLD, f"{label}: af {af} below dedicated-antifungal threshold"


def test_generic_nrps_pks_not_inflated():
    """A generic hybrid with no PTM/HSAF KCB evidence must NOT fire T43-PTM and must stay below threshold."""
    af, trig, _ = _run(_bgc("BGCgen", ["NRPS,T1PKS"], kcb_top="Streptomyces sp. strain XYZ chromosome"))
    assert PTM_TRIG not in trig
    assert af < AF_DEDICATED_THRESHOLD, f"generic NRPS/PKS inflated to {af}"


def test_ptm_beats_generic_by_diagnostic_margin():
    af_ptm, _, _ = _run(_bgc("p", ["NRPS,T1PKS"], kcb_top=SURVEY["SURVEY-5|BGC020"]))
    af_gen, _, _ = _run(_bgc("g", ["NRPS,T1PKS"], kcb_top="Streptomyces sp. chromosome"))
    assert af_ptm - af_gen >= 25, f"diagnostic margin {af_ptm - af_gen} < 25"


def test_route_b_lone_hybrid_architecture_fires():
    """KCB-dark PTM (bare 'macrolactam', no compound name) + a LONE hybrid-KS megasynthase -> Route B."""
    bgc = _bgc("BGCarch", ["NRPS,T1PKS"], kcb_top="uncharacterised macrolactam natural product")
    cds = [CDSFeature("NODE_1", 1200, 9000, 1, "ks1", "iterative PKS-NRPS hybrid megasynthase", None, {})]
    af, trig, ss = _run(bgc, cds)
    assert PTM_TRIG in trig
    assert ss.cctt["ptm_kcb_coupling"].get("BGCarch") == "lone_hybrid_architecture"
    assert af >= AF_DEDICATED_THRESHOLD


def test_route_b_does_not_fire_on_multimodule_hybrid():
    """A hybrid carrying a ketosynthase CDS (mod_KS present -> not a lone hybrid) must NOT trip Route B."""
    bgc = _bgc("BGCmm", ["NRPS,T1PKS"], kcb_top="uncharacterised macrolactam natural product")
    cds = [CDSFeature("NODE_1", 1200, 9000, 1, "ks2", "hybrid PKS-NRPS ketosynthase module", None, {})]
    _, trig, ss = _run(bgc, cds)
    assert PTM_TRIG not in trig, "Route B fired on a multi-module hybrid (mod_KS present)"


def test_per_bgc_bridge_populated():
    """Latent-bug fix: run_source_scans must populate cctt['per_bgc'] (== bgc_coupling), else the
    diagnostic layer is dead in production (it fired only when a test mocked per_bgc)."""
    bgc = _bgc("BGCnuc", ["nucleoside", "other"], kcb_top="nikkomycin biosynthetic gene cluster")
    cds = [CDSFeature("NODE_1", 1200, 1900, 1, "nikJ", "nikkomycin nucleoside NikJ", None, {})]
    ss = run_source_scans([bgc], cds, {"NODE_1": "A" * 200000})
    assert ss.cctt.get("per_bgc") == ss.cctt.get("bgc_coupling")
    assert ss.cctt["per_bgc"].get("BGCnuc") == ["T43-NUC_nucleoside"]


def test_nucleoside_diagnostic_revived_end_to_end():
    """The per_bgc bridge end-to-end via the REAL pipeline (not a per_bgc mock): the T43-NUC
    diagnostic fires and floors the tier to at least Medium.

    v9.7.85 note: this test previously asserted ``af >= AF_DEDICATED_THRESHOLD`` (45). That only
    held because the keyword scorer was reading "nikkomycin" out of the kcb_top anchor TEXT and
    banking it as the BGC's own class credit — the KCB-anchor-text contamination fixed in P-7
    (scoring_class_text). On this synthetic BGC the architecture class-confidence is LOW
    (products "NRPS,T1PKS" → unresolved capacity), so the #28 guard correctly treats T43-NUC as
    uncorroborated and withholds the +25 AF *bonus*; the raw AF is 38. The tier floor is
    likewise corroborated-only (PC-12), so on THIS cross-class fixture the honest outcome is
    trigger-present + visible UNCORROBORATED exclusion + evidence-based tier; the compatible-
    class companion below proves the diagnostic layer still reaches lead tier end-to-end.
    """
    bgc = _bgc("BGCnuc2", ["NRPS,T1PKS"], kcb_top="nikkomycin biosynthetic gene cluster")
    cds = [CDSFeature("NODE_1", 1200, 1900, 1, "nikJ", "nikkomycin nucleoside NikJ", None, {})]
    ss = run_source_scans([bgc], cds, {"NODE_1": "A" * 200000})
    rec = triage_bgcs([bgc], scans=ss)[0]
    trig = ss.cctt["bgc_coupling"].get(bgc.bgc_id, [])
    assert "T43-NUC_nucleoside" in trig
    # .402 correction (kcb missing-evidence card): this cross-class fixture only ever reached
    # Medium through the removed `KCB is None -> novelty +5` credit-from-absence (51 -> 46
    # without it). The shipped tier floor is CORROBORATED-ONLY by design (v9.7.37 PC-12: an
    # ICE-cargo impostor must not float to Medium), and the #28 guard marks T43-NUC
    # uncorroborated on this NRPS,T1PKS locus — so the honest end-to-end outcome is: trigger
    # fires, guard excludes it VISIBLY in the rationale, tier reflects observed evidence.
    # OPEN POLICY FORK for the owner: this test's docstring expected an uncorroborated
    # diagnostic to still floor the tier; PC-12 says corroborated-only. Pinning shipped
    # behavior until the owner rules (a NUC~NRPS class-compatibility ruling would flip this
    # fixture to corroborated + floored).
    assert "CCTT-UNCORROBORATED" in rec.rationale and "T43-NUC" in rec.rationale
    assert rec.lead_tier == "Low", (
        f"uncorroborated diagnostic must not float tier (PC-12); got {rec.lead_tier}"
    )
    # The diagnostic layer stays alive end-to-end on a CLASS-COMPATIBLE locus: same gene
    # evidence, compatible product label -> AF diagnostic bonus carries it to lead tier.
    bgc_ok = _bgc("BGCnuc3", ["nucleoside", "other"], kcb_top="nikkomycin biosynthetic gene cluster")
    ss_ok = run_source_scans([bgc_ok], cds, {"NODE_1": "A" * 200000})
    rec_ok = triage_bgcs([bgc_ok], scans=ss_ok)[0]
    assert rec_ok.lead_tier in ("Medium", "High", "Exceptional"), (
        f"class-compatible nucleoside diagnostic lost lead tier: {rec_ok.lead_tier}"
    )


if __name__ == "__main__":  # allow running without pytest
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
    print("PTM AF-scoring regression: all tests pass")


def test_kcb_anchor_text_not_scored_as_own_class():
    """P-7 (v9.7.85): the keyword scorer must NOT credit class tokens that live only in the
    kcb_top genome-description blob. A bare `saccharide` BGC whose KCB anchor is a reference
    genome described as "... | Type: NRPS,NRPS-like,T1PKS,T2PKS" must score AB from saccharide
    ALONE — not from the reference organism's unrelated class tokens."""
    from mamey.scoring import scoring_class_text, product_text, score_keywords, AB_KEYWORDS
    bgc = _bgc("BGCsacc", ["saccharide"],
               kcb_top="Natronosporangium hydrolyticum strain DSM 106523 chromosome, "
                       "complete genome | Type: NRPS,NRPS-like,T1PKS,T2PKS")
    own = score_keywords(scoring_class_text(bgc), AB_KEYWORDS)
    contaminated = score_keywords(product_text(bgc), AB_KEYWORDS)
    # own-class credit must exclude the nrps/t1pks/t2pks that exist only in the anchor description
    assert own < contaminated, "scoring_class_text should exclude KCB-genome-description tokens"
    # and must not contain the contaminating PKS/NRPS class words
    ct = scoring_class_text(bgc)
    assert "natronosporangium" not in ct and "t2pks" not in ct, \
        f"KCB genome description leaked into scoring text: {ct!r}"


def test_resolved_mibig_product_still_scored():
    """The legitimate v9.7.19 path is preserved: a RESOLVED MIBiG product line
    (closest_candidate_kcb_product, not UNRESOLVED) is the matched-cluster product name and
    IS a valid own-class signal, so it must still reach the keyword scorer."""
    from mamey.scoring import scoring_class_text
    bgc = _bgc("BGCres", ["NRPS"], kcb_top="Streptomyces genome self-hit")
    # simulate a resolved MIBiG product line
    bgc.closest_candidate_kcb_product = "HSAF tetramic-acid antifungal"
    ct = scoring_class_text(bgc)
    assert "hsaf" in ct, f"resolved MIBiG product should be in scoring text: {ct!r}"
    # but the genome self-hit blob must NOT be
    assert "self-hit" not in ct
