"""v9.7.377 BLACK_CHERRY correctness fix: _shared_class_tokens must not let a qualified
antiSMASH product class (e.g. 'NI-siderophore') collide, via naive substring containment,
with its own unqualified substring class ('siderophore') -- these are listed separately in
_CLASS_TOKENS because antiSMASH treats them as DIFFERENT, biosynthetically distinct product
types (NRPS-independent vs NRPS-dependent siderophore/metallophore synthesis).

The false "shared specific class" verdict this collision produces is claim-safety critical:
it feeds directly into the terminus-truncation rescue's OVERLAPPING_PARALOG override, so a
pair whose only real evidence is a genuinely shared subject gene (e.g. a siderophore-uptake
receptor conserved across UNRELATED siderophore gene clusters -- the textbook false-paralog
case) gets its correct OVERLAPPING_PARALOG verdict silently flipped to TERMINUS_TRUNCATION_SPLIT,
and its rggmci_confidence promoted out of LOW into MODERATE/HIGH rescue eligibility, purely off
a text-substring artifact rather than any real biosynthetic-logic complementarity.
"""
from mamey.rggmci import _shared_class_tokens, compute_rggmci
from mamey.models import BGCRecord


def test_qualified_and_unqualified_siderophore_are_not_a_shared_class():
    # NI-siderophore (NRPS-independent) and siderophore (generic/NRPS-dependent) are two
    # DIFFERENT antiSMASH product types -- both separately listed in _CLASS_TOKENS -- so they
    # must NOT be reported as a shared specific class.
    assert _shared_class_tokens("NI-siderophore", "siderophore") == set()


def test_qualified_and_unqualified_metallophore_are_not_a_shared_class():
    assert _shared_class_tokens("NRP-metallophore", "metallophore") == set()


def test_genuinely_shared_specific_class_still_detected():
    # Regression guard: the fix must not break real shared-class detection.
    assert "lanthipeptide" in _shared_class_tokens("RiPP; lanthipeptide-class-i", "lanthipeptide; other")
    assert "bottromycin" in _shared_class_tokens("bottromycin", "bottromycin; RiPP")


def test_generic_umbrella_tokens_still_excluded():
    assert _shared_class_tokens("RRE-containing; RiPP", "RiPP; RiPP-like; bottromycin") == set()


def _bgc(bid, contig, products, edge, start, end, clen):
    return BGCRecord(bgc_id=bid, contig=contig, region_number=1, start=start, end=end,
                     contig_length=clen, products=list(products), edge_status=edge)


def _ref(bgc_id, contig, ref, subjects):
    return {
        "bgc_id": bgc_id, "contig": contig, "region_number": 1, "region_key": contig + "_c1",
        "ref": ref, "source": ref, "reference_type": "siderophore", "rank": 1,
        "nprot": len(subjects), "cumulative_score": 1000.0, "mean_identity": 60.0,
        "interval_start": None, "interval_end": None, "source_file": f"knownclusterblast/{contig}_c1.txt",
        "subjects": tuple(subjects), "db_kind": "knownclusterblast",
    }


def test_end_to_end_paralog_verdict_survives_substring_collision():
    """The production, end-to-end failure mode: a terminus-truncated NI-siderophore fragment
    paired with an unrelated, non-truncated 'siderophore' BGC that happens to share one
    conserved subject gene (the textbook false-paralog case -- e.g. a TonB-dependent uptake
    receptor common across many unrelated siderophore clusters). Correct behavior: the pair
    stays OVERLAPPING_PARALOG (proof-2 refuted) and is demoted out of rescue eligibility.
    The pre-fix substring collision instead overrides it to a false TERMINUS_TRUNCATION_SPLIT
    and promotes rggmci_confidence to MODERATE_RG_GMCI_CANDIDATE.
    """
    bgcs = [
        _bgc("SID01", "NODE_1_length_9000", ["NI-siderophore"], "Edge", 8600, 9000, 9000),
        _bgc("SID02", "NODE_2_length_100000", ["siderophore"], "Interior", 40000, 60000, 100000),
    ]
    refmap = {"reference_records": [
        _ref("SID01", "NODE_1_length_9000", "BGC_SIDERO", ["S1", "S2"]),
        _ref("SID02", "NODE_2_length_100000", "BGC_SIDERO", ["S1", "S3"]),  # shared S1 -> paralog
    ]}
    out = compute_rggmci(bgcs, refmap)
    r = out["ranked_pairs"][0]
    assert r["shared_class_tokens"] == "", r
    assert r["terminus_truncation_rescue"] is False, r
    assert r["subject_tiling_verdict"] == "OVERLAPPING_PARALOG", r
    assert r["rggmci_confidence"] not in ("HIGH_RG_GMCI_RESCUE", "MODERATE_RG_GMCI_CANDIDATE"), r
