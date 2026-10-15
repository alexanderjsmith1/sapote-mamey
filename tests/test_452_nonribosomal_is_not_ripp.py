"""'nonribosomal' does not add a RiPP class token in the MIBiG per-gene concordance."""
from mamey.mibig_per_gene import _class_concordance, _class_tokens


def test_nonribosomal_gives_nrps_only():
    assert _class_tokens("Nonribosomal peptide") == {"NRPS"}
    assert _class_tokens("non-ribosomal peptide") == {"NRPS"}


def test_nrps_query_against_ripp_reference_is_discordant():
    assert _class_concordance("NRPS", "RiPP") == "DISCORDANT"
    assert _class_concordance("nonribosomal peptide", "ribosomally synthesized RiPP") == "DISCORDANT"


def test_real_ripp_and_hybrid_labels_still_match():
    assert _class_tokens("lanthipeptide-class-i") == {"RiPP"}
    assert _class_tokens("NRPS,lassopeptide") == {"NRPS", "RiPP"}
    assert _class_concordance("ribosomal peptide", "RiPP:Lanthipeptide") == "CONCORDANT"
