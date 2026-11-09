"""The enediyne mis-anchor guard removes only the enediyne novelty credit that was banked."""
from types import SimpleNamespace

from mamey.models import BGCRecord
from mamey.scoring import triage_bgcs


def _novelty(products, misanchor):
    bgc = BGCRecord(bgc_id="BGC001", contig="c1", region_number=1, start=1, end=9000, contig_length=50000,
                    products=list(products), edge_status="Interior", architecture_confidence="A",
                    closest_candidate_kcb_product="calicheamicin", ene_ks_count=0)
    guard = {"enediyne_misanchor": True, "enediyne_verdict": "ENEDIYNE_MISANCHOR"} if misanchor else {}
    scans = SimpleNamespace(primary_metabolism={"per_bgc": {}}, cctt={"per_bgc": {}},
                            resistance_tiers={"per_bgc": {}}, misanchor_guards={"per_bgc": {"BGC001": guard}})
    return triage_bgcs([bgc], None, scans)[0].novelty_score


def test_no_enediyne_product_means_nothing_to_strip():
    # Products never named enediyne, so no +18 was banked; the guard must not subtract it.
    assert _novelty(["other"], misanchor=True) == _novelty(["other"], misanchor=False)


def test_enediyne_product_credit_is_stripped():
    assert _novelty(["enediyne"], misanchor=True) == _novelty(["enediyne"], misanchor=False) - 18
