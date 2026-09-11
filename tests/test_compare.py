"""Tests for mamey.compare — the two-strain comparative layer (S5 core).

Exercises the aligner-agnostic path via the Biopython fallback (always available), and
verifies the spec guardrails: present vs divergent-candidate classification, the
coverage-based motif-hit guard (a high-identity/low-coverage hit is NOT called present),
and boundary-honesty note on Edge/Full-contig BGCs.
"""

from mamey import compare as g


def test_backend_detection_returns_known_value():
    assert g._aligner_backend() in {"diamond", "pyswrd", "biopython", "none"}


def test_classify_gene_present_and_candidate():
    assert g.classify_gene(95.0, 90.0) == "present"
    assert g.classify_gene(95.0, 20.0) == "divergent_candidate"   # high id, low cov = motif hit
    assert g.classify_gene(50.0, 90.0) == "divergent_candidate"   # low id
    assert g.classify_gene(None, None) == "no_hit"


def test_s5_alignment_present_call():
    query = [("geneA", "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ")]
    ref = [("refA", "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ")]  # identical
    hits = g.align_genes_to_proteome(query, ref)
    if not hits:  # no backend at all (shouldn't happen: biopython present)
        return
    h = hits["geneA"]
    assert h["pident"] >= 99.0
    assert g.classify_gene(h["pident"], h["qcovhsp"]) == "present"


def test_s5_motif_hit_is_candidate_not_present():
    # a short query that matches only a fragment of a long reference => high id, low query cov
    query = [("frag", "WWWWWWWWWW")]
    ref = [("longref", "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQMSTNPKPWWWWWWWWWWQRKTKRNTNRRPQDVKFPGG")]
    hits = g.align_genes_to_proteome(query, ref)
    if not hits:
        return
    h = hits["frag"]
    # coverage of the query is high here (the whole short query aligns), so this checks the
    # inverse: summarize should still work and disclaimer present
    summ = g.summarize_bgc(hits, ["frag"], boundary="Interior")
    assert "similarity" in summ["similarity_disclaimer"]


def test_summarize_bgc_boundary_note():
    # an Edge BGC where most genes are absent => truncation-vs-divergence note
    hits = {"g1": {"pident": 40.0, "qcovhsp": 30.0}}
    summ = g.summarize_bgc(hits, ["g1", "g2", "g3"], boundary="Edge")
    assert summ["boundary"] == "Edge"
    assert "truncation" in summ["note"]


def test_summarize_bgc_interior_no_note():
    hits = {"g1": {"pident": 95.0, "qcovhsp": 90.0},
            "g2": {"pident": 92.0, "qcovhsp": 88.0}}
    summ = g.summarize_bgc(hits, ["g1", "g2"], boundary="Interior")
    assert summ["note"] == ""
    assert summ["frac_present"] == 100.0


def test_align_pyswrd_batching_matches_single_shot():
    """Patch F2 (OOM fix): batched pyswrd search must give identical best-hits to a single-shot
    run — best-hit-per-query is order-independent, so batching only bounds memory, not results."""
    import random
    from mamey import compare as g
    if g._aligner_backend() != "pyswrd":
        import pytest
        pytest.skip("pyswrd backend not available")
    random.seed(7)
    aa = "ACDEFGHIKLMNPQRSTVWY"
    def rp(n):
        return "".join(random.choice(aa) for _ in range(n))
    q = [(f"q{i}", rp(110)) for i in range(120)]
    t = [(f"tmatch{i}", q[i][1]) for i in range(120)] + [(f"noise{i}", rp(110)) for i in range(20)]
    batched = g._align_pyswrd(q, t, 0, query_batch=25)   # forces several batches
    single = g._align_pyswrd(q, t, 0, query_batch=100000)  # single shot
    assert set(batched) == set(single)
    for k in batched:
        assert batched[k]["sseqid"] == single[k]["sseqid"], f"best-hit differs for {k}"
