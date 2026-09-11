"""Engine-side regression tests for the fragment claim-ceiling (P4). pytest -q"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from mamey.fragment_ceiling import fragment_claim_ceiling, apply_to_bgc, DOWNGRADE_CEILING

# --- pure-function fixtures from the 4 cohort over-calls + NZ_QHHY ---
def test_teicoplanin_fragment_trips():
    dg,_ = fragment_claim_ceiling("Teicoplanin A2-1", "Edge", 15.9); assert dg
def test_uk68597_fragment_trips():
    dg,_ = fragment_claim_ceiling("UK-68,597", "Edge", 31.1); assert dg
def test_friulimicin_fragment_trips():
    dg,_ = fragment_claim_ceiling("friulimicin A/friulimicin B", "Edge", 32.1); assert dg
def test_nystatin_fragment_trips():
    dg,_ = fragment_claim_ceiling("nystatin A1", "Edge", 28.4); assert dg
def test_enduracidin_fragment_trips():   # NZ_QHHY BGC028 from Batch-2 audit
    dg,_ = fragment_claim_ceiling("enduracidin A/enduracidin B", "Edge", 38.0); assert dg

# --- negative controls ---
def test_interior_lanthipeptide_safe():
    dg,_ = fragment_claim_ceiling("microbisporicin A2", "Interior", 25.0); assert not dg
def test_interior_glycopeptide_safe():
    dg,_ = fragment_claim_ceiling("UK-68,597", "Interior", 60.0); assert not dg
def test_fullsize_edge_glycopeptide_safe():
    dg,_ = fragment_claim_ceiling("teicoplanin", "Edge", 70.0); assert not dg
def test_siderophore_fragment_safe():
    dg,_ = fragment_claim_ceiling("coelichelin", "Edge", 20.0); assert not dg
def test_empty_product_safe():
    dg,_ = fragment_claim_ceiling("", "Edge", 10.0); assert not dg

# --- apply_to_bgc mutation behavior ---
class _FakeBGC:
    def __init__(self, **k):
        self.closest_candidate_kcb_product = k.get("product","")
        self.edge_status = k.get("edge","Full-contig")
        self.start = k.get("start",0); self.end = k.get("end",0)
        self.product_claim_ceiling = "candidate product-level similarity, manual check required"
        self.needs_manual_kcb_check = "no"; self.notes = ""
    def length_kb(self): return round((self.end-self.start)/1000,2)

def test_apply_downgrades_ceiling_and_flags():
    b = _FakeBGC(product="Teicoplanin A2-1", edge="Edge", start=0, end=15900)
    reason = apply_to_bgc(b)
    assert reason is not None
    assert b.product_claim_ceiling == DOWNGRADE_CEILING
    assert b.needs_manual_kcb_check == "yes"
    assert "FRAGMENT_CEILING" in b.notes

def test_apply_leaves_interior_untouched():
    b = _FakeBGC(product="microbisporicin A2", edge="Interior", start=0, end=25000)
    before = b.product_claim_ceiling
    reason = apply_to_bgc(b)
    assert reason is None and b.product_claim_ceiling == before

def test_apply_handles_list_notes():
    """Real BGCRecord.notes is a list — apply_to_bgc must append, not concatenate-as-str."""
    class _ListNotesBGC:
        closest_candidate_kcb_product = "Teicoplanin A2-1"
        edge_status = "Edge"; start = 0; end = 15900
        product_claim_ceiling = "candidate"; needs_manual_kcb_check = "no"
        notes = []
        def length_kb(self): return 15.9
    b = _ListNotesBGC()
    apply_to_bgc(b)
    assert isinstance(b.notes, list) and any("FRAGMENT_CEILING" in n for n in b.notes)


def test_kcb_top_fallback_source_derived_path():
    """P4 must also fire when the product name is only in kcb_top (source-derived path),
    where closest_candidate_kcb_product stays 'UNRESOLVED'."""
    class B:
        closest_candidate_kcb_product = "UNRESOLVED"
        kcb_top = "BGC0000440.5 | teicoplanin a2-1 | knownclusterblast #1"
        edge_status = "Edge"; length_kb = 15.9
        needs_manual_kcb_check = "no"; product_claim_ceiling = "source-derived similarity anchor only"
        notes = []
    b = B(); reason = apply_to_bgc(b)
    assert reason is not None
    assert b.product_claim_ceiling == DOWNGRADE_CEILING
    assert b.needs_manual_kcb_check == "yes"

def test_reviewed_gap_keywords_trip():
    # stambomycin (51-membered macrolactone) was a keyword-set GAP found in the 32-strain review
    dg,_ = fragment_claim_ceiling("BGC0000151.5 | stambomycin A | knownclusterblast #1", "Edge", 30.0)
    assert dg
def test_cda_anchored_no_substring_overtrip():
    # bare 'cda' removed; an unrelated name containing 'cda' must NOT trip
    dg,_ = fragment_claim_ceiling("some-cdaXYZ-metabolite", "Edge", 10.0)
    assert not dg


# ---- size-ratio path (v9.7.28): use the matched reference's real size, not just keywords ----
def test_size_ratio_trips_non_keyword_large_reference():
    # a product NOT in LARGE_BACKBONE_KEYWORDS still trips when its matched reference is large
    dg, why = fragment_claim_ceiling("novel-unlisted-macrolactam", "Edge", 28.0, reference_size_kb=130.0)
    assert dg and "reference-size path" in why

def test_size_ratio_conservative_above_floor():
    # a substantial fragment (>= floor) never trips, even against a large reference
    dg, _ = fragment_claim_ceiling("novel-unlisted-macrolactam", "Edge", 60.0, reference_size_kb=130.0)
    assert not dg

def test_size_ratio_small_reference_does_not_trip():
    # reference itself below the floor -> not a large backbone -> never trips
    dg, _ = fragment_claim_ceiling("small-thing", "Edge", 10.0, reference_size_kb=20.0)
    assert not dg

def test_size_ratio_interior_never_trips():
    dg, _ = fragment_claim_ceiling("teicoplanin", "Interior", 20.0, reference_size_kb=90.0)
    assert not dg

def test_reference_size_lookup_real_accessions():
    # v9.7.362: sizes come from the MIBiG reference index, which is now user-provisioned
    # (CC BY 4.0, not redistributed). Skip where it is absent; the keyword-fallback path below
    # is the back-compat guarantee and still runs unconditionally.
    import pytest as _pt, sys as _sys, pathlib as _pl
    _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
    from mamey import external_data as _xd
    if _xd.resolve("mibig") is None:
        _pt.skip("MIBiG not provisioned (see docs/EXTERNAL_DATA.md)")
    from mamey.fragment_ceiling import reference_size_kb_for
    assert reference_size_kb_for("BGC0000440") and reference_size_kb_for("BGC0000440") > 80   # teicoplanin ~89.7
    assert reference_size_kb_for("BGC0000440.5") == reference_size_kb_for("BGC0000440")        # version-tolerant

def test_keyword_fallback_when_no_reference_size():
    # with no reference size, the curated keyword path still protects (back-compat)
    dg, _ = fragment_claim_ceiling("teicoplanin a2-1", "Edge", 15.9, reference_size_kb=None)
    assert dg
