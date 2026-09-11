"""Regression tests for the four schema-stability patches. Run: pytest test_patches.py -q"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from mamey.dedup_and_guard import dedup_b1_rows, derive_release, leak_audit, fragment_claim_ceiling
from mamey.b1_normalizer import normalize_table, _norm_products, _norm_boundary, _norm_region

CANON = ['strain','BGC_ID','contig','region','start','end','length_kb','products','boundary','arch',
'kcb_top','kcb_score','kcb_proteins','cctt_triggers','resistance_tier','tta_tier','ab_auto','af_auto',
'novelty_auto','lead_tier_auto','depth_floor','closest_product_provenance','source_kcb_file',
'source_kcb_locator','kcb_hit_rank','denominator_type','parse_confidence','needs_manual_kcb_check',
'product_claim_ceiling','efls_status','flank_census_tier1','flank_census_tier2_todo',
'cross_contig_candidate_set','efls_claim_ceiling','dkp_rank','dkp_cdps_evidence','dkp_oxidase_homology',
'dkp_provenance','dkp_claim_ceiling','diagnostic_signal_score','evidence_weight_tier','claim_confidence',
'claim_ceiling','safe_claim']

# ---- (A) dedup-on-ingest ----
def test_dedup_removes_exact_duplicates():
    rows = [{"strain":"X","BGC_ID":"BGC001"},{"strain":"X","BGC_ID":"BGC002"},
            {"strain":"X","BGC_ID":"BGC001"}]  # dup
    out, rep = dedup_b1_rows(rows)
    assert rep["removed"] == 1 and len(out) == 2

def test_dedup_is_idempotent():
    rows = [{"strain":"X","BGC_ID":"BGC001"}]*5
    out, _ = dedup_b1_rows(rows)
    out2, rep2 = dedup_b1_rows(out)
    assert len(out)==1 and rep2["removed"]==0

def test_dedup_last_wins():
    rows = [{"strain":"X","BGC_ID":"BGC001","v":"old"},{"strain":"X","BGC_ID":"BGC001","v":"new"}]
    out,_ = dedup_b1_rows(rows, policy="last")
    assert out[0]["v"]=="new"

# ---- (B) release guard ----
def test_release_as_private():     assert derive_release("AS-XXX")=="PRIVATE"
def test_release_ajs_private():    assert derive_release("AJS-XXX")=="PRIVATE"
def test_release_pending_private():assert derive_release("PENDING-XXX")=="PRIVATE"
def test_release_sid_public():     assert derive_release("SID"+"3212")=="PUBLIC"  # split literal: survives clean-tier SID anonymization
def test_release_unknown_failsafe_private(): assert derive_release("WWXY00000000")=="PRIVATE"
def test_release_registry_override():
    assert derive_release("WeirdName", private_registry={"WeirdName"})=="PRIVATE"

def test_leak_audit_catches_pending_in_public():
    rows=[{"strain":"S","BGC_ID":"B1","release":"PUBLIC","notes":"derived from PENDING-XXX"}]
    assert len(leak_audit(rows))==1

def test_leak_audit_clean_when_private_tagged():
    rows=[{"strain":"PENDING-XXX","BGC_ID":"B1","release":"PRIVATE","notes":"x"}]
    assert leak_audit(rows)==[]

# ---- (C) fragment claim-ceiling ----
def test_ceiling_trips_on_small_glycopeptide_fragment():
    dg,ceil,_ = fragment_claim_ceiling({"closest_candidate_kcb_product":"Teicoplanin A2-1",
                                        "edge_status":"Edge","start":0,"end":15900})
    assert dg and ceil=="class_capacity_only"

def test_ceiling_ignores_interior_cluster():
    dg,_,_ = fragment_claim_ceiling({"closest_candidate_kcb_product":"UK-68,597",
                                     "edge_status":"Interior","start":0,"end":60000})
    assert not dg

def test_ceiling_ignores_small_non_backbone():
    dg,_,_ = fragment_claim_ceiling({"closest_candidate_kcb_product":"microbisporicin A2",
                                     "edge_status":"Edge","start":0,"end":20000})
    assert not dg  # microbisporicin not in large-backbone list

# ---- (D) normalizer ----
def test_normalizer_maps_divergent_names():
    src=[{"strain":"X","BGC_ID":"B1","Contig":"c1","Edge_Status":"interior","Products":"NRPS/PKS","Region":3}]
    out,ledger = normalize_table(src, CANON)
    assert out[0]["contig"]=="c1"
    assert out[0]["boundary"]=="Interior"
    assert out[0]["products"]=="NRPS;PKS"
    assert out[0]["region"]=="region003"

def test_normalizer_routes_taxonomy_to_a2():
    src=[{"strain":"X","BGC_ID":"B1","taxonomy":"Streptomyces sp."}]
    _,ledger = normalize_table(src, CANON)
    assert "taxonomy" in ledger["route_to_A2"]

def test_normalizer_needs_manual_default():
    src=[{"strain":"X","BGC_ID":"B1","KCB_Top_Hit":"BGC0000440"}]
    out,_ = normalize_table(src, CANON)
    assert out[0]["needs_manual_kcb_check"]=="yes"

def test_normalizer_honest_blanks():
    src=[{"strain":"X","BGC_ID":"B1"}]  # minimal
    out,_ = normalize_table(src, CANON)
    assert out[0]["start"]=="" and out[0]["arch"]==""  # honest blanks, not fabricated

def test_value_normalizers():
    assert _norm_products("a/b/c")=="a;b;c"
    assert _norm_boundary("edge")=="Edge"
    assert _norm_region("5")=="region005"
