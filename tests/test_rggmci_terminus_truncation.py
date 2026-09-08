"""v9.7.100 P-TT: terminus-truncation rescue overrides paralogy on multi-copy-within-cluster genes.

Pins a synthetic bottromycin terminus-split case (mirrors AS-XXX bottromycin): BGC018 (RRE-containing RiPP, Edge, ends AT the NODE_28 terminus)
+ BGC042 (bottromycin, Full-contig, the whole 9.8 kb NODE_69) are ONE cluster split by the assembly break.
Subject tiling calls it OVERLAPPING_PARALOG because both fragments carry a Bottromycin_Methyltransferase_RRE
gene (legitimately multi-copy in one bottromycin cluster); the coordinate-confirmed truncation must override.
"""
from mamey.rggmci import (_terminus_truncation, _shared_class_tokens, compute_rggmci,
                          TT_TERMINUS_MARGIN_BP, TT_SMALL_PARTNER_BP)
from mamey.models import BGCRecord


def _bgc(bid, contig, products, edge, start, end, clen):
    return BGCRecord(bgc_id=bid, contig=contig, region_number=1, start=start, end=end,
                     contig_length=clen, products=list(products), edge_status=edge)


def test_terminus_truncation_detects_contig_end():
    # BGC018: region 62389-73283 on a 73283 bp contig -> ends exactly at terminus -> 'end'.
    b = _bgc("BGC018", "NODE_28_length_73283", ["RRE-containing", "RiPP"], "Edge", 62389, 73283, 73283)
    assert _terminus_truncation(b) == "end"


def test_interior_region_is_not_truncated():
    b = _bgc("BGC017", "NODE_28_length_73283", ["saccharide"], "Interior", 18604, 39621, 73283)
    assert _terminus_truncation(b) == ""


def test_edge_not_near_boundary_is_not_truncated():
    # Edge label but the region sits >margin from both ends (shouldn't normally happen, but guard it).
    b = _bgc("X", "C_length_100000", ["nrps"], "Edge", 40000, 60000, 100000)
    assert _terminus_truncation(b) == ""


def test_shared_class_tokens_are_specific_not_umbrella():
    # Generic umbrellas (ripp, rre-containing, pks, saccharide) are NOT shared-class anchors; only specific
    # classes are. Bottromycin's products share no SPECIFIC token, so this is empty — the bottromycin rescue
    # must therefore come from severed-arm geometry (small complete partner contig), not class match.
    assert _shared_class_tokens("RRE-containing; RiPP", "RiPP; RiPP-like; bottromycin") == set()
    assert "lanthipeptide" in _shared_class_tokens("RiPP; lanthipeptide-class-i", "lanthipeptide; other")


def _ref(bgc_id, contig, ref, subjects, db_kind="knownclusterblast", rank=1):
    return {
        "bgc_id": bgc_id, "contig": contig, "region_number": 1, "region_key": contig + "_c1",
        "ref": ref, "source": ref, "reference_type": "ripp", "rank": rank,
        "nprot": len(subjects), "cumulative_score": 1000.0, "mean_identity": 60.0,
        "interval_start": None, "interval_end": None, "source_file": f"knownclusterblast/{contig}_c1.txt",
        "subjects": tuple(subjects), "db_kind": db_kind,
    }


def test_terminus_truncation_overrides_paralog():
    # Both fragments hit the same reference subject (the shared RRE gene) -> tiling would say PARALOG.
    # BGC018 is terminus-truncated on a different contig from the small Full-contig BGC042 -> override.
    bgcs = [
        _bgc("BGC018", "NODE_28_length_73283", ["RRE-containing", "RiPP"], "Edge", 62389, 73283, 73283),
        _bgc("BGC042", "NODE_69_length_9799", ["RiPP", "bottromycin"], "Full-contig", 1, 9799, 9799),
    ]
    refmap = {"reference_records": [
        # Shared subject 'RRE1' on both -> OVERLAPPING_SUBJECTS -> would be OVERLAPPING_PARALOG.
        _ref("BGC018", "NODE_28_length_73283", "BGC_BOTTRO", ["RRE1", "MTF1"]),
        _ref("BGC042", "NODE_69_length_9799", "BGC_BOTTRO", ["RRE1", "YCAO1"]),
    ]}
    out = compute_rggmci(bgcs, refmap)
    r = out["ranked_pairs"][0]
    assert r["terminus_truncation_rescue"] is True
    assert r["subject_tiling_verdict"] == "TERMINUS_TRUNCATION_SPLIT"
    assert "OVERRODE_OVERLAPPING_PARALOG" in r["terminus_override_note"]


def test_genuine_paralog_not_overridden():
    # Two core-complete fragments on different contigs, NEITHER terminus-truncated, shared subject ->
    # stays OVERLAPPING_PARALOG (the function is preserved, not eliminated).
    bgcs = [
        _bgc("BGC008", "NODE_15_length_157950", ["PKS", "T1PKS"], "Interior", 40000, 60000, 157950),
        _bgc("BGC032", "NODE_47_length_28356", ["PKS", "T1PKS"], "Interior", 5000, 22000, 28356),
    ]
    refmap = {"reference_records": [
        _ref("BGC008", "NODE_15_length_157950", "BGC_X", ["S1", "S2"]),
        _ref("BGC032", "NODE_47_length_28356", "BGC_X", ["S1", "S3"]),  # shared S1
    ]}
    out = compute_rggmci(bgcs, refmap)
    r = out["ranked_pairs"][0]
    assert r["terminus_truncation_rescue"] is False
    assert r["subject_tiling_verdict"] == "OVERLAPPING_PARALOG"
