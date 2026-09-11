"""CLAUDE_AUG3_07 guard — composite protocluster-split de-inflation invariant.

Locks the two properties a future edit must never silently break:

  1. MAX-not-SUM: a composite region (protocluster_count >= 2, non-hybrid, >=2 distinct
     protocluster products) scores its base AB/AF/novelty from the STRONGEST single
     protocluster, not from the UNION of all co-captured classes. So turning the gate on
     lowers the base by exactly (union_score - max_over_protocluster).

  2. HYBRID UNTOUCHED: a genuine chemical_hybrid region (has_chemical_hybrid=True) is
     EXCLUDED from de-inflation even at protocluster_count >= 2 — its union text is
     preserved (never split a fused single-compound pathway).

Design: assert RELATIONAL deltas between a record and its gate-off twin (identical in every
field except the one attribute that flips the gate), so the test is immune to any uniform
downstream scoring offset — it isolates exactly the de-inflation contribution.

Products NRPS;PKS;T1PKS are a verified inflating case on this engine's keyword tables:
  AB  max=12 union=22 (delta 10) · AF max=10 union=18 (delta 8) · NOV max=8 union=16 (delta 8)

Standalone: python3 tests/test_composite_deinflation_gate.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.models import BGCRecord
from mamey.scoring import (
    triage_bgcs, score_keywords, AB_KEYWORDS, AF_KEYWORDS, NOVELTY_KEYWORDS,
)

_PRODUCTS = ["NRPS", "PKS", "T1PKS"]          # union inflates over the strongest single
_BREAKDOWN = [{"product": "NRPS"}, {"product": "T1PKS"}]   # 2 distinct single protoclusters
_UNION_TXT = "nrps;pks;t1pks"


def _expected_deltas():
    """(union - max) per channel = the amount de-inflation must remove."""
    d = {}
    for name, KW in (("ab", AB_KEYWORDS), ("af", AF_KEYWORDS), ("nov", NOVELTY_KEYWORDS)):
        per = [score_keywords(p.lower(), KW) for p in ("NRPS", "T1PKS")]
        d[name] = score_keywords(_UNION_TXT, KW) - max(per)
    return d


def _bgc(bid, *, protocluster_count, has_chemical_hybrid, breakdown=None, products=None):
    b = BGCRecord(bgc_id=bid, contig="ctg1", region_number=1, start=0, end=120000,
                  contig_length=120000, products=list(products or _PRODUCTS),
                  edge_status="Interior", architecture_confidence="D")
    b.protocluster_count = protocluster_count
    b.has_chemical_hybrid = has_chemical_hybrid
    b.protocluster_breakdown = list(breakdown if breakdown is not None else _BREAKDOWN)
    return b


def _score(b):
    t = triage_bgcs([b])[0]
    return {"ab": t.ab_score, "af": t.af_score, "nov": t.novelty_score, "tier": t.lead_tier}


# ---- 1. MAX-not-SUM: gate ON lowers base by exactly (union - max) --------------------

def test_composite_deinflates_by_union_minus_max():
    on = _score(_bgc("ON", protocluster_count=2, has_chemical_hybrid=False))    # gate fires
    off = _score(_bgc("OFF", protocluster_count=1, has_chemical_hybrid=False))  # union path
    d = _expected_deltas()
    assert d["ab"] > 0 and d["af"] > 0 and d["nov"] > 0, "fixture must be an inflating case"
    assert off["ab"] - on["ab"] == d["ab"], (off["ab"], on["ab"], d["ab"])
    assert off["af"] - on["af"] == d["af"], (off["af"], on["af"], d["af"])
    assert off["nov"] - on["nov"] == d["nov"], (off["nov"], on["nov"], d["nov"])
    # strictly de-inflating: never an increase
    assert on["ab"] < off["ab"] and on["af"] < off["af"] and on["nov"] < off["nov"]


# ---- 2. HYBRID UNTOUCHED: chemical_hybrid is excluded even at pc>=2 ------------------

def test_chemical_hybrid_not_deinflated():
    hyb_on = _score(_bgc("HY2", protocluster_count=2, has_chemical_hybrid=True))
    hyb_off = _score(_bgc("HY1", protocluster_count=1, has_chemical_hybrid=True))
    # identical hybrid flag on both -> any architecture effect cancels; the ONLY difference
    # would be de-inflation, which must NOT fire for a hybrid. So scores are equal.
    assert hyb_on["ab"] == hyb_off["ab"]
    assert hyb_on["af"] == hyb_off["af"]
    assert hyb_on["nov"] == hyb_off["nov"]


# ---- 3. GATE PREDICATE: needs >=2 DISTINCT protocluster products ---------------------

def test_single_distinct_product_not_deinflated():
    # pc>=2 but the breakdown has only one distinct product -> union path (no de-inflation)
    same = [{"product": "NRPS"}, {"product": "NRPS"}]
    on = _score(_bgc("SD2", protocluster_count=2, has_chemical_hybrid=False, breakdown=same))
    off = _score(_bgc("SD1", protocluster_count=1, has_chemical_hybrid=False, breakdown=same))
    assert on["ab"] == off["ab"] and on["af"] == off["af"] and on["nov"] == off["nov"]


def test_empty_breakdown_not_deinflated():
    on = _score(_bgc("EB2", protocluster_count=2, has_chemical_hybrid=False, breakdown=[]))
    off = _score(_bgc("EB1", protocluster_count=1, has_chemical_hybrid=False, breakdown=[]))
    assert on["ab"] == off["ab"] and on["af"] == off["af"] and on["nov"] == off["nov"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
