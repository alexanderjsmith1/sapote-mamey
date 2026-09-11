"""v9.7.49 — intake dedup gate. A different strain with an identical BGC fingerprint (the ST-956 == ST-678 (identical-fingerprint mislabel)
mislabel) is flagged; a genuinely different strain and a same-sid re-bank are not."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.ingest_package import strain_fingerprint, find_duplicate


def _bgcs(spec):
    return [{"sid": "X", "products": p, "length_kb": kb, "edge_status": e} for (p, kb, e) in spec]


SPEC_A = [("NRPS;other", 44.0, "Interior"), ("terpene", 21.0, "Edge"), ("RiPP", 12.5, "Full")]
SPEC_B = [("T2PKS", 30.0, "Interior"), ("siderophore", 18.0, "Interior")]


def test_identical_fingerprint_detected():
    bank = {"strains": {"ST-678": "n"}, "bgcs": [dict(b, sid="ST-678") for b in _bgcs(SPEC_A)]}
    dup = find_duplicate(_bgcs(SPEC_A), bank, self_sid="ST-956")  # different sid, identical genome
    assert dup == "ST-678"


def test_distinct_strain_not_flagged():
    bank = {"strains": {"ST-678": "n"}, "bgcs": [dict(b, sid="ST-678") for b in _bgcs(SPEC_A)]}
    assert find_duplicate(_bgcs(SPEC_B), bank, self_sid="ST-100") is None


def test_same_sid_rebank_not_a_duplicate():
    bank = {"strains": {"ST-678": "n"}, "bgcs": [dict(b, sid="ST-678") for b in _bgcs(SPEC_A)]}
    assert find_duplicate(_bgcs(SPEC_A), bank, self_sid="ST-678") is None


def test_fingerprint_stable_and_order_independent():
    assert strain_fingerprint(_bgcs(SPEC_A)) == strain_fingerprint(_bgcs(list(reversed(SPEC_A))))


def test_empty_strain_no_false_dup():
    bank = {"strains": {"ST-678": "n"}, "bgcs": []}
    assert find_duplicate([], bank, self_sid="ST-1") is None
