"""FA3 / R1 — chemical_hybrid architecture-confidence signal.

antiSMASH marks a genuinely FUSED cross-class pathway with cand_cluster /kind="chemical_hybrid"
(distinct from /kind="single" and /kind="neighbouring"). mamey previously read only kind="single"
to DEMOTE over-merged regions; it never read chemical_hybrid, the coherence signal. This adds
`count_hybrid_cand_clusters`, a `BGCRecord.has_chemical_hybrid` field, and a claim-safe capacity
note fed into `architecture_grade` (+ a guarded, sign-off-flagged B->A promotion).

Verified first-hand on AS-846 NODE_4 region001 (NRPS + T1PKS + polyhalogenated-pyrrole hybrid).

Standalone: python3 tests/test_chemical_hybrid_signal.py
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.parsers import (
    count_hybrid_cand_clusters,
    count_single_cand_clusters,
    architecture_grade,
)
from mamey.models import BGCRecord

_HYBRID_NOTE = "chemical_hybrid"


class _F:
    def __init__(self, ftype, kind=None):
        self.type = ftype
        self.qualifiers = {"kind": [kind]} if kind is not None else {}


# ---- counting ------------------------------------------------------------------

def test_counts_only_chemical_hybrid():
    feats = [_F("region"), _F("cand_cluster", "single"), _F("cand_cluster", "neighbouring"),
             _F("cand_cluster", "chemical_hybrid"), _F("protocluster"), _F("CDS"),
             _F("cand_cluster", "chemical_hybrid")]
    assert count_hybrid_cand_clusters(feats) == 2
    # the single/composite counter must be unaffected (the two signals are inverse)
    assert count_single_cand_clusters(feats) == 1


def test_missing_or_other_kind_not_counted():
    feats = [_F("cand_cluster"), _F("cand_cluster", "single"), _F("cand_cluster", "interleaved"),
             _F("protocluster", "chemical_hybrid")]  # only cand_cluster type counts
    assert count_hybrid_cand_clusters(feats) == 0


# ---- architecture_grade wiring -------------------------------------------------

def test_note_appended_when_hybrid_and_multiclass():
    products = ["NRPS", "T1PKS", "polyhalogenated-pyrrole"]  # >=2 distinct core classes
    grade, rationale = architecture_grade("Interior", products, 120000, has_chemical_hybrid=True)
    assert grade == "A"
    assert _HYBRID_NOTE in rationale
    assert "not a product/novelty/activity claim" in rationale


def test_note_requires_two_core_classes():
    # a lone-class region flagged hybrid gets NO capacity note (guarded against over-reading)
    grade, rationale = architecture_grade("Interior", ["terpene"], 120000, has_chemical_hybrid=True)
    assert _HYBRID_NOTE not in rationale


def test_additive_default_unchanged():
    # default call (no hybrid arg) must be byte-identical to the pre-FA3 behaviour
    g0, r0 = architecture_grade("Interior", ["NRPS", "T1PKS"], 120000)
    assert g0 == "A"
    assert _HYBRID_NOTE not in r0
    assert r0 == "Interior BGC with coherent biosynthetic product annotation."


def test_guarded_promotion_compact_interior():
    # a compact (<10kb) Interior core region grades B normally...
    g_plain, r_plain = architecture_grade("Interior", ["NRPS", "T1PKS"], 5000)
    assert g_plain == "B"
    # ...and is promoted to A only when antiSMASH says the classes are FUSED (chemical_hybrid)
    g_hyb, r_hyb = architecture_grade("Interior", ["NRPS", "T1PKS"], 5000, has_chemical_hybrid=True)
    assert g_hyb == "A"
    assert _HYBRID_NOTE in r_hyb


def test_truncation_grades_never_promoted():
    # the hybrid flag is orthogonal to edge/length truncation: Edge/Full-contig stay C/D
    g_edge, _ = architecture_grade("Edge", ["NRPS", "T1PKS"], 8000, has_chemical_hybrid=True)
    assert g_edge == "C"
    g_fc, _ = architecture_grade("Full-contig", ["NRPS", "T1PKS"], 8000, has_chemical_hybrid=True)
    assert g_fc == "D"


def test_bgcrecord_default_is_additive():
    b = BGCRecord(bgc_id="BGC1", contig="c", region_number=1, start=1, end=9, contig_length=99)
    assert b.has_chemical_hybrid is False


# ---- real-input confirmation (skips if AS-846.zip absent) ----------------------

_AS846 = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()) + "/Antismash/AS-846.zip"


def test_as846_node4_flagged():
    if not os.path.exists(_AS846):
        print("SKIP test_as846_node4_flagged (AS-846.zip not present)")
        return
    from mamey.parsers import parse_bgcs_from_zip
    bgcs = parse_bgcs_from_zip(_AS846, json_mode="off")
    node4 = [b for b in bgcs if "NODE_4_" in b.source_gbk]
    assert node4, "NODE_4 region not parsed"
    b = node4[0]
    assert b.has_chemical_hybrid is True
    assert _HYBRID_NOTE in b.architecture_rationale
    # at least one hybrid region in this strain (there are 6)
    assert sum(1 for x in bgcs if x.has_chemical_hybrid) >= 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
