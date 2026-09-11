from mamey.models import BGCRecord
from mamey.rggmci import _terminus_sequence_state, compute_rggmci


def _bgc(bid, contig, edge, start, end, length):
    return BGCRecord(
        bgc_id=bid, contig=contig, region_number=1, start=start, end=end,
        contig_length=length, products=["lanthipeptide"], edge_status=edge,
    )


def _ref(bid, contig):
    return {
        "bgc_id": bid, "contig": contig, "region_number": 1,
        "region_key": contig + "_c1", "ref": "BGC0000001",
        "source": "reference chromosome", "reference_type": "lanthipeptide",
        "rank": 1, "nprot": 3, "cumulative_score": 1000.0,
        "mean_identity": 70.0, "interval_start": 1, "interval_end": 100,
        "source_file": "knownclusterblast/x.txt", "subjects": ("s1", "s2"),
        "db_kind": "knownclusterblast",
    }


def test_homopolymer_terminus_is_long_read_only_and_cannot_override():
    a = _bgc("BGC001", "NODE_A", "Edge", 801, 1000, 1000)
    b = _bgc("BGC002", "NODE_B", "Full-contig", 1, 100, 100)
    contigs = {"NODE_A": "ACGT" * 200 + "A" * 200, "NODE_B": "ACGT" * 25}
    refs = {"reference_records": [_ref("BGC001", "NODE_A"), _ref("BGC002", "NODE_B")]}
    row = compute_rggmci([a, b], refs, contigs=contigs)["ranked_pairs"][0]
    assert row["terminus_sequence_state_a"] == "HOMOPOLYMER_TERMINUS"
    assert row["junction_evidence_state"] == "LONG_READ_ONLY"
    assert row["terminus_truncation_rescue"] is False
    assert row["terminus_override_note"].startswith("LONG_READ_ONLY")


def test_balanced_terminus_remains_complex():
    bgc = _bgc("BGC001", "NODE_A", "Edge", 801, 1000, 1000)
    assert _terminus_sequence_state(bgc, {"NODE_A": "ACGT" * 250}) == "COMPLEX_TERMINUS"


def test_missing_sequence_is_explicit_not_clear():
    bgc = _bgc("BGC001", "NODE_A", "Edge", 801, 1000, 1000)
    assert _terminus_sequence_state(bgc, {}) == "TERMINUS_SEQUENCE_UNAVAILABLE"
