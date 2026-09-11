"""Tests for the Diagnostic Rescue layer gates (synthetic inputs — no private strain data)."""
from mamey import diagnostic_rescue as DR


def _pair(edge_a="Edge", edge_b="Full-contig", prod_a="halogenated; saccharide", prod_b="indole"):
    return {"pair": "BGC001+BGC013", "bgc_a": "BGC001", "bgc_b": "BGC013",
            "contig_a": "NODE_105", "contig_b": "NODE_182",
            "products_a": prod_a, "products_b": prod_b, "edge_a": edge_a, "edge_b": edge_b,
            "rggmci_confidence": "LOW_SHARED_REFERENCE_SIGNAL", "acceptance_gate": "DEMOTED_TO_LOW"}


# cctt: BGC001 = halogenase arm, BGC013 = IDC core
CCTT_A = ["T43-HAL_halogenase"]
CCTT_B = ["T43-IDC_indolocarbazole"]
TILING = {"best_scaffold": "NZ_KB913036", "covered": 8, "overlap": 0, "genes_a": 2, "genes_b": 6,
          "overlap_fraction": 0.0, "verdict": "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY",
          "ref_source": "Salinispora arenicola"}
# both KCB to indolocarbazoles -> concordant
FMAP = {"by_accession": {"BGC0000809": "indolocarbazole", "BGC0002460": "indolocarbazole",
                         "BGC0002381": "tambjamine"}, "compatible_pairs": []}
KCB_A = "BGC0002460.3 | loonamycin"          # indolocarbazole
KCB_B = "BGC0000809.3 | AT2433-A1"           # indolocarbazole
KCB_B_DISCORDANT = "BGC0002381.3 | tambjamine"


def test_roles_core_and_arm():
    r_arm = DR.roles(CCTT_A, "halogenated; saccharide")
    r_core = DR.roles(CCTT_B, "indole")
    assert r_arm["hal_trigger"] is True and "halogenase" in r_arm["arms"]
    assert r_core["cores"] == ["T43-IDC"]


def test_saccharide_only_is_not_diagnostic_arm():
    r = DR.roles([], "saccharide")
    assert r["saccharide_only"] is True and r["hal_trigger"] is False


def test_edge_gate_drops_interior_pairs():
    # an Interior (complete) member is not a fragment -> not a rescue candidate
    lead = DR.assess_pair(_pair(edge_a="Interior"), CCTT_A, CCTT_B, deep_tiling=TILING,
                          kcb_a=KCB_A, kcb_b=KCB_B, family_map=FMAP)
    assert lead is None


def test_concordant_pair_is_high():
    lead = DR.assess_pair(_pair(), CCTT_A, CCTT_B, deep_tiling=TILING,
                          kcb_a=KCB_A, kcb_b=KCB_B, family_map=FMAP)
    assert lead["rescue_tier"] == "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"
    assert lead["kcb_concordance"] == "concordant"
    assert lead["reference_genes_covered"] == 8 and lead["reference_gene_overlap"] == 0


def test_discordant_pair_demoted_from_high():
    lead = DR.assess_pair(_pair(), CCTT_A, CCTT_B, deep_tiling=TILING,
                          kcb_a=KCB_A, kcb_b=KCB_B_DISCORDANT, family_map=FMAP)
    assert lead["rescue_tier"] != "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"
    assert lead["kcb_concordance"] == "discordant"


def test_unknown_family_capped_at_moderate():
    lead = DR.assess_pair(_pair(), CCTT_A, CCTT_B, deep_tiling=TILING,
                          kcb_a=KCB_A, kcb_b="GenericGenome no accession", family_map=FMAP)
    assert lead["rescue_tier"] == "DIAGNOSTIC_RESCUE_MODERATE"
    assert lead["kcb_concordance"] == "indeterminate"


def test_claim_ceiling_present_on_every_lead():
    lead = DR.assess_pair(_pair(), CCTT_A, CCTT_B, deep_tiling=TILING,
                          kcb_a=KCB_A, kcb_b=KCB_B, family_map=FMAP)
    assert "reconstruction hypothesis" in lead["claim_ceiling"].lower()
    assert "not a nucleotide-level contig join" in lead["claim_ceiling"].lower()


def test_no_concordance_gate_when_family_map_absent():
    # backward-compat: without a family map the concordant geometry pair stays HIGH
    lead = DR.assess_pair(_pair(), CCTT_A, CCTT_B, deep_tiling=TILING,
                          kcb_a=KCB_A, kcb_b=KCB_B, family_map=None)
    assert lead["rescue_tier"] == "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"
    assert lead["kcb_concordance"] == "not_evaluated"


def test_below_covered_floor_not_high():
    weak = dict(TILING, covered=4, genes_a=2, genes_b=2)
    lead = DR.assess_pair(_pair(), CCTT_A, CCTT_B, deep_tiling=weak,
                          kcb_a=KCB_A, kcb_b=KCB_B, family_map=FMAP)
    assert lead["rescue_tier"] != "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"
