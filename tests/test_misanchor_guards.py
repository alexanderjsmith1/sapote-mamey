"""§4.1/§4.2 gene-filter mis-anchor guards.

KCB = similarity, not identity. A product-name anchor lacking its class's committed diagnostic is spurious
for the locus:
  - aminoglycoside (2-deoxystreptamine) anchor WITHOUT a DOIS (2-deoxy-scyllo-inosose synthase) gene
  - polyene-macrolide anchor WITHOUT a modular-PKS backbone (>=4 PKS_KS domains)
The scorer suppresses the anchor-derived AB/AF credit unless a Tier-1 diagnostic independently fires.

Standalone: python3 tests/test_misanchor_guards.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.models import BGCRecord, CDSFeature
from mamey.source_scans import scan_misanchor_guards
from mamey.scoring import triage_bgcs


def _bgc(bgc_id, products, anchor="", ks=0, start=1, end=9000):
    return BGCRecord(bgc_id=bgc_id, contig="c1", region_number=1, start=start, end=end, contig_length=50000,
                     products=list(products), edge_status="Interior", architecture_confidence="A",
                     closest_candidate_kcb_product=anchor, ks_domain_count=ks)


def _cds(product, start=100, end=400):
    return CDSFeature(contig="c1", start=start, end=end, strand=1, locus_tag="x", product=product, translation="M")


def test_aminoglycoside_without_dois_is_misanchor():
    bgcs = [_bgc("BGC056", ["NRPS"], anchor="gentamicin C")]
    per = scan_misanchor_guards([_cds("hypothetical protein")], bgcs)["per_bgc"]
    assert per["BGC056"]["aminoglycoside_anchor"] and not per["BGC056"]["dois_present"]
    assert per["BGC056"]["aminoglycoside_misanchor"]


def test_aminoglycoside_with_dois_is_supported():
    bgcs = [_bgc("BGC100", ["aminoglycoside"], anchor="kanamycin")]
    per = scan_misanchor_guards([_cds("2-deoxy-scyllo-inosose synthase")], bgcs)["per_bgc"]
    assert per["BGC100"]["dois_present"] and not per["BGC100"]["aminoglycoside_misanchor"]


def test_polyene_without_pks_backbone_is_misanchor():
    bgcs = [_bgc("BGC018", ["NRPS", "saccharide", "RiPP-like"], anchor="natamycin", ks=0)]
    per = scan_misanchor_guards([_cds("DUF692 family protein")], bgcs)["per_bgc"]
    assert per["BGC018"]["polyene_anchor"] and per["BGC018"]["polyene_misanchor"]


def test_polyene_with_big_pks_is_supported():
    """BGC030 control: a genuine polyene with a modular PKS backbone (ks=8) is NOT a mis-anchor."""
    bgcs = [_bgc("BGC030", ["T1PKS", "saccharide"], anchor="ECO-02301", ks=8)]
    per = scan_misanchor_guards([_cds("polyketide synthase")], bgcs)["per_bgc"]
    assert per["BGC030"]["polyene_anchor"] and not per["BGC030"]["polyene_misanchor"]


def test_scorer_floors_aminoglycoside_misanchor_ab():
    bgcs = [_bgc("BGC056", ["NRPS"], anchor="gentamicin")]
    scans = SimpleNamespace(primary_metabolism={"per_bgc": {}}, cctt={"per_bgc": {}},
                            resistance_tiers={"per_bgc": {}},
                            misanchor_guards={"per_bgc": {"BGC056": {"aminoglycoside_misanchor": True}}})
    r = {x.bgc_id: x for x in triage_bgcs(bgcs, None, scans)}["BGC056"]
    assert r.ab_score <= 25.0 and "aminoglycoside" in r.misanchor_flag


def test_scorer_floors_polyene_misanchor_af():
    bgcs = [_bgc("BGC018", ["RiPP-like"], anchor="natamycin", ks=0)]
    scans = SimpleNamespace(primary_metabolism={"per_bgc": {}}, cctt={"per_bgc": {}},
                            resistance_tiers={"per_bgc": {}},
                            misanchor_guards={"per_bgc": {"BGC018": {"polyene_misanchor": True, "ks_domain_count": 0}}})
    r = {x.bgc_id: x for x in triage_bgcs(bgcs, None, scans)}["BGC018"]
    assert r.af_score <= 20.0 and "polyene" in r.misanchor_flag


def test_corroborated_nucleoside_af_survives_stray_polyene_anchor():
    """H4 / PI ruling (the Developer or User, 2026-08-05): "Don't demote nucleosides. They are antifungals. Any
    nucleoside machinery should be noted and brought to the user's attention."

    This INTENTIONALLY INVERTS the v9.7.337 MISANCHOR-01 assertion (previously
    `test_unrelated_tier1_trigger_does_not_rescue_a_polyene_anchor`). A `RiPP-like` locus with a
    stray `natamycin` polyene KCB anchor (0 PKS KS domains) AND a corroborated `T43-NUC` nucleoside
    diagnostic must NOT have its independent antifungal credit clamped to 20 by the polyene
    mis-anchor guard. The polyene-comparator credit is still withheld (no polyene backbone exists),
    but the nucleoside AF machinery keeps its credit and is SURFACED in the flag for the human.

    The clamp still fires when the polyene anchor is the SOLE AF evidence — see
    `test_scorer_floors_polyene_misanchor_af` (AF 20, no nucleoside trigger) and the `bare` leg of
    `test_polyene_clamp_bare_vs_nucleoside`. Narrowing, not removing, the guard.

    NOTE for the cut chat: this reverses a shipped assertion by explicit PI decision. Bless it
    consciously, as v9.7.335 did for test_blastp_online and .336 for the convergence fallback.
    """
    bgcs = [_bgc("BGC018", ["RiPP-like"], anchor="natamycin", ks=0)]
    scans = SimpleNamespace(primary_metabolism={"per_bgc": {}},
                            cctt={"per_bgc": {"BGC018": ["T43-NUC_nucleoside"]}},
                            resistance_tiers={"per_bgc": {}},
                            misanchor_guards={"per_bgc": {"BGC018": {"polyene_misanchor": True,
                                                                     "ks_domain_count": 0}}})
    r = {x.bgc_id: x for x in triage_bgcs(bgcs, None, scans)}["BGC018"]
    # nucleoside machinery is surfaced to the human, not silently sunk ...
    assert "nucleoside_AF_machinery_present" in r.misanchor_flag, r.misanchor_flag
    # ... and the independent antifungal credit is NOT clamped to the mis-anchor floor
    assert r.af_score > 20.0, r.af_score


def test_unrelated_tier1_trigger_does_not_rescue_an_aminoglycoside_anchor():
    """Same, on the AB axis: an antifungal nucleoside trigger must not lift the DOIS clamp."""
    bgcs = [_bgc("BGC056", ["RiPP-like"], anchor="kanamycin", ks=0)]
    scans = SimpleNamespace(primary_metabolism={"per_bgc": {}},
                            cctt={"per_bgc": {"BGC056": ["T43-NUC_nucleoside"]}},
                            resistance_tiers={"per_bgc": {}},
                            misanchor_guards={"per_bgc": {"BGC056": {"aminoglycoside_misanchor": True}}})
    r = {x.bgc_id: x for x in triage_bgcs(bgcs, None, scans)}["BGC056"]
    assert "aminoglycoside" in r.misanchor_flag, r.misanchor_flag
    assert r.ab_score <= 25.0, r.ab_score


def test_polyene_clamp_bare_vs_nucleoside():
    """H4 narrowing (PI ruling 2026-08-05): the polyene clamp is now SOLE-EVIDENCE-specific.

    - `bare` (stray polyene anchor, no independent AF diagnostic) -> AF stays clamped to 20:
      the locus has no polyene backbone and nothing else supports antifungal capacity.
    - `nuc`  (same anchor + corroborated T43-NUC nucleoside diagnostic) -> AF is NOT demoted, and
      the nucleoside machinery is surfaced in the flag. Nucleosides are antifungals.
    """
    bgcs = [_bgc("BGC018", ["RiPP-like"], anchor="natamycin", ks=0)]
    def _run(cctt):
        scans = SimpleNamespace(primary_metabolism={"per_bgc": {}}, cctt={"per_bgc": cctt},
                                resistance_tiers={"per_bgc": {}},
                                misanchor_guards={"per_bgc": {"BGC018": {"polyene_misanchor": True,
                                                                         "ks_domain_count": 0}}})
        return {x.bgc_id: x for x in triage_bgcs(bgcs, None, scans)}["BGC018"]
    bare = _run({})
    nuc = _run({"BGC018": ["T43-NUC_nucleoside"]})
    assert bare.af_score <= 20.0, bare.af_score          # polyene anchor alone -> still clamped
    assert "polyene_anchor" in bare.misanchor_flag        # and the mis-anchor warning is shown
    assert nuc.af_score > 20.0, nuc.af_score             # corroborated nucleoside AF -> not demoted
    assert "nucleoside_AF_machinery_present" in nuc.misanchor_flag  # surfaced for a human


def test_arylpolyene_class_is_not_a_polyene_anchor():
    """Regression: an arylpolyene (pigment) class must NOT read as a polyene-macrolide anchor (BGC013)."""
    bgcs = [_bgc("BGC013", ["PKS", "arylpolyene"], anchor="a201a", ks=1)]
    per = scan_misanchor_guards([_cds("hypothetical protein")], bgcs)["per_bgc"]
    assert per["BGC013"]["polyene_anchor"] is False and per["BGC013"]["polyene_misanchor"] is False


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")


def test_anchor_tokens_bounded_against_organism_names():
    """v9.7.18: anchors match compound names as whole tokens, not as prefixes of KCB organism epithets
    (cohort sweep: 'Streptomyces filipinensis' must NOT fire the polyene gate). enzyme/domain is the evidence,
    not an organism name."""
    from mamey.source_scans import _POLYENE_ANCHOR as P, _AMINOGLYCOSIDE_ANCHOR as A
    assert not P.search("Streptomyces filipinensis strain X chromosome")
    assert not P.search("Streptomyces nystatinicus")
    assert not A.search("Streptomyces gentamicinicus")
    # real compound anchors still match
    assert P.search("filipin III complex") and P.search("natamycin")
    assert A.search("gentamicin C")


def test_tetraene_pentaene_hexaene_and_hyphen_forms():
    """v9.7.18: bare ene-count polyene subclasses + hyphenated macrolide forms match."""
    from mamey.source_scans import _POLYENE_ANCHOR as P
    for s in ["tetraene", "pentaene", "hexaene", "heptaene", "tetraene macrolide", "tetraene-macrolide"]:
        assert P.search(s), f"missed {s}"
