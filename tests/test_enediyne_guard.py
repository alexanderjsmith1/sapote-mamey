"""§4.3 PREV-001 enediyne guard (ene_KS-gated).

A GENUINE enediyne ([E-signal]) requires BOTH a named-enediyne KCB anchor AND the ene_KS warhead PKS
domain (antiSMASH PKS_KS(Enediyne-KS)). A named anchor WITHOUT ene_KS is similarity-only -> ENEDIYNE_MISANCHOR
(KCB = similarity, not identity; mirrors §4.2's PKS_KS requirement). Generic enediyne + hglE -> PREV001_ARTIFACT.
Both mis-anchor verdicts strip the spurious +18 enediyne novelty. No BSL-2 lab-safety flag is ever emitted.

Regression: BGC015 (calicheamicin, ene_KS=0) + BGC042 (neocarzinostatin, ene_KS=0) -> MISANCHOR;
BGC009/BGC033 (named + ene_KS>0) -> GENUINE.

Standalone: python3 tests/test_enediyne_guard.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.models import BGCRecord
from mamey.source_scans import scan_misanchor_guards
from mamey.scoring import triage_bgcs


def _bgc(bgc_id, products, anchor="", ene_ks=0):
    return BGCRecord(bgc_id=bgc_id, contig="c1", region_number=1, start=1, end=9000, contig_length=50000,
                     products=list(products), edge_status="Interior", architecture_confidence="A",
                     closest_candidate_kcb_product=anchor, ene_ks_count=ene_ks)


def test_genuine_requires_named_anchor_and_ene_ks():
    per = scan_misanchor_guards([], [_bgc("BGC033", ["T1PKS", "enediyne"], anchor="dynemicin", ene_ks=2)])["per_bgc"]
    assert per["BGC033"]["enediyne_verdict"] == "GENUINE_E_SIGNAL"
    assert per["BGC033"]["esignal_enediyne"] and not per["BGC033"]["enediyne_misanchor"]


def test_named_anchor_without_ene_ks_is_misanchor():
    """The v9.7.16 bug: BGC015 calicheamicin / BGC042 neocarzinostatin with ene_KS=0 -> MISANCHOR (no enediyne novelty credit)."""
    per = scan_misanchor_guards([], [_bgc("BGC015", ["PKS", "NRPS"], anchor="calicheamicin", ene_ks=0),
                                     _bgc("BGC042", ["NRPS"], anchor="neocarzinostatin", ene_ks=0)])["per_bgc"]
    for bid in ("BGC015", "BGC042"):
        assert per[bid]["enediyne_verdict"] == "ENEDIYNE_MISANCHOR"
        assert per[bid]["enediyne_misanchor"] and not per[bid]["esignal_enediyne"]


def test_prev001_artifact_generic_enediyne_with_hgle():
    per = scan_misanchor_guards([], [_bgc("BGC060", ["enediyne", "hglE-KS"], anchor="hexacosalactone enediyne-like")])["per_bgc"]
    assert per["BGC060"]["enediyne_verdict"] == "PREV001_ARTIFACT"
    assert per["BGC060"]["enediyne_misanchor"] and not per["BGC060"]["esignal_enediyne"]


def test_generic_enediyne_no_hgle_unresolved():
    per = scan_misanchor_guards([], [_bgc("BGCx", ["enediyne"], anchor="enediyne-like cluster")])["per_bgc"]
    assert per["BGCx"]["enediyne_verdict"] == "E_SIGNAL_UNRESOLVED"


def test_misanchor_strips_novelty_and_no_bsl2():
    bgcs = [_bgc("BGC015", ["PKS"], anchor="calicheamicin", ene_ks=0)]
    scans = SimpleNamespace(primary_metabolism={"per_bgc": {}}, cctt={"per_bgc": {}},
                            resistance_tiers={"per_bgc": {}},
                            misanchor_guards={"per_bgc": {"BGC015": {"enediyne_misanchor": True,
                                                                     "enediyne_verdict": "ENEDIYNE_MISANCHOR"}}})
    r = {x.bgc_id: x for x in triage_bgcs(bgcs, None, scans)}["BGC015"]
    assert "similarity_only" in r.misanchor_flag and "BSL-2" not in r.rationale


def test_genuine_gets_esignal_note_no_bsl2():
    bgcs = [_bgc("BGC033", ["T1PKS", "enediyne"], anchor="dynemicin", ene_ks=2)]
    scans = SimpleNamespace(primary_metabolism={"per_bgc": {}}, cctt={"per_bgc": {}},
                            resistance_tiers={"per_bgc": {}},
                            misanchor_guards={"per_bgc": {"BGC033": {"esignal_enediyne": True}}})
    r = {x.bgc_id: x for x in triage_bgcs(bgcs, None, scans)}["BGC033"]
    # R-B: a genuine enediyne carries the [E-signal] claim-safety note but NO BSL-2 lab-safety warning
    assert "[E-signal]" in r.rationale and "enediyne candidate" in r.rationale
    assert "BSL-2" not in r.rationale and "BSL-2" not in r.misanchor_flag
    assert "E-signal" in r.misanchor_flag


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
