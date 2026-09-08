"""B1 (v9.7.8) guards: permanent-exclusion standing-rule downgrades, corrected_rank, habitat placeholder.

Covers the 12-genome WomBee report:
- P1-1: saccharide/NAPAA/hglE-KS downgrades enforced in the board (`standing_rule_flag` + `corrected_rank`).
- P1-2: habitat must not be silently inferred from provenance/taxonomy → `ENGINE_DEFAULT_PLACEHOLDER`.

Claim-safety invariants checked:
- saccharide reads the BGC's OWN product class, not the KCB anchor (KCB = similarity, not identity).
- hglE-KS downgrade preserves the structural-novelty score (only the drug-lead claim is downgraded).

Standalone: python3 tests/test_standing_rules_b1.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.models import BGCRecord
from mamey.scoring import triage_bgcs, standing_rule_for
from mamey.master_workbook import _infer_habitat


def _bgc(bgc_id, products, kcb_top=None, kcb=None):
    return BGCRecord(bgc_id=bgc_id, contig="c1", region_number=1, start=1, end=9000, contig_length=20000,
                     products=list(products), edge_status="Interior", architecture_confidence="A",
                     kcb_top=kcb_top, kcb_cumulative=kcb)


def _scans(pm=None):
    return SimpleNamespace(primary_metabolism={"per_bgc": pm or {}}, cctt={"per_bgc": {}},
                           resistance_tiers={"per_bgc": {}})


def _by_id(recs):
    return {r.bgc_id: r for r in recs}


def test_saccharide_downgraded_and_excluded_from_corrected_rank():
    bgcs = [_bgc("BGC024", ["saccharide"], kcb=90000), _bgc("BGC001", ["NRPS", "T1PKS"])]
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    assert recs["BGC024"].standing_rule_flag == "saccharide-exclusion"
    assert recs["BGC024"].lead_tier == "Inventory"
    assert recs["BGC024"].corrected_rank is None
    assert recs["BGC001"].corrected_rank == 1   # the only non-downgraded lead


def test_saccharide_in_kcb_anchor_only_does_not_downgrade():
    """KCB = similarity not identity: a real NRPS whose anchor carries a saccharide arm is NOT downgraded."""
    bgcs = [_bgc("BGC002", ["NRPS"], kcb_top="streptomycin saccharide hybrid")]
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    assert recs["BGC002"].standing_rule_flag == ""
    assert recs["BGC002"].corrected_rank == 1


def test_napaa_neutral_not_downgraded():
    # build -q: NAPAA is NEUTRAL (common, adjacent to real BGCs) -> no standing-rule downgrade, stays ranked.
    bgcs = [_bgc("BGC050", ["other"], kcb_top="NAPAA epsilon-poly-L-lysine")]
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    assert recs["BGC050"].standing_rule_flag == ""        # no NAPAA exclusion fires
    assert recs["BGC050"].corrected_rank is not None       # remains in the corrected lead order


def test_committed_lead_with_saccharide_arm_not_downgraded():
    """A real polyene-macrolide (T1PKS) with a mycosamine saccharide arm must KEEP its lead status."""
    bgcs = [_bgc("BGC030", ["PKS", "T1PKS", "saccharide"], kcb=31000)]
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    assert recs["BGC030"].standing_rule_flag == ""    # committed class → not a standing-rule target
    assert recs["BGC030"].corrected_rank == 1         # stays IN the corrected lead order (not excluded)


def test_hgle_ks_noted_not_downgraded_novelty_preserved():
    """build -q: hglE-KS is NOTED, not downgraded -> no exclusion, stays ranked; novelty still intact."""
    bgcs = [_bgc("BGC013", ["other"], kcb_top="hglE-KS PREV-001 glycolipid", kcb=None)]
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    r = recs["BGC013"]
    assert r.standing_rule_flag == ""        # hglE no longer fires a standing-rule downgrade
    assert r.corrected_rank is not None       # remains in the corrected lead order
    # v9.7.402 (audit W402-23): was `> 30.0`, riding on a since-removed +5 credit for missing KCB
    # evidence (KCB-dark != observed novelty). The actual property this test checks — hglE-KS
    # handling does not suppress/zero the base novelty — holds at exactly the base score too.
    assert r.novelty_score >= 30.0   # structural novelty NOT downgraded by the hglE-KS handling


def test_corrected_rank_skips_downgraded_and_primary_metab():
    bgcs = [_bgc("BGC_A", ["NRPS"]), _bgc("BGC_B", ["saccharide"]),
            _bgc("BGC_C", ["T1PKS"]), _bgc("BGC_D", ["terpene"])]
    pm = {"BGC_D": {"families": ["pigment"]}}   # primary/pigment-flagged
    recs = _by_id(triage_bgcs(bgcs, None, _scans(pm=pm)))
    assert recs["BGC_B"].corrected_rank is None         # standing-rule downgraded
    assert recs["BGC_D"].corrected_rank is None         # primary-metab flagged
    ranked = sorted([r for r in recs.values() if r.corrected_rank], key=lambda r: r.corrected_rank)
    assert [r.bgc_id for r in ranked] == ["BGC_A", "BGC_C"] or [r.bgc_id for r in ranked] == ["BGC_C", "BGC_A"]
    assert {r.corrected_rank for r in ranked} == {1, 2}


def test_standing_rule_for_uses_own_products_for_saccharide():
    assert standing_rule_for("saccharide", "nrps") == "saccharide-exclusion"
    assert standing_rule_for("nrps", "nrps saccharide anchor") == ""   # anchor-only does not fire


def test_habitat_user_source_kept_inference_placeholdered():
    assert _infer_habitat("honeybee gut isolate") == "4_Hymenoptera"
    assert _infer_habitat("Sphagnum moss") == "3_Bryophyte_lichen"
    assert _infer_habitat("rhizosphere soil") == "1_Terrestrial_soil"
    # provenance / type-strain / empty must NOT be guessed
    assert _infer_habitat("ATCC type strain") == "ENGINE_DEFAULT_PLACEHOLDER"
    assert _infer_habitat("SID1328") == "ENGINE_DEFAULT_PLACEHOLDER"
    assert _infer_habitat("") == "ENGINE_DEFAULT_PLACEHOLDER"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")


# v9.7.61 CCTT co-occurrence exemption for hglE-KS
def test_hgle_ks_cctt_exemption_suppresses_downgrade():
    """hglE-KS downgrade is suppressed when a CCTT trigger fires on the same BGC (tambjamine/T43-NN case)."""
    from mamey.scoring import triage_bgcs
    from mamey.models import BGCRecord
    from types import SimpleNamespace

    bgc = BGCRecord(
        bgc_id="BGC_CCTT_EXEMPT", contig="NODE_2", region_number=1,
        start=1, end=50000, contig_length=168000,
        products=["PKS", "azoxy-crosslink", "fatty_acid", "hglE-KS", "other"],
        edge_status="Interior", kcb_cumulative=7196, kcb_top="BGC0002381.3",
        architecture_confidence="HIGH",
    )
    scans = SimpleNamespace(
        cctt={"per_bgc": {"BGC_CCTT_EXEMPT": ["T43-NN_n_n_bond"]},
              "context_uncorroborated_by_bgc": {}},
        cassette={}, primary_metabolism={"per_bgc": {}},
        resistance_tiers={"per_bgc": {}},
    )
    records = triage_bgcs([bgc], scans=scans)
    result = records[0]
    assert result.standing_rule_flag == "", (
        f"hglE-KS downgrade should be suppressed by T43-NN trigger, "
        f"got standing_rule_flag={result.standing_rule_flag!r}"
    )


def test_hgle_ks_no_cctt_still_downgraded():
    """hglE-KS downgrade fires normally when NO CCTT trigger is present."""
    from mamey.scoring import triage_bgcs
    from mamey.models import BGCRecord
    from types import SimpleNamespace

    bgc = BGCRecord(
        bgc_id="BGC_HGLE_PLAIN", contig="NODE_43", region_number=1,
        start=1, end=40000, contig_length=80000,
        products=["PKS", "T1PKS", "hglE-KS"],
        edge_status="Interior", kcb_cumulative=6424, kcb_top="BGC0002497.3",
        architecture_confidence="HIGH",
    )
    scans = SimpleNamespace(
        cctt={"per_bgc": {}, "context_uncorroborated_by_bgc": {}},
        cassette={}, primary_metabolism={"per_bgc": {}},
        resistance_tiers={"per_bgc": {}},
    )
    records = triage_bgcs([bgc], scans=scans)
    result = records[0]
    assert "hgle" in result.standing_rule_flag.lower(), (
        f"Expected hglE-KS-PREV-001 downgrade, got {result.standing_rule_flag!r}"
    )


# ── BH-007 / BH-007b (v9.7.122) — iron/metal-acquisition exclusions ────────────
# NI-siderophore and NRP-metallophore are registry downgrade rules. They fire when the
# BGC's own class is iron/metal-acquisition, but the committed-class guard protects a
# real NRPS/PKS/RiPP/lanthipeptide backbone that merely co-carries the acquisition arm.

def test_bh007_pure_ni_siderophore_downgraded():
    assert standing_rule_for("ni-siderophore other", "ni-siderophore other") == "NI-siderophore-exclusion"


def test_bh007b_pure_nrp_metallophore_downgraded():
    assert standing_rule_for("nrp-metallophore other", "nrp-metallophore other") == "NRP-metallophore-exclusion"


def test_bh007_mixed_lanthipeptide_lead_preserved():
    # AS-901 BGC017: lanthipeptide-class-iii + ni-siderophore — the lanthipeptide lead must survive
    assert standing_rule_for("lanthipeptide-class-iii ni-siderophore",
                             "lanthipeptide-class-iii ni-siderophore") == ""


def test_bh007b_mixed_nrps_lead_preserved():
    # NRP backbone scoring is legitimate — only the metallophore component is the exclusion target
    assert standing_rule_for("nrps nrp-metallophore other", "nrps nrp-metallophore other") == ""
    assert standing_rule_for("nrps ni-siderophore", "nrps ni-siderophore") == ""


def test_bh007_anchor_only_does_not_fire():
    # KCB anchor mentioning a siderophore must not downgrade a committed lead (KCB = similarity)
    assert standing_rule_for("nrps", "nrps coelibactin ni-siderophore anchor") == ""
