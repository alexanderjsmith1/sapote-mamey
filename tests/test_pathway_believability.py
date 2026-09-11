"""FA4: tests for the per-locus committed-step believability prior (mamey/pathway_believability.py).

Synthetic phosphonate-anchored loci, WITH vs WITHOUT the committed gene, plus the two over-call
guards the classifier exists for:
  * a lone/weak PepM gateway (no committed pull, no downstream) -> LOW  (defeats the ICL-superfamily
    over-call: a bare PEP_mutase is NOT a confident phosphonate call);
  * a phosphonate class flag with NO gateway at all -> SUSPECT.
Also asserts the result is explicitly NON-RANKING and delegates to the shared marker registry.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey import pathway_believability as pb  # noqa: E402


def _cds(lt, domains=(), product="", gene_functions=""):
    return {"locus_tag": lt, "sec_met_domains": list(domains),
            "product": product, "gene_functions": gene_functions}


# WITH the committed gene: strong PepM gateway + TPP decarboxylase (committed pull) + aminotransferase
# (downstream warhead) -> canonical committed signature.
LOCUS_WITH_COMMITTED = [
    _cds("g1", product="phosphoenolpyruvate mutase",
         gene_functions="PEP_mutase (E-value: 1e-80, bitscore: 250.0)"),
    _cds("g2", domains=["TPP_enzyme_N"], gene_functions="phosphonopyruvate decarboxylase (tpp_enzyme)"),
    _cds("g3", gene_functions="aminotransferase class-III"),
]

# WITHOUT the committed gene: a lone, weak PepM only -> the ICL-superfamily false-positive mode.
LOCUS_WITHOUT_COMMITTED = [
    _cds("g1", gene_functions="PEP_mutase (E-value: 0.01, bitscore: 30.0)"),
    _cds("g2", gene_functions="hypothetical protein"),
]

# antiSMASH called "phosphonate" but no gateway enzyme captured -> SUSPECT.
LOCUS_CLASS_FLAG_NO_GATEWAY = [
    _cds("g1", product="phosphonate", gene_functions="hypothetical protein"),
    _cds("g2", gene_functions="ABC transporter"),
]


def test_with_committed_gene_is_high():
    r = pb.classify_locus(LOCUS_WITH_COMMITTED, "phosphonate")
    assert r.believability_tier == "HIGH", r
    assert r.evidence["gateway"] and r.evidence["committed"]
    assert r.non_ranking is True


def test_without_committed_gene_is_low():
    r = pb.classify_locus(LOCUS_WITHOUT_COMMITTED, "phosphonate")
    assert r.believability_tier == "LOW", r
    # LOW must name the ICL-superfamily false-positive risk (the over-call this defeats).
    assert "isocitrate-lyase" in r.evidence["fp_superfamily"]
    assert "false positive" in r.reason.lower()


def test_with_beats_without():
    from mamey.class_believability import RANK
    hi = pb.believability_tier(LOCUS_WITH_COMMITTED, "phosphonate")
    lo = pb.believability_tier(LOCUS_WITHOUT_COMMITTED, "phosphonate")
    assert RANK[hi] < RANK[lo]  # committed signature ranks strictly stronger


def test_class_flag_without_gateway_is_suspect():
    assert pb.believability_tier(LOCUS_CLASS_FLAG_NO_GATEWAY, "phosphonate") == "SUSPECT"


def test_non_candidate_is_none():
    assert pb.believability_tier([_cds("g1", gene_functions="DNA polymerase")], "phosphonate") == "NONE"


def test_phosphonate_is_available_and_unknown_class_raises():
    assert "phosphonate" in pb.available_classes()
    try:
        pb.classify_locus([], "not_a_class")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for an unregistered class")
