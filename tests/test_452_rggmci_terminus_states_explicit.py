"""Terminal sequence states stay explicit: unavailable and ambiguous termini are never CLEAR (P300-152).

Synthetic noncoding sequence only.
"""
from mamey.models import BGCRecord
from mamey.rggmci import _terminus_sequence_state, compute_rggmci

COMPLEX = "ACGTTGCAAGCTTCGA" * 60          # 960 bp, entropy 2 bits, no homopolymer


def _bgc(bid, contig, edge, start, end, length):
    return BGCRecord(bgc_id=bid, contig=contig, region_number=1, start=start, end=end,
                     contig_length=length, products=["lanthipeptide"], edge_status=edge)


def _ref(bid, contig):
    return {"bgc_id": bid, "contig": contig, "region_number": 1, "region_key": contig + "_c1",
            "ref": "BGC0000001", "source": "reference chromosome", "reference_type": "lanthipeptide",
            "rank": 1, "nprot": 3, "cumulative_score": 1000.0, "mean_identity": 70.0,
            "interval_start": 1, "interval_end": 100, "source_file": "knownclusterblast/x.txt",
            "subjects": ("s1", "s2"), "db_kind": "knownclusterblast"}


def _pair_row(contigs):
    a = _bgc("BGC001", "NODE_A", "Edge", 801, 1000, 1000)
    b = _bgc("BGC002", "NODE_B", "Full-contig", 1, 100, 100)
    refs = {"reference_records": [_ref("BGC001", "NODE_A"), _ref("BGC002", "NODE_B")]}
    return compute_rggmci([a, b], refs, contigs=contigs)["ranked_pairs"][0]


def test_terminal_ns_are_assessed_in_place_not_replaced_by_interior():
    bgc = _bgc("BGC001", "NODE_A", "Edge", 801, 1000, 1000)
    # The last 200 bp are 150 complex bases then 50 N. Deleting the Ns first used to read 200 complex bases.
    seq = COMPLEX[:800] + COMPLEX[:150] + "N" * 50
    assert _terminus_sequence_state(bgc, {"NODE_A": seq}) == "AMBIGUOUS_TERMINUS"


def test_low_complexity_behind_terminal_ns_is_still_vetoed():
    bgc = _bgc("BGC001", "NODE_A", "Edge", 801, 1000, 1000)
    seq = COMPLEX[:800] + "AT" * 75 + "N" * 50       # callable terminal bases are a dinucleotide repeat
    assert _terminus_sequence_state(bgc, {"NODE_A": seq}) == "LOW_COMPLEXITY_TERMINUS"


def test_all_n_terminus_is_ambiguous():
    bgc = _bgc("BGC001", "NODE_A", "Edge", 801, 1000, 1000)
    assert _terminus_sequence_state(bgc, {"NODE_A": COMPLEX[:800] + "N" * 200}) == "AMBIGUOUS_TERMINUS"


def test_clean_termini_are_unchanged():
    bgc = _bgc("BGC001", "NODE_A", "Edge", 801, 1000, 1000)
    assert _terminus_sequence_state(bgc, {"NODE_A": COMPLEX[:1000]}) == "COMPLEX_TERMINUS"
    assert _terminus_sequence_state(bgc, {"NODE_A": COMPLEX[:800] + "A" * 200}) == "HOMOPOLYMER_TERMINUS"
    # Interior Ns away from the terminal window do not change the reading.
    assert _terminus_sequence_state(bgc, {"NODE_A": "N" * 100 + COMPLEX[:900]}) == "COMPLEX_TERMINUS"


def test_missing_sequence_is_not_labelled_clear():
    row = _pair_row(None)
    assert row["terminus_sequence_state_a"] == "TERMINUS_SEQUENCE_UNAVAILABLE"
    assert row["junction_evidence_state"] == "SEQUENCE_COMPLEXITY_UNRESOLVED"


def test_ambiguous_terminus_is_not_labelled_clear():
    row = _pair_row({"NODE_A": COMPLEX[:950] + "N" * 50, "NODE_B": COMPLEX[:100]})
    assert row["terminus_sequence_state_a"] == "AMBIGUOUS_TERMINUS"
    assert row["junction_evidence_state"] == "SEQUENCE_COMPLEXITY_UNRESOLVED"


def test_measured_complex_terminus_is_still_clear():
    row = _pair_row({"NODE_A": COMPLEX[:1000], "NODE_B": COMPLEX[:100]})
    assert row["terminus_sequence_state_a"] == "COMPLEX_TERMINUS"
    assert row["junction_evidence_state"] == "SEQUENCE_COMPLEXITY_CLEAR"


def test_pair_without_truncated_terminus_is_not_applicable():
    # Edge regions (engine 5 kb flank) that stop more than 500 bp short of both contig ends.
    a = _bgc("BGC001", "NODE_A", "Edge", 600, 1400, 2000)
    b = _bgc("BGC002", "NODE_B", "Edge", 600, 1400, 2000)
    refs = {"reference_records": [_ref("BGC001", "NODE_A"), _ref("BGC002", "NODE_B")]}
    seq = (COMPLEX * 3)[:2000]
    rows = compute_rggmci([a, b], refs, contigs={"NODE_A": seq, "NODE_B": seq})["ranked_pairs"]
    assert rows and rows[0]["junction_evidence_state"] == "NOT_APPLICABLE"
