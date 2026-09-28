"""Two regions on one contig are never an RG-GMCI rescue; they are listed as related loci.

A contig with a region at each end has both regions flagged as on a contig edge, yet no assembly break separates
them. Such a pair reached HIGH and gave both regions the triage rescue bonus, although candidate groups already left it
out. Alex, 2026-09-27, approved moving these pairs to the related-loci list.
"""
from mamey.models import BGCRecord
from mamey.rggmci import RELATED_LOCUS_LABEL, compute_rggmci, related_locus_pairs
from mamey.scoring import triage_bgcs


def _bgc(bid, contig, edge, start, end, clen):
    return BGCRecord(bgc_id=bid, contig=contig, region_number=1, start=start, end=end,
                     contig_length=clen, products=["NRPS"], edge_status=edge)


def _ref(bgc_id, contig, ref, subjects):
    return {"bgc_id": bgc_id, "contig": contig, "region_number": 1, "region_key": contig + "_c1", "ref": ref,
            "source": ref, "reference_type": "nrps", "rank": 1, "nprot": len(subjects), "cumulative_score": 1000.0,
            "mean_identity": 60.0, "interval_start": None, "interval_end": None,
            "source_file": f"knownclusterblast/{contig}_c1.txt", "subjects": tuple(subjects),
            "db_kind": "knownclusterblast"}


# A and B sit at the two ends of one contig; C is a whole small contig. All three tile the same references.
BGCS = [
    _bgc("A", "ctgLong", "Edge", 1, 20000, 170000),
    _bgc("B", "ctgLong", "Edge", 150001, 170000, 170000),
    _bgc("C", "ctgSmall", "Full-contig", 1, 9000, 9000),
]
CONTIGS = {"A": "ctgLong", "B": "ctgLong", "C": "ctgSmall"}
REFMAP = {"reference_records": [
    _ref(b, CONTIGS[b], ref, genes)
    for ref in ("BGC0000001", "BGC0000002", "BGC0000003")
    for b, genes in (("A", ["g1", "g2", "g3"]), ("B", ["g4", "g5", "g6"]), ("C", ["g7", "g8", "g9"]))
]}
EDGE = {"A", "B", "C"}


def test_same_contig_pairs_are_not_rescues():
    out = compute_rggmci(BGCS, REFMAP, contig_edge_bgcs=EDGE)
    pairs = {p["pair"] for p in out["ranked_pairs"]}
    assert "A+B" not in pairs
    assert pairs == {"A+C", "B+C"}
    assert "different_contigs" in out["pairing_scope"]


def test_same_contig_pairs_are_listed_as_related_loci():
    rel = {p["pair"]: p for p in related_locus_pairs(BGCS, REFMAP, EDGE)}
    assert set(rel) == {"A+B"}
    assert rel["A+B"]["rggmci_confidence"] == RELATED_LOCUS_LABEL
    assert rel["A+B"]["related_because"] == "same contig"
    assert rel["A+B"]["interior_side"] == ""


def test_interior_and_same_contig_reasons_are_both_named():
    bgcs = BGCS[:1] + [_bgc("B", "ctgLong", "Interior", 80001, 100000, 170000)] + BGCS[2:]
    rel = {p["pair"]: p for p in related_locus_pairs(bgcs, REFMAP, {"A", "C"})}
    assert rel["A+B"]["related_because"] == "interior region; same contig"
    assert rel["B+C"]["related_because"] == "interior region"


def test_triage_gives_no_rescue_bonus_to_a_same_contig_pair_from_an_older_package():
    old = {"ranked_pairs": [{"pair": "A+B", "bgc_a": "A", "bgc_b": "B", "contig_a": "ctgLong", "contig_b": "ctgLong",
                             "rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "rggmci_score": 29}]}
    with_pair = {t.bgc_id: t for t in triage_bgcs(BGCS, old)}
    without = {t.bgc_id: t for t in triage_bgcs(BGCS, {"ranked_pairs": []})}
    for bid in ("A", "B"):
        assert with_pair[bid].ab_score == without[bid].ab_score
        assert "RG-GMCI=" not in with_pair[bid].rationale
