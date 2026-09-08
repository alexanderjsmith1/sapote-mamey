"""v9.7.100 P-ST: subject-gene tiling evidence for RG-GMCI.

The split fingerprint is two contigs hitting DISJOINT, COMPLEMENTARY runs of subject genes in the same
reference cluster. Paralogy is two contigs hitting the SAME subject genes. These tests pin the helper and
the per-reference verdict using the representative AS-XXX NODE_105 / NODE_182 (BGC001/BGC013) AT2433-A1 mapping.
"""
from mamey.rggmci import _subject_tiling, ST_MIN_SUBJECTS_PER_SIDE


# Real AT2433-A1 (BGC0000809) subject hits from the AS-XXX KnownClusterBlast TXT.
NODE_105_AT2433 = ("ABC02802.1", "ABC02801.1", "ABC02798.1", "ABC02805.1")   # tailoring arm
NODE_182_AT2433 = ("ABC02792.1", "ABC02791.1", "ABC02795.1", "ABC02800.1",
                   "ABC02789.1", "ABC02790.1", "ABC02793.1", "ABC02794.1")   # core arm


def test_complementary_disjoint_is_the_split_fingerprint():
    t = _subject_tiling(NODE_105_AT2433, NODE_182_AT2433)
    assert t["subject_tiling_class"] == "COMPLEMENTARY_DISJOINT"
    assert t["n_shared_subjects"] == 0
    assert t["n_a_only_subjects"] == 4
    assert t["n_b_only_subjects"] == 8


def test_overlapping_subjects_flags_paralogy():
    # Same conserved subject gene hit by both contigs -> shared machinery, not a split.
    a = ("ABC02790.1", "ABC02791.1")
    b = ("ABC02790.1", "ABC02792.1")
    t = _subject_tiling(a, b)
    assert t["subject_tiling_class"] == "OVERLAPPING_SUBJECTS"
    assert t["shared_subjects"] == ("ABC02790.1",)


def test_thin_side_cannot_be_called_complementary():
    # One side with a single subject hit is too thin to call complementary either way.
    t = _subject_tiling(("ABC02805.1",), NODE_182_AT2433)
    assert t["subject_tiling_class"] == "SINGLETON_OR_THIN"
    assert ST_MIN_SUBJECTS_PER_SIDE == 2


def test_empty_subjects_is_thin_not_complementary():
    t = _subject_tiling((), ())
    assert t["subject_tiling_class"] == "SINGLETON_OR_THIN"
    assert t["n_shared_subjects"] == 0


# ── Pair-level verdict corroboration (v9.7.100) ──────────────────────────────────────────
from mamey.rggmci import (compute_rggmci, ST_MIN_DISJOINT_REFS, ST_MIN_AGG_SUBJECTS_PER_SIDE,
                          ST_MIN_GEOMETRY_FOR_SPLIT)
from mamey.models import BGCRecord


def _bgc(bid, contig, products, edge="Edge"):
    return BGCRecord(bgc_id=bid, contig=contig, region_number=1, start=1, end=10000,
                     contig_length=20000, products=list(products), edge_status=edge)


def _ref(bgc_id, contig, ref, subjects, rank=1, nprot=None, score=None, mean_id=60.0,
         interval_start=None, interval_end=None):
    return {
        "bgc_id": bgc_id, "contig": contig, "region_number": 1, "region_key": contig + ":1",
        "ref": ref, "source": ref, "reference_type": "other", "rank": rank,
        "nprot": nprot if nprot is not None else len(subjects),
        "cumulative_score": score if score is not None else 1000.0,
        "mean_identity": mean_id, "interval_start": interval_start, "interval_end": interval_end,
        "source_file": "x.txt", "subjects": tuple(subjects),
    }


def test_single_disjoint_reference_is_not_a_split():
    # Two BGCs sharing ONE reference, disjoint subjects -> default for unrelated BGCs, must NOT be SPLIT.
    bgcs = [_bgc("BGC01", "ctgA", ["NRPS"]), _bgc("BGC02", "ctgB", ["PKS"])]
    refmap = {"reference_records": [
        _ref("BGC01", "ctgA", "REF1", ["s1", "s2", "s3"]),
        _ref("BGC02", "ctgB", "REF1", ["s4", "s5", "s6"]),
    ]}
    out = compute_rggmci(bgcs, refmap)
    r = out["ranked_pairs"][0]
    assert ST_MIN_DISJOINT_REFS == 2
    assert r["subject_tiling_verdict"] == "INSUFFICIENT_SUBJECT_DATA"


def test_corroborated_disjoint_tiling_is_a_split():
    # Two BGCs, TWO shared references, disjoint + substantive + adjacent locus-proxy geometry on both
    # references -> COMPLEMENTARY_SPLIT. Subjects share a numeric locus prefix (REF_RS#####) with adjacent
    # numbers across the two contigs, so _adjacency reports good geometry via the locus-number proxy.
    bgcs = [_bgc("BGC01", "ctgA", ["NRPS"]), _bgc("BGC02", "ctgB", ["PKS"])]
    refmap = {"reference_records": [
        _ref("BGC01", "ctgA", "REF1", ["R1_RS0100", "R1_RS0105", "R1_RS0110"]),
        _ref("BGC02", "ctgB", "REF1", ["R1_RS0115", "R1_RS0120", "R1_RS0125"]),
        _ref("BGC01", "ctgA", "REF2", ["R2_RS0100", "R2_RS0105", "R2_RS0110"]),
        _ref("BGC02", "ctgB", "REF2", ["R2_RS0115", "R2_RS0120", "R2_RS0125"]),
    ]}
    out = compute_rggmci(bgcs, refmap)
    r = out["ranked_pairs"][0]
    assert r["good_geometry_references"] >= ST_MIN_GEOMETRY_FOR_SPLIT
    assert r["subject_tiling_verdict"] == "COMPLEMENTARY_SPLIT"
    assert r["complementary_disjoint_refs"] == 2
    assert r["overlapping_subject_refs"] == 0


def test_disjoint_without_geometry_is_insufficient_not_split():
    # Same disjoint subjects but NO adjacency geometry (cross-namespace loci, no proxy) -> INSUFFICIENT.
    bgcs = [_bgc("BGC01", "ctgA", ["NRPS"]), _bgc("BGC02", "ctgB", ["PKS"])]
    refmap = {"reference_records": [
        _ref("BGC01", "ctgA", "REF1", ["aaa.1", "bbb.1", "ccc.1"]),
        _ref("BGC02", "ctgB", "REF1", ["ddd.1", "eee.1", "fff.1"]),
        _ref("BGC01", "ctgA", "REF2", ["ggg.1", "hhh.1", "iii.1"]),
        _ref("BGC02", "ctgB", "REF2", ["jjj.1", "kkk.1", "lll.1"]),
    ]}
    out = compute_rggmci(bgcs, refmap)
    r = out["ranked_pairs"][0]
    assert r["subject_tiling_verdict"] == "INSUFFICIENT_SUBJECT_DATA"


def test_shared_subjects_flag_paralog_not_split():
    bgcs = [_bgc("BGC01", "ctgA", ["NRPS"]), _bgc("BGC02", "ctgB", ["NRPS"])]
    refmap = {"reference_records": [
        _ref("BGC01", "ctgA", "REF1", ["s1", "s2", "s3"]),
        _ref("BGC02", "ctgB", "REF1", ["s1", "s2", "s9"]),  # share s1,s2
        _ref("BGC01", "ctgA", "REF2", ["t1", "t2", "t3"]),
        _ref("BGC02", "ctgB", "REF2", ["t1", "t2", "t9"]),
    ]}
    out = compute_rggmci(bgcs, refmap)
    r = out["ranked_pairs"][0]
    assert r["subject_tiling_verdict"] == "OVERLAPPING_PARALOG"


# ── v9.7.352 AMBER_CORRECTNESS FIX 2: two-proof rule now GATES confidence ──────────────────
#
# Before this cut subject_tiling_verdict was observational and never gated rggmci_confidence, so a
# same-class paralog pair with good geometry (OVERLAPPING_PARALOG) still reached HIGH_RG_GMCI_RESCUE
# and both BGCs collected the +8 triage rescue in scoring.py — a single-proof rescue that the governing
# rggmci-two-proof rule (homology AND biosynthetic-logic complementarity) exists to block. FIX 2 demotes
# OVERLAPPING_PARALOG out of rescue eligibility (proof 2 is affirmatively refuted). Genuine complementary
# splits keep HIGH and their rescue.

from mamey.scoring import triage_bgcs


def _paralog_refmap():
    # same specific class both sides + good geometry (RS-locus adjacency) + SHARED subject genes on
    # every reference -> OVERLAPPING_PARALOG that would previously reach HIGH via geometry+product gate.
    return {"reference_records": [
        _ref("BGC01", "ctgA", "REF1", ["R1_RS0100", "R1_RS0105", "s3"]),
        _ref("BGC02", "ctgB", "REF1", ["R1_RS0100", "R1_RS0105", "s9"]),
        _ref("BGC01", "ctgA", "REF2", ["R2_RS0100", "R2_RS0105", "t3"]),
        _ref("BGC02", "ctgB", "REF2", ["R2_RS0100", "R2_RS0105", "t9"]),
    ]}


def test_overlapping_paralog_is_demoted_below_high():
    bgcs = [_bgc("BGC01", "ctgA", ["NRPS"]), _bgc("BGC02", "ctgB", ["NRPS"])]
    out = compute_rggmci(bgcs, _paralog_refmap())
    r = out["ranked_pairs"][0]
    assert r["subject_tiling_verdict"] == "OVERLAPPING_PARALOG"
    # proof-2 refuted -> demoted out of rescue eligibility (not HIGH, not MODERATE candidate)
    assert r["rggmci_confidence"] != "HIGH_RG_GMCI_RESCUE", r
    assert r["rggmci_confidence"] not in ("HIGH_RG_GMCI_RESCUE", "MODERATE_RG_GMCI_CANDIDATE"), r
    assert "ST-PARALOG_no_complementarity_proof" in r["acceptance_gate"]


def test_overlapping_paralog_gets_no_rescue_bonus():
    """A demoted paralog pair must not add any RG-GMCI rescue bonus to either BGC — scores match the
    no-RGGMCI baseline exactly."""
    bgcs = [_bgc("BGC01", "ctgA", ["NRPS"]), _bgc("BGC02", "ctgB", ["NRPS"])]
    out = compute_rggmci(bgcs, _paralog_refmap())
    with_rg = {t.bgc_id: (t.ab_score, t.af_score, t.novelty_score) for t in triage_bgcs(bgcs, rggmci=out)}
    baseline = {t.bgc_id: (t.ab_score, t.af_score, t.novelty_score) for t in triage_bgcs(bgcs)}
    assert with_rg == baseline, (with_rg, baseline)


def test_complementary_split_keeps_high_and_rescue():
    """Positive control: genuine complementary tiling (proof 2 satisfied) still reaches HIGH and DOES
    grant the rescue bonus — the gate is selective, not a blanket suppression."""
    bgcs = [_bgc("BGC01", "ctgA", ["NRPS"]), _bgc("BGC02", "ctgB", ["PKS"])]
    refmap = {"reference_records": [
        _ref("BGC01", "ctgA", "REF1", ["R1_RS0100", "R1_RS0105", "R1_RS0110"]),
        _ref("BGC02", "ctgB", "REF1", ["R1_RS0115", "R1_RS0120", "R1_RS0125"]),
        _ref("BGC01", "ctgA", "REF2", ["R2_RS0100", "R2_RS0105", "R2_RS0110"]),
        _ref("BGC02", "ctgB", "REF2", ["R2_RS0115", "R2_RS0120", "R2_RS0125"]),
    ]}
    out = compute_rggmci(bgcs, refmap)
    r = out["ranked_pairs"][0]
    assert r["subject_tiling_verdict"] == "COMPLEMENTARY_SPLIT"
    assert r["rggmci_confidence"] == "HIGH_RG_GMCI_RESCUE"
    with_rg = {t.bgc_id: t.novelty_score for t in triage_bgcs(bgcs, rggmci=out)}
    baseline = {t.bgc_id: t.novelty_score for t in triage_bgcs(bgcs)}
    assert with_rg != baseline  # rescue bonus applied to the genuine split
