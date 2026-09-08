"""BLACK_CHERRY_377: the RG-GMCI rationale note (`rg_note` in triage_bgcs) must reflect the SAME
rescue-eligibility gate (functional_rescue_class != ACCESSORY_ONLY) that governs the numeric
rescue_bonus/effective_penalty -- not just take support[0] unconditionally. Two failure shapes:

  (a) the sole ranked pair for a BGC is HIGH/MODERATE confidence but proof-2-refuted
      (ACCESSORY_ONLY) -> rescue_bonus is correctly 0 (covered by
      test_rggmci_subject_tiling.py::test_overlapping_paralog_gets_no_rescue_bonus), but the
      rationale text still asserted "RG-GMCI=HIGH_RG_GMCI_RESCUE via ..." as if a rescue had
      been granted -- a false claim-safety statement in the audit trail.
  (b) a BGC has TWO ranked pairs: an ineligible HIGH one and an eligible MODERATE one. The
      numeric bonus correctly falls back to the MODERATE credit (+4), but the rationale
      attributed the rescue to the wrong (ineligible, HIGH) pair.

Neither shape was exercised by the existing rggmci/scoring test surface -- every existing
fixture used either a single eligible pair or a single ineligible pair with no note-content
assertion, so this narrow-fixture gap masked the bug the same way the .374 rescue_bonus
zeroing fix was itself once masked before that card.
"""
import os, sys
from types import SimpleNamespace as NS
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from mamey.scoring import triage_bgcs


def _bgc(bid, products=("nrps",), contig="NODE_10_length_54129_cov_72", region="region001"):
    return NS(bgc_id=bid, products=list(products), mibig_hits=[], kcb_top="Streptomyces sp. chromosome",
              kcb_cumulative=None, riq_score=None, edge_status="Interior", architecture_confidence="C",
              contig=contig, node_id=contig, antismash_region=region,
              user_label=f"{bid} / {contig} {region}")


def test_rg_note_absent_when_sole_pair_is_ineligible():
    bgcs = [_bgc("BGC001"), _bgc("BGC002")]
    rggmci = {"ranked_pairs": [
        {"bgc_a": "BGC001", "bgc_b": "BGC002", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "ACCESSORY_ONLY", "pair": "BGC001-BGC002"},
    ]}
    scans = NS(cctt={"per_bgc": {}}, resistance_tiers={"per_bgc": {}})
    recs = triage_bgcs(bgcs, rggmci=rggmci, scans=scans)
    baseline = triage_bgcs(bgcs, rggmci=None, scans=scans)
    r0 = [r for r in recs if r.bgc_id == "BGC001"][0]
    b0 = [r for r in baseline if r.bgc_id == "BGC001"][0]
    # numeric scores are unaffected (already covered elsewhere) -- confirm still true here too
    assert (r0.ab_score, r0.af_score, r0.novelty_score) == (b0.ab_score, b0.af_score, b0.novelty_score)
    # the rationale must NOT claim RG-GMCI rescue support when zero bonus was actually granted
    assert "RG-GMCI=" not in r0.rationale, r0.rationale


def test_rg_note_attributes_the_eligible_pair_not_the_ineligible_one():
    bgcs = [_bgc("BGC001"), _bgc("BGC002"), _bgc("BGC003")]
    rggmci = {"ranked_pairs": [
        {"bgc_a": "BGC001", "bgc_b": "BGC002", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "ACCESSORY_ONLY", "pair": "BGC001-BGC002"},
        {"bgc_a": "BGC001", "bgc_b": "BGC003", "rggmci_confidence": "MODERATE_RG_GMCI_CANDIDATE",
         "functional_rescue_class": "COMPLEMENTARY", "pair": "BGC001-BGC003"},
    ]}
    scans = NS(cctt={"per_bgc": {}}, resistance_tiers={"per_bgc": {}})
    recs = triage_bgcs(bgcs, rggmci=rggmci, scans=scans)
    r1 = [r for r in recs if r.bgc_id == "BGC001"][0]
    assert "RG-GMCI=MODERATE_RG_GMCI_CANDIDATE via BGC001-BGC003" in r1.rationale
    assert "HIGH_RG_GMCI_RESCUE" not in r1.rationale


def test_rg_note_still_fires_for_a_genuinely_eligible_high_pair():
    """Backward-compat pin: a real eligible HIGH pair still produces the note (and the bonus)."""
    bgcs = [_bgc("BGC001"), _bgc("BGC002")]
    rggmci = {"ranked_pairs": [
        {"bgc_a": "BGC001", "bgc_b": "BGC002", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "COMPLEMENTARY", "pair": "BGC001-BGC002"},
    ]}
    scans = NS(cctt={"per_bgc": {}}, resistance_tiers={"per_bgc": {}})
    recs = triage_bgcs(bgcs, rggmci=rggmci, scans=scans)
    r0 = [r for r in recs if r.bgc_id == "BGC001"][0]
    assert "RG-GMCI=HIGH_RG_GMCI_RESCUE via BGC001-BGC002" in r0.rationale
