"""BLACK_CHERRY_377 regression: `_logic_proof`'s complementary_disjoint_refs (cdr) fallback must not
grant the biosynthetic-logic-complementarity proof when the SAME rggmci.py subject-tiling
accumulator that produced cdr also shows a contradicting pile of overlapping_subject_refs.

Real-cohort grounding (.368 sealed AS-348_4A_RGGMCI_ranked_pairs.csv, pair BGC014+BGC033,
NODE_19/NODE_74): rggmci_confidence=HIGH_RG_GMCI_RESCUE, functional_rescue_class=AMBIGUOUS,
complementary_disjoint_refs=6, overlapping_subject_refs=22, rggmci.py's own subject_tiling_verdict
= MIXED_SUBJECT_SIGNAL (never COMPLEMENTARY_SPLIT -- rggmci.py's Phase 4 gate, `cd >= 1 and ov >= 1`,
demotes exactly this shape to MIXED, on purpose). The unfixed `_logic_proof` ignored
overlapping_subject_refs entirely and returned True from the raw cdr>=3 count alone, and the real
sealed AS-348_4D_two_proof_rescue.csv row for this pair reads
`RGGMCI_ONLY,logic-only rescue (no shared KS clade)` -- a live false biosynthetic-logic-
complementarity claim over a pair whose own evidence is 22:6 paralogy-dominant.

No shipped data: the fixtures below use the real AS-348 cd/ov counts (public, already-derived
summary numbers, not sequence/strain-identifying content) with synthetic contig/BGC tokens.
"""
import csv
import os

from mamey.rescue_two_proof import _logic_proof, two_proof_join


def _scan(clades):
    return {"cross_contig_clades": clades}


def _write_4a(path, rows):
    cols = ["contig_a", "contig_b", "rggmci_confidence", "rggmci_score",
            "functional_rescue_class", "complementary_disjoint_refs", "overlapping_subject_refs",
            "subject_tiling_verdict", "bgc_a", "bgc_b"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    return path


def test_cdr_fallback_blocked_when_overlapping_subjects_also_present():
    # Real AS-348 BGC014+BGC033 shape: cd=6 (clears the old cdr>=3 bar) but ov=22 -- rggmci.py's
    # own Phase 4 gate calls this MIXED_SUBJECT_SIGNAL, not a clean split. The fallback must not
    # grant the logic proof from contradicted evidence.
    row = {"rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "functional_rescue_class": "AMBIGUOUS",
           "complementary_disjoint_refs": "6", "overlapping_subject_refs": "22"}
    assert not _logic_proof(row)


def test_cdr_fallback_still_fires_when_clean_no_overlap():
    # Backward-compat pin: cd>=3 with genuinely ZERO overlapping evidence (the shape
    # test_rescue_two_proof.py::test_logic_proof_gate already exercises, where
    # overlapping_subject_refs is simply absent from the row) still passes.
    row = {"rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "functional_rescue_class": "BOTH_CORE",
           "complementary_disjoint_refs": "3"}
    assert _logic_proof(row)
    row_explicit_zero = {"rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "functional_rescue_class": "BOTH_CORE",
                          "complementary_disjoint_refs": "3", "overlapping_subject_refs": "0"}
    assert _logic_proof(row_explicit_zero)


def test_cdr_fallback_blocked_by_even_one_overlapping_ref():
    # A single contradicting overlapping reference is enough to withhold the fallback -- matches
    # rggmci.py's own `cd >= 1 and ov >= 1 -> MIXED_SUBJECT_SIGNAL` boundary (any ov disqualifies).
    row = {"rggmci_confidence": "MODERATE_RG_GMCI_CANDIDATE", "functional_rescue_class": "AMBIGUOUS",
           "complementary_disjoint_refs": "5", "overlapping_subject_refs": "1"}
    assert not _logic_proof(row)


def test_complementary_frc_proof_is_unaffected_by_overlapping_subjects():
    # functional_rescue_class == COMPLEMENTARY is an INDEPENDENT proof (clusterblast_genes.py
    # core/tailoring gene-content profiling, a different data source from rggmci.py's subject-
    # tiling counts) -- it must still pass on its own even when the subject-tiling axis is mixed.
    row = {"rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "functional_rescue_class": "COMPLEMENTARY",
           "complementary_disjoint_refs": "0", "overlapping_subject_refs": "22"}
    assert _logic_proof(row)


def test_end_to_end_mixed_signal_pair_is_hold_not_rescue(tmp_path):
    # Real AS-348 BGC014+BGC033 shape end-to-end through two_proof_join: KS-clade present (so this
    # isn't the "no KS at all" WEAK case) but the fallback is properly blocked -> MULTI_CHANNEL_HOLD
    # (advisory, complementarity still owed), never TWO_PROOF_RESCUE or RGGMCI_ONLY.
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_19", "contig_b": "NODE_74", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "AMBIGUOUS", "complementary_disjoint_refs": "6",
         "overlapping_subject_refs": "22", "subject_tiling_verdict": "MIXED_SUBJECT_SIGNAL"},
    ])
    scan = _scan([{"clade_id": "KSC01", "contigs": ["NODE_19", "NODE_74"]}])
    rows, summary, counts = two_proof_join(a4, scan)
    verds = {(r["contig_a"], r["contig_b"]): r["verdict"] for r in rows}
    assert verds[("NODE_19", "NODE_74")] == "MULTI_CHANNEL_HOLD"
    assert counts["TWO_PROOF_RESCUE"] == 0


def test_end_to_end_mixed_signal_pair_without_ks_is_weak(tmp_path):
    # Same contradicted-evidence pair, but no KS-clade co-membership at all: before the fix this
    # was the real sealed AS-348 shape (RGGMCI_ONLY, "logic-only rescue (no shared KS clade)" --
    # a live false complementarity claim). After the fix it correctly falls all the way to WEAK
    # (neither proof clears its bar), not RGGMCI_ONLY.
    a4 = _write_4a(os.path.join(tmp_path, "X_4A.csv"), [
        {"contig_a": "NODE_19", "contig_b": "NODE_74", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "functional_rescue_class": "AMBIGUOUS", "complementary_disjoint_refs": "6",
         "overlapping_subject_refs": "22", "subject_tiling_verdict": "MIXED_SUBJECT_SIGNAL"},
    ])
    scan = _scan([])
    rows, summary, counts = two_proof_join(a4, scan)
    verds = {(r["contig_a"], r["contig_b"]): r["verdict"] for r in rows}
    assert verds[("NODE_19", "NODE_74")] == "WEAK"
    assert counts["RGGMCI_ONLY"] == 0
