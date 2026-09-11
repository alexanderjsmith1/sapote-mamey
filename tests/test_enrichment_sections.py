"""Tests for mamey.enrichment_sections — deterministic §11–§20 enrichment generators."""
from mamey.enrichment_sections import (
    Gene, genome_domain_frequency, compose_enrichment,
    emit_rarest_domains, emit_rarest_genes, emit_domain_inventory,
    emit_peptide_precursor, _RIPP_PRECURSOR_KEYS,
)


def _g(locus, doms, aa=300):
    return Gene(locus, tuple(doms), aa)


def test_catchalls_clear_floor_on_small_cluster():
    """A 6-gene cluster reaches the 1,000c enrichment floor from catch-alls alone."""
    genes = [_g(f"ctg1_{i}", [d]) for i, d in enumerate(
        ["AfsA", "MerR_1", "FMO-like", "NDK", "NAD_binding_4", "PP-binding"], 1)]
    freq = genome_domain_frequency({"BGC001": genes})
    text, used = compose_enrichment(genes, freq, "", floor=1000)
    assert len(text) >= 1000
    assert "rarest_domains" in used or "domain_inventory" in used


def test_single_gene_fragment_enrichment_is_honest_not_padded():
    """A single-domain-gene fragment generates what it honestly can; the generators do NOT
    fabricate to hit 1,000c. (Such fragments are STUB-exempt from the floor at the gate level —
    the gate's sub-2,000-char STUB branch short-circuits before the enrichment check.)"""
    genes = [_g("ctg9_1", ["Halogenase"], aa=520)]
    freq = genome_domain_frequency({"BGC099": genes})
    text, used = compose_enrichment(genes, freq, "", floor=1000)
    # It uses every applicable section (incl. halogenase subtyping) and reports real content,
    # but does not pad — a 1-gene fragment legitimately may not reach 1,000c.
    assert "halogenase_subtyping" in used
    assert len(text) > 0 and "fabricat" not in text.lower()


def test_rarest_is_genome_grounded():
    """A genome-unique domain is surfaced as a singleton; a common one is not 'rarest'."""
    common = [_g(f"ctgC_{i}", ["Condensation"]) for i in range(10)]
    rare = [_g("ctgR_1", ["CorA"])]
    freq = genome_domain_frequency({"BGCcommon": common, "BGCrare": rare})
    out = emit_rarest_domains(rare, freq)
    assert "CorA" in out
    assert "singleton" in out.lower()


def test_thio_key_does_not_false_match_thioesterase():
    """Regression (Patch Chat v9.7.112): 'thio' must not fire RiPP-precursor on Thioesterase/Thioredoxin."""
    # The keys themselves must not contain a bare 'thio' substring trigger
    assert "thio" not in _RIPP_PRECURSOR_KEYS
    assert "thiopeptide" in _RIPP_PRECURSOR_KEYS
    # A cluster whose only 'thio' content is a thioesterase must NOT be called RiPP-precursor-bearing
    genes = [_g("ctg1_1", ["Thioesterase"]), _g("ctg1_2", ["Condensation"])]
    out = emit_peptide_precursor(genes, products="NRPS")
    assert "RiPP-maturation" not in out  # no false RiPP claim


def test_peptide_precursor_fires_on_real_ripp():
    """A genuine lanthipeptide cluster does fire the precursor scan."""
    genes = [_g("ctg1_1", ["LanC"], aa=400), _g("ctg1_2_lanthipeptide", ["leader"], aa=55)]
    out = emit_peptide_precursor(genes, products="lanthipeptide")
    assert out  # non-empty
    assert "precursor" in out.lower()


def test_composer_does_not_drop_rare_present_sections():
    """Regression (v9.7.114): a distinctive section (halogenase) must not be dropped just because
    earlier generic sections already cleared the floor. Rare-but-present is ordered before fillers."""
    # A cluster with a halogenase plus enough generic content that earlier sections clear the floor.
    genes = [_g(f"ctgX_{i}", ["Condensation"]) for i in range(8)]
    genes += [_g("ctgX_hal", ["Trp_halogenase"], aa=520)]
    freq = genome_domain_frequency({"BGC001": genes})
    text, used = compose_enrichment(genes, freq, "NRPS", floor=1000)
    assert "halogenase_subtyping" in used, "halogenase section was dropped despite being present"
