"""v9.7.233: readiness lints — bind card prose to the deterministic data + to itself.
Targets the real BGC043 failures: novelty asserted at 100% identity, and ctg66_8 '1 TTA
in §28 / 7 TTA in §15'. Hermetic (bgc_context passed directly; no package needed)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.modeb_structure_gate import (
    _novelty_conservation_findings, _internal_consistency_findings,
    _fact_binding_findings, readiness_state,
)


def _codes(fs):
    return {x["code"] for x in fs}


# ---- NOVELTY_CONTRADICTION: data-relative ----
def test_novelty_flagged_when_conserved():
    ctx = {"conservation_median_id": 100.0, "conservation_n_genes": 34, "multispecies_hits": 31}
    card = "## §2 Why selected\nThis represents meaningful structural novelty and a rare halogenase.\n"
    assert "NOVELTY_CONTRADICTION" in _codes(_novelty_conservation_findings(card, ctx))


def test_novelty_allowed_when_divergent():
    ctx = {"conservation_median_id": 67.0, "conservation_n_genes": 10}
    card = "## §19 Judgement\nThis is the standout novelty lead — a genuinely novel scaffold.\n"
    assert not _novelty_conservation_findings(card, ctx)      # divergent -> allowed


def test_novelty_allows_uncharacterised_language_when_conserved():
    ctx = {"conservation_median_id": 100.0, "conservation_n_genes": 34}
    card = "## §8 KCB\nNo MIBiG match; the compound is uncharacterised though the machinery is genus-common.\n"
    assert not _novelty_conservation_findings(card, ctx)      # 'uncharacterised' != novelty claim


def test_novelty_silent_without_conservation_data():
    card = "## §2\nMeaningful structural novelty.\n"
    assert not _novelty_conservation_findings(card, {})       # no data -> no false block


def test_novelty_unrelated_denial_does_not_mask_real_claim():
    """CONFIRMED BUG (2026-07-08), fixed: the sentence-level denial guard exempted the WHOLE
    sentence if a denial/contrast cue appeared ANYWHERE in it, so an unrelated negation could
    mask a genuine, unhedged novelty overclaim later in the same sentence. Fix: the denial check
    is now windowed around the matched claim, not sentence-wide."""
    ctx = {"conservation_median_id": 98.0, "conservation_n_genes": 12}
    card = ("## §5 Architecture\nThis is not a housekeeping gene, but the scaffold itself is a "
            "novel, isolate-specific biosynthetic architecture with no known relatives in the "
            "database.\n")
    assert "NOVELTY_CONTRADICTION" in _codes(_novelty_conservation_findings(card, ctx))


def test_novelty_denial_still_exempts_the_four_documented_phrasings():
    """Regression lock for the original v9.7.233 fix (do not let the windowing change above
    reintroduce these false positives): all four phrasings the changelog names must stay clean."""
    ctx = {"conservation_median_id": 98.0, "conservation_n_genes": 12}
    sentences = [
        "Given the conservation, this is not a novel scaffold.",
        "This machinery is not an isolate-specific, unusual one; it is broadly shared.",
        "The cluster reflects a genus-wide backbone rather than a bee-specific locus.",
        "There is no meaningful scaffold-novelty score to report here.",
    ]
    for sent in sentences:
        card = f"## §5 Architecture\n{sent}\n"
        findings = _novelty_conservation_findings(card, ctx)
        assert not findings, f"false positive on documented-clean denial: {sent!r} -> {findings}"


# ---- INTERNAL_CONTRADICTION ----
def test_internal_tta_contradiction():
    card = ("## §15\nThe T4 bldA tier (7 TTA codons in ctg66_8) means production is gated.\n"
            "## §28\nTTA codon count (ctg66_8: 1 TTA).\n")
    assert "INTERNAL_CONTRADICTION" in _codes(_internal_consistency_findings(card))


def test_internal_clean_when_consistent():
    card = "## §15\nctg66_8 carries 1 TTA codon.\n## §28\nTTA count (ctg66_8: 1 TTA).\n"
    assert not _internal_consistency_findings(card)


# ---- FACT_MISMATCH: bind to gene_context ----
def test_fact_mismatch_tta_vs_gene_context():
    ctx = {"tta_by_gene": {"ctg66_8": 1}}
    card = "## §15\n7 TTA codons in ctg66_8.\n"
    assert "FACT_MISMATCH" in _codes(_fact_binding_findings(card, ctx))


def test_fact_ok_when_matches_source():
    ctx = {"tta_by_gene": {"ctg66_8": 1}, "cds_count": 36}
    card = "## §4\nAll 36 CDS.\nctg66_8 carries 1 TTA.\n"
    assert not _fact_binding_findings(card, ctx)


# ---- readiness_state lifecycle ----
def test_readiness_state_transitions():
    clean = []
    blocked = [{"severity": "WARN", "code": "NOVELTY_CONTRADICTION"}]
    err = [{"severity": "ERROR", "code": "MISSING_REQUIRED_SECTION"}]
    assert readiness_state(clean, "FULL") == "EVIDENCE_MATRIX_VALIDATED"
    assert readiness_state(blocked, "FULL") == "STRUCTURE_VALIDATED_WITH_SCIENCE_HOLDS"
    assert readiness_state(clean, "STUB") == "DRAFT"
    assert readiness_state(err, "FULL") == "DRAFT"
