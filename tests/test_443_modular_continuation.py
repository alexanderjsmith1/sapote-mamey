"""MODULAR_CONTINUATION: module-aware reading of an RG-GMCI pair, reported beside functional_rescue_class."""
from mamey.clusterblast_genes import (modular_continuation, modular_profile_from_gene_context,
                                      rescue_functional_complementarity, functional_profile_from_gene_context)


def cds(*doms, kind="biosynthetic"):
    return {"sec_met_domains": list(doms), "gene_kind": kind, "gene_functions": "", "product": ""}


# one NRPS line in pieces: modules on both fragments, a single thioesterase between them
PIECE_A = [cds("Condensation", "AMP-binding", "PCP"), cds("Condensation", "AMP-binding", "PCP")]
PIECE_B = [cds("Condensation", "AMP-binding", "PCP"), cds("Thioesterase")]
# two complete lines: each fragment has its own release domain
LINE_1 = [cds("PKS_KS", "PKS_AT", "ACP"), cds("Thioesterase")]
LINE_2 = [cds("PKS_KS", "PKS_AT", "ACP"), cds("Thioesterase")]
TERPENE = [cds("Terpene_synth"), cds("p450", kind="biosynthetic-additional")]


def prof(**frags):
    return modular_profile_from_gene_context(frags)


def test_line_in_pieces_is_modular_continuation():
    p = prof(A=PIECE_A, B=PIECE_B)
    r = modular_continuation(p["A"], p["B"])
    assert r["modular_continuation"] == "MODULAR_CONTINUATION"
    assert (r["a_assembly_line_cds"], r["b_release_cds"]) == (2, 1)


def test_two_complete_lines_are_not_a_continuation():
    p = prof(A=LINE_1, B=LINE_2)
    assert modular_continuation(p["A"], p["B"])["modular_continuation"] == "MODULAR_TWO_RELEASES"


def test_non_modular_partner():
    p = prof(A=PIECE_A, B=TERPENE)
    assert modular_continuation(p["A"], p["B"])["modular_continuation"] == "NOT_MODULAR"


def test_missing_profile():
    assert modular_continuation(None, {"assembly_line_cds": 1})["modular_continuation"] == "UNKNOWN_NO_PROFILE"


def test_the_existing_class_is_unchanged_and_misses_this_shape():
    # the reason for the new column: core-fraction reads both module-only pieces as core-rich
    f = functional_profile_from_gene_context({"A": PIECE_A, "B": PIECE_B})
    assert rescue_functional_complementarity(f["A"], f["B"])["functional_rescue_class"] != "COMPLEMENTARY"
