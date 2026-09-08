"""tests/test_bgc_decomp.py — BGC two-model decomposition (v9.7.131).

K_albida BGC054 is the positive fixture:
  NRPS anchors at 0–36% window (KALB_5873, 5905, 5924, 5925)
  RiPP anchors at 86–88% window (KALB_5942, 5944, LANC_like)
  ~17 kb gap between the two groups
Expected: TWO_MODEL_STRONG, group_a=NRPS, group_b=RiPP.

K_albida PKS-NRPS hybrids (BGC039, BGC052, BGC057) must return ONE_MODEL_CONSISTENT.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest
from mamey.bgc_decomp import (
    _classify_gene, _fit_two_model, _class_coherence, two_model_flag_cell, run_bgc_decomp,
    COHERENCE_STRONG, COHERENCE_CANDIDATE, GAP_STRONG_BP, GAP_CANDIDATE_BP,
)


# ---------------------------------------------------------------------------
# Unit: gene classifier
# ---------------------------------------------------------------------------

def test_classify_pks_core_domains():
    assert _classify_gene("PKS_KS; PKS_AT") == "PKS"
    assert _classify_gene("ketoacyl-synt; Ketoacyl-synt_C") == "PKS"
    assert _classify_gene("PKS_KR; adh_short") == "PKS"      # PKS_KR is a PKS domain
    assert _classify_gene("PKSI-KR_m1; adh_short") == "PKS"

def test_classify_pks_t3():
    assert _classify_gene("Chal_sti_synt_C; Chal_sti_synt_N") == "PKS"   # T3PKS

def test_classify_nrps():
    assert _classify_gene("AMP-binding; AMP-binding_C") == "NRPS"
    assert _classify_gene("Condensation") == "NRPS"
    assert _classify_gene("NRPS-A_a3; NRPS-A_a6") == "NRPS"

def test_classify_ripp():
    assert _classify_gene("YcaO; LANC_like") == "RiPP"
    assert _classify_gene("LANC_like; Pkinase") == "RiPP"
    assert _classify_gene("Lant_dehydr") == "RiPP"

def test_classify_trp_halogenase_is_tailoring():
    # Critical: Trp_halogenase is NOT a core RiPP engine — it is a tailoring enzyme
    # in both NRPS and RiPP pathways. Must NOT be classified as RiPP.
    assert _classify_gene("Trp_halogenase") == "tailoring"

def test_classify_terpene():
    assert _classify_gene("Terpene_synth; Terpene_synth_C") == "terpene"
    assert _classify_gene("SQHop_cyclase") == "terpene"

def test_classify_tailoring():
    assert _classify_gene("p450") == "tailoring"
    assert _classify_gene("Methyltransf_21") == "tailoring"
    assert _classify_gene("FAD_binding_3") == "tailoring"
    assert _classify_gene("Aminotran_3") == "tailoring"

def test_classify_regulator():
    assert _classify_gene("TetR_N; TetR_C_16") == "regulator"
    assert _classify_gene("HTH_1; LysR_substrate") == "regulator"

def test_classify_unknown():
    assert _classify_gene("") == "unknown"
    assert _classify_gene("—") == "unknown"
    assert _classify_gene("SomeDomainNotInAnySet") == "unknown"


# ---------------------------------------------------------------------------
# Unit: two-model fitter
# ---------------------------------------------------------------------------

def _gene(lt, start, end, broad_class):
    return {"locus_tag": lt, "cds_start": start, "cds_end": end,
            "broad_class": broad_class}

def test_nrps_ripp_large_gap_strong():
    genes = [
        _gene("g1",     0,  5000, "NRPS"),
        _gene("g2",  5200,  5600, "tailoring"),
        _gene("g3",  6000, 10000, "NRPS"),
        _gene("g4", 10200, 10500, "regulator"),
        # 39.5kb gap
        _gene("g5", 50000, 55000, "RiPP"),
        _gene("g6", 55200, 55500, "tailoring"),
        _gene("g7", 56000, 60000, "RiPP"),
    ]
    r = _fit_two_model(genes)
    assert r["two_model_confidence"] == "TWO_MODEL_STRONG"
    assert r["group_a_class"] == "NRPS"
    assert r["group_b_class"] == "RiPP"
    assert r["gap_bp"] >= 39_000
    assert r["class_coherence_score"] >= COHERENCE_STRONG

def test_pks_nrps_hybrid_one_model():
    """PKS+NRPS is the canonical hybrid — one pathway, ONE_MODEL_CONSISTENT."""
    genes = [
        _gene("g1",  0, 5000, "PKS"),
        _gene("g2", 5200, 5600, "tailoring"),
        _gene("g3", 15000, 20000, "NRPS"),
    ]
    r = _fit_two_model(genes)
    assert r["two_model_confidence"] == "ONE_MODEL_CONSISTENT"
    assert "hybrid" in r.get("null_reason", "")

def test_single_class_one_model():
    genes = [
        _gene("g1",  0, 5000, "PKS"),
        _gene("g2", 5200, 8000, "tailoring"),
        _gene("g3", 20000, 25000, "PKS"),
    ]
    r = _fit_two_model(genes)
    assert r["two_model_confidence"] == "ONE_MODEL_CONSISTENT"

def test_no_anchors_one_model():
    genes = [
        _gene("g1", 0, 1000, "tailoring"),
        _gene("g2", 1100, 2000, "regulator"),
    ]
    r = _fit_two_model(genes)
    assert r["two_model_confidence"] == "ONE_MODEL_CONSISTENT"
    assert r["n_anchor_genes"] == 0

def test_small_gap_candidate_or_lower():
    """Gap 9kb is above CANDIDATE threshold but below STRONG — CANDIDATE at most."""
    genes = [
        _gene("g1",     0,  5000, "NRPS"),
        _gene("g2",  5200,  5600, "tailoring"),
        _gene("g3",  5700,  5800, "unknown"),
        _gene("g4", 14800, 19000, "RiPP"),   # gap 9kb
    ]
    r = _fit_two_model(genes)
    assert r["two_model_confidence"] in ("TWO_MODEL_CANDIDATE", "ONE_MODEL_CONSISTENT")
    assert r["two_model_confidence"] != "TWO_MODEL_STRONG"

def test_terpene_nrps_strong():
    """terpene+NRPS is mechanistically distinct — genuine two-pathway signal."""
    genes = [
        _gene("g1",     0,  5000, "terpene"),
        _gene("g2",  5200,  5500, "tailoring"),
        _gene("g3", 25000, 30000, "NRPS"),
        _gene("g4", 30200, 30500, "tailoring"),
        _gene("g5", 31000, 35000, "NRPS"),
    ]
    r = _fit_two_model(genes)
    assert r["two_model_confidence"] in ("TWO_MODEL_STRONG", "TWO_MODEL_CANDIDATE")

def test_lasso_nrps_large_gap_strong_new_class_anchor():
    """lasso is a route-defining anchor class, not merely a display label."""
    genes = [
        _gene("lasB",     0,  1200, "lasso"),
        _gene("lasE",  1600,  2600, "lasso"),
        _gene("nrps1", 30000, 34000, "NRPS"),
        _gene("nrps2", 34500, 39000, "NRPS"),
    ]
    r = _fit_two_model(genes)
    assert r["n_anchor_genes"] == 4
    assert r["two_model_confidence"] == "TWO_MODEL_STRONG"
    assert r["group_a_class"] == "lasso"
    assert r["group_b_class"] == "NRPS"


def test_phosphonate_nrps_candidate_new_class_anchor():
    """A single PEP_mutase anchor can support a candidate split when spatially separated."""
    genes = [
        _gene("pepM",     0,  1000, "phosphonate"),
        _gene("nrpsA", 20000, 25000, "NRPS"),
    ]
    r = _fit_two_model(genes)
    assert r["n_anchor_genes"] == 2
    assert r["two_model_confidence"] == "TWO_MODEL_CANDIDATE"
    assert r["group_a_class"] == "phosphonate"
    assert r["group_b_class"] == "NRPS"


def test_ripp_family_coherence_unifies_thioamide_lasso_ripp():
    """RiPP, lasso, and thioamide score as one family for binary coherence only."""
    assert _class_coherence(["thioamide", "RiPP", "lasso"], family_aware=True) == 1.0
    assert _class_coherence(["thioamide", "RiPP", "lasso"], family_aware=False) < 1.0


def test_bgc055_style_hierarchical_ripp_family_split_strong():
    """Mixed thioamide/RiPP/lasso anchors should not dilute the BGC055 binary split.

    The desired binary model is Sub-BGC A (thioamide/RiPP family) versus
    Sub-BGC B+C (lasso/RiPP-family plus NRPS), with the NRPS-dominant side
    still reported as NRPS. The shorter lasso|NRPS split is not selected merely
    because it has perfect family coherence; tier-qualified large-gap splits win.
    """
    genes = [
        _gene("ctg49_198", 212280, 213450, "thioamide"),
        _gene("ctg49_199", 214000, 215200, "RiPP"),
        _gene("ctg49_201", 217000, 218100, "thioamide"),
        _gene("ctg49_202", 219000, 220200, "RiPP"),
        _gene("ctg49_220", 251565, 252650, "lasso"),
        _gene("ctg49_221", 253000, 254000, "lasso"),
        _gene("ctg49_227", 258225, 262000, "NRPS"),
        _gene("ctg49_237", 279000, 279900, "NRPS"),
        _gene("ctg49_241", 289000, 295000, "NRPS"),
    ]
    r = _fit_two_model(genes)
    assert r["two_model_confidence"] == "TWO_MODEL_STRONG"
    assert r["group_a_class"] == "thioamide"
    assert r["group_b_class"] == "NRPS"
    assert r["group_a_anchor_genes"] == "ctg49_198; ctg49_199; ctg49_201; ctg49_202"
    assert "ctg49_220" in r["group_b_anchor_genes"]
    assert r["gap_bp"] == 31_365
    assert r["class_coherence_score"] >= COHERENCE_STRONG


# ---------------------------------------------------------------------------
# Flag cell helper
# ---------------------------------------------------------------------------

def test_flag_cell_strong_with_disconnect():
    mock = {"rows": [{
        "bgc_id": "BGC001",
        "two_model_confidence": "TWO_MODEL_STRONG",
        "group_a_class": "NRPS", "group_b_class": "RiPP",
        "gap_bp": "17048",
        "kcb_architectural_disconnect": "YES",
    }]}
    cell = two_model_flag_cell("BGC001", mock)
    assert cell.startswith("TWO_MODEL_STRONG")
    assert "NRPS+RiPP" in cell
    assert "KCB_DISCONNECT" in cell

def test_flag_cell_one_model_empty():
    mock = {"rows": [{"bgc_id": "BGC001", "two_model_confidence": "ONE_MODEL_CONSISTENT",
                      "group_a_class": "", "group_b_class": "", "gap_bp": "",
                      "kcb_architectural_disconnect": ""}]}
    assert two_model_flag_cell("BGC001", mock) == ""
    assert two_model_flag_cell("BGC_MISSING", mock) == ""
    assert two_model_flag_cell("BGC001", None) == ""


# ---------------------------------------------------------------------------
# Integration: K_albida BGC054 (requires sandbox package)
# ---------------------------------------------------------------------------

_LIVE_PKG = Path("/data/mamey-local/kalbida_run/K_albida/package")


@pytest.mark.skipif(not _LIVE_PKG.exists(), reason="K_albida package not in sandbox")
def test_kalbida_bgc054_two_model_strong():
    """BGC054: NRPS at 0-36%, RiPP (LANC_like) at 86-88%, ~17kb gap -> TWO_MODEL_STRONG."""
    gene_csv = next(_LIVE_PKG.glob("*_gene_by_gene_all_bgcs.csv"), None)
    assert gene_csv, "gene_by_gene_all_bgcs.csv not found"

    bgc054 = SimpleNamespace(
        bgc_id="BGC054", contig="CP007155.1", start=6527367, end=6629190,
        products=["HR-T2PKS", "NRPS", "RiPP", "lanthipeptide-class-iv"],
        node_id="CP007155.1", kcb_top="", closest_candidate_kcb_product="",
    )
    result = run_bgc_decomp([bgc054], gene_csv, kcb_dir=None)
    assert result["status"] == "PASS"

    row = next(r for r in result["rows"] if r["bgc_id"] == "BGC054")
    assert row["two_model_confidence"] == "TWO_MODEL_STRONG", (
        f"Expected TWO_MODEL_STRONG, got {row['two_model_confidence']}. "
        f"null_reason: {row.get('null_reason')} | "
        f"coherence: {row.get('class_coherence_score')} | gap: {row.get('gap_bp')}"
    )
    assert row["group_a_class"] == "NRPS", f"group_a was {row['group_a_class']}"
    assert row["group_b_class"] == "RiPP", f"group_b was {row['group_b_class']}"
    assert int(row["gap_bp"]) >= 15_000, f"gap was {row['gap_bp']}"


@pytest.mark.skipif(not _LIVE_PKG.exists(), reason="K_albida package not in sandbox")
def test_kalbida_pks_nrps_hybrids_one_model():
    """BGC039/052/057 are PKS-NRPS hybrids — must return ONE_MODEL_CONSISTENT."""
    gene_csv = next(_LIVE_PKG.glob("*_gene_by_gene_all_bgcs.csv"), None)
    assert gene_csv

    hybrid_bgcs = [
        SimpleNamespace(bgc_id=bid, contig="CP007155.1", start=0, end=100000,
                        products=["PKS", "NRPS"], node_id="CP007155.1",
                        kcb_top="", closest_candidate_kcb_product="")
        for bid in ["BGC039", "BGC052", "BGC057"]
    ]
    result = run_bgc_decomp(hybrid_bgcs, gene_csv)
    for row in result["rows"]:
        assert row["two_model_confidence"] == "ONE_MODEL_CONSISTENT", (
            f"{row['bgc_id']} should be ONE_MODEL_CONSISTENT, got {row['two_model_confidence']}"
        )


# ---------------------------------------------------------------------------
# v9.7.130 — new class additions
# ---------------------------------------------------------------------------

def test_classify_lasso_stand_alone_rre():
    """Stand_Alone_Lasso_RRE is the definitive lasso anchor — must classify lasso."""
    assert _classify_gene("Stand_Alone_Lasso_RRE; PqqD") == "lasso"

def test_classify_lasso_transglut():
    """Transglut_core3 is the lasso peptidase B1 catalytic domain."""
    assert _classify_gene("Transglut_core3") == "lasso"
    assert _classify_gene("Transglut_core; ABC_tran") == "lasso"

def test_classify_lasso_fused_rre():
    assert _classify_gene("Lasso_Fused_RRE") == "lasso"

def test_classify_thioamide_tfua():
    """TfuA is the thioamide-forming enzyme — unique to thioamide-RiPP."""
    assert _classify_gene("TfuA") == "thioamide"

def test_classify_thioamide_rre_domains():
    """Thiopeptide_F_RRE and Heterocycloanthracin_C_RRE mark thioamitide class.
    Priority note: when co-occurring with YcaO (as in BGC055 ctg49_201/202),
    the RiPP class fires first because PKS/NRPS/RiPP/terpene are checked before
    thioamide. This is CORRECT — those genes are the YcaO-core RiPP engines.
    The RRE-only genes (no YcaO) correctly classify as thioamide."""
    # RRE alone → thioamide
    assert _classify_gene("Thiopeptide_F_RRE") == "thioamide"
    assert _classify_gene("Heterocycloanthracin_C_RRE") == "thioamide"
    # RRE + YcaO → RiPP wins (YcaO checked first; this is intended)
    assert _classify_gene("Thiopeptide_F_RRE; YcaO") == "RiPP"

def test_classify_thioamide_tigrfams():
    assert _classify_gene("TIGR03605") == "thioamide"
    assert _classify_gene("TIGR03882") == "thioamide"

def test_classify_phosphonate_pep_mutase():
    assert _classify_gene("PEP_mutase") == "phosphonate"

def test_classify_ripp_spasm():
    """SPASM domain marks radical SAM RiPPs (ranthipeptide/sactipeptide)."""
    assert _classify_gene("Radical_SAM; SPASM") == "RiPP"

def test_classify_ripp_sactipeptide_tigrfams():
    assert _classify_gene("TIGR03975; Radical_SAM") == "RiPP"
    assert _classify_gene("TIGR03988") == "RiPP"

def test_classify_radical_sam_alone_is_unknown():
    """Radical_SAM without SPASM or RiPP TIGRFAM must NOT classify as RiPP.
    Radical SAM appears in primary metabolism, terpene tailoring, etc."""
    assert _classify_gene("Radical_SAM") == "unknown"

def test_classify_pks_er_domains():
    """PKS_ER and ECH domains (169 + 207 unknowns corrected in v9.7.130)."""
    assert _classify_gene("PKS_ER") == "PKS"
    assert _classify_gene("ECH") == "PKS"
    assert _classify_gene("ECH_1; PKS_ER") == "PKS"
    assert _classify_gene("PKSI-ER_m5") == "PKS"
    assert _classify_gene("PKSI-ER_m2; adh_short") == "PKS"

def test_classify_pks_polyketide_cyclase():
    """T2PKS aromatase/cyclase domains — uniquely PKS."""
    assert _classify_gene("Polyketide_cyc") == "PKS"
    assert _classify_gene("Polyketide_cyc2; Polyketide_cyc") == "PKS"

def test_classify_nrps_cy4():
    """Cy4 heterocyclisation domain — azole-forming NRPS. Validated BGC055 ctg49_241."""
    assert _classify_gene("AMP-binding; Cy4; NRPS-A_a2; NRPS-A_a3") == "NRPS"
    # Cy4 alone (rare but should classify NRPS)
    assert _classify_gene("Cy4") == "NRPS"

def test_classify_nrps_mbtH():
    """MbtH-like chaperone — always NRPS context."""
    assert _classify_gene("MbtH") == "NRPS"

def test_classify_nrps_te1():
    """NRPS-te1 is NRPS-specific thioesterase. Bare Thioesterase is still unknown."""
    assert _classify_gene("NRPS-te1") == "NRPS"
    assert _classify_gene("Thioesterase") == "unknown"  # ambiguous — NOT added

def test_classify_terpene_polyprenyl():
    """polyprenyl_synt, Terpene_syn_C_2, SQS_PSY added in v9.7.130."""
    assert _classify_gene("polyprenyl_synt") == "terpene"
    assert _classify_gene("Terpene_syn_C_2") == "terpene"
    assert _classify_gene("SQS_PSY") == "terpene"


# ---------------------------------------------------------------------------
# Integration: SID8375 BGC055 three-model validation
# ---------------------------------------------------------------------------
# BGC055 contains three spatially distinct biosynthetic sub-BGCs:
#   Sub-BGC A: thioamitide (TfuA + dual YcaO + Thiopeptide_RRE)  — bp 0-23,277 (offset)
#   Sub-BGC B: lassopeptide (Stand_Alone_Lasso_RRE + Transglut_core3) — bp 39,285-45,232
#   Sub-BGC C: NRPS with azole + halogenation — bp 45,945-83,397
#
# v9.7.129 two-model: correctly split A | BC (RiPP vs NRPS, gap 22.7 kb, coh 1.00)
#   but could not resolve B from C because lasso domains were 'unknown'.
# v9.7.130 target: split A | BC still STRONG; the B lasso genes now classify 'lasso'
#   which means a THREE-partition run (future work) could separate B from C.
#   For the current binary fitter: the best split is still A | BC because the
#   lasso sub-BGC (B) is only 3-5 anchor genes, and the NRPS sub-BGC (C) is 4,
#   so combined BC still dominates one side. The test verifies B's key genes
#   now classify correctly.

def test_bgc055_subA_genes_classify_thioamide_and_ripp():
    """Sub-BGC A key genes: thioamide (TfuA, RREs) and RiPP (YcaO) classes."""
    # ctg49_198 — TfuA
    assert _classify_gene("TfuA") == "thioamide"
    # ctg49_199 — YcaO / TIGR00702
    assert _classify_gene("TIGR00702; YcaO") == "RiPP"
    # ctg49_201 — Heterocycloanthracin_C_RRE; Thiopeptide_F_RRE
    assert _classify_gene("Heterocycloanthracin_C_RRE; Thiopeptide_F_RRE") == "thioamide"
    # ctg49_202 — TIGR03604; TIGR03882; YcaO
    assert _classify_gene("TIGR03604; TIGR03882; YcaO") == "RiPP"  # YcaO fires first

def test_bgc055_subB_genes_classify_lasso():
    """Sub-BGC B key genes: lasso class. This is the v9.7.130 regression fix."""
    # ctg49_221 — PqqD; Stand_Alone_Lasso_RRE (the definitive lasso anchor)
    assert _classify_gene("PqqD; Stand_Alone_Lasso_RRE") == "lasso"
    # ctg49_220 — Transglut_core3 (lasso peptidase)
    assert _classify_gene("Transglut_core3") == "lasso"
    # ctg49_222 — Asn_synthase (cyclase — intentionally NOT added, too ambiguous)
    assert _classify_gene("Asn_synthase") == "unknown"

def test_bgc055_subC_genes_classify_nrps():
    """Sub-BGC C key genes: NRPS (including Cy4 heterocyclisation)."""
    # ctg49_227 — AMP-binding; AMP-binding_C; C1_DCL_004-017
    assert _classify_gene("AMP-binding; AMP-binding_C") == "NRPS"
    # ctg49_241 — AMP-binding; Cy4; NRPS-A_a2; NRPS-A_a3 (heterocyclisation module)
    assert _classify_gene("AMP-binding; Cy4; NRPS-A_a2; NRPS-A_a3") == "NRPS"
    # ctg49_237 — MbtH (chaperone, now NRPS)
    assert _classify_gene("MbtH") == "NRPS"
    # ctg49_244 — Trp_halogenase (confirmed tailoring, NOT NRPS)
    assert _classify_gene("Trp_halogenase") == "tailoring"



def test_new_classes_are_two_model_anchors():
    """lasso/thioamide/phosphonate are route-defining anchors, not labels only."""
    genes = [
        _gene("las1",     0,  1000, "lasso"),
        _gene("las2",  1200,  2200, "lasso"),
        _gene("tail",  2300,  3000, "tailoring"),
        _gene("nrp1", 26000, 30000, "NRPS"),
        _gene("nrp2", 30500, 34000, "NRPS"),
    ]
    r = _fit_two_model(genes)
    assert r["n_anchor_genes"] == 4
    assert r["two_model_confidence"] == "TWO_MODEL_STRONG"
    assert r["group_a_class"] == "lasso"
    assert r["group_b_class"] == "NRPS"


def test_bgc055_ripp_family_coherence_large_gap_split_strong():
    """BGC055-style mixed thioamide/RiPP/lasso + NRPS stays STRONG.

    Exact-label scoring made this only CANDIDATE after lasso became an anchor.
    Family-level coherence scores thioamide/RiPP/lasso as one RiPP-family bucket
    for binary partitioning, while preserving exact labels in group_a/b_class.
    Gap-first selection within a tier keeps the large A|BC boundary instead of
    choosing a shorter internal NRPS-side split.
    """
    genes = [
        _gene("ctg49_198", 212280, 213450, "thioamide"),
        _gene("ctg49_199", 214000, 215200, "RiPP"),
        _gene("ctg49_201", 217000, 218100, "thioamide"),
        _gene("ctg49_202", 219000, 220200, "RiPP"),
        _gene("ctg49_220", 251565, 252650, "lasso"),
        _gene("ctg49_221", 253000, 254000, "lasso"),
        _gene("ctg49_222", 254500, 255800, "unknown"),
        _gene("ctg49_227", 258225, 262000, "NRPS"),
        _gene("ctg49_237", 279000, 279900, "NRPS"),
        _gene("ctg49_241", 289000, 295000, "NRPS"),
        _gene("ctg49_244", 300000, 301000, "tailoring"),
    ]
    r = _fit_two_model(genes)
    assert r["n_anchor_genes"] == 9
    assert r["two_model_confidence"] == "TWO_MODEL_STRONG"
    assert r["group_a_class"] == "thioamide"
    assert r["group_a_anchor_genes"] == "ctg49_198; ctg49_199; ctg49_201; ctg49_202"
    assert r["group_b_class"] == "NRPS"
    assert r["group_b_anchor_genes"].startswith("ctg49_220; ctg49_221; ctg49_227")
    assert r["gap_bp"] == 31365
    assert r["class_coherence_score"] >= COHERENCE_STRONG

_SID8375_BGC055_PKG = Path("/data/mamey-local/intake/runs/SID8375/package")


@pytest.mark.skipif(
    not _SID8375_BGC055_PKG.exists(),
    reason="SID8375 package not in sandbox",
)
def test_sid8375_bgc055_two_model_strong():
    """Live integration: BGC055 must still score TWO_MODEL_STRONG after v9.7.130 changes.
    Expected split: thioamide/RiPP group (Sub-BGC A) vs NRPS group (Sub-BGC C).
    The lasso Sub-BGC B now contributes lasso-class anchors to the BC side,
    and RiPP-family coherence should still preserve a clean A | BC split."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from mamey.bgc_decomp import run_bgc_decomp
    from types import SimpleNamespace

    gene_csv = next(_SID8375_BGC055_PKG.glob("*_gene_by_gene_all_bgcs.csv"), None)
    assert gene_csv, "gene_by_gene_all_bgcs.csv not found for SID8375"

    bgc055 = SimpleNamespace(
        bgc_id="BGC055", contig="WWGG01000053.1",
        start=212280, end=310260,
        products=["NRPS", "RiPP", "azole-containing-RiPP", "halogenated",
                  "lassopeptide", "thioamitides"],
        node_id="WWGG01000053.1",
        kcb_top="BGC0002053.3 | ulleungdin",
        closest_candidate_kcb_product="ulleungdin",
    )
    result = run_bgc_decomp([bgc055], gene_csv, kcb_dir=None)
    assert result["status"] == "PASS"
    row = next(r for r in result["rows"] if r["bgc_id"] == "BGC055")

    assert row["two_model_confidence"] == "TWO_MODEL_STRONG", (
        f"Expected TWO_MODEL_STRONG, got {row['two_model_confidence']}. "
        f"coherence={row.get('class_coherence_score')} gap={row.get('gap_bp')} "
        f"null_reason={row.get('null_reason')}"
    )
    # Group A should be thioamide/RiPP side; Group B should be NRPS
    assert row["group_b_class"] == "NRPS", f"group_b was {row['group_b_class']}"
    assert int(row["gap_bp"]) >= 15_000, f"gap was {row['gap_bp']}"

