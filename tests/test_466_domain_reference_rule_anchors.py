"""mamey.domain_reference.categorize: transport, efflux, CBM, Cy_ and IPP rules (Codex T05 examples)."""
from mamey import domain_reference as DR


def cat(name, desc=""):
    return DR.categorize(name, desc)[0]


def test_sugar_transporters_are_transport_not_glycosylation():
    assert cat("SMCOG1169: sugar transport protein") == "transport"
    assert cat("Sugar_tr") == "transport"
    # sugar-tailoring names keep their rule
    assert cat("SMCOG1146: sugar transferase") == "tailoring-glycosylation"
    assert cat("dTDP_sugar_isom") == "tailoring-glycosylation"
    assert cat("SMCOG1152: nucleotide sugar dehydrogenase") == "tailoring-oxidoreduction"


def test_efflux_alone_is_transport_and_resistance_names_stay():
    assert cat("SMCOG1116: Homoserine/threonine efflux protein") == "transport"
    assert cat("Cation_efflux") == "transport"
    assert cat("SMCOG1086: MATE efflux family protein") == "transport"
    assert cat("LysE") == "transport" and cat("MatE") == "transport"
    assert cat("SMCOG1005: Drug resistance transporter, EmrB/QacA") == "resistance"
    assert cat("", "multidrug resistance efflux pump") == "resistance"
    assert cat("Beta-lactamase") == "resistance"


def test_cbm_is_a_binding_module_not_a_hydrolase():
    for d in ("CBM_2", "CBM_48", "CBM9_1", "NPCBM", "NPCBM_assoc"):
        assert cat(d) == "other", d
    assert DR.categorize("CBM_2")[1].startswith("Carbohydrate-binding module")
    assert cat("Abhydrolase_1") == "tailoring-other" and cat("Alpha-amylase") == "tailoring-other"


def test_cy_and_ipp_are_anchored():
    assert cat("Ad_Cy_reg") == "other"
    assert cat("Condensation_LCL") == "NRPS-core" and cat("Cy_tandem") == "NRPS-core"
    assert cat("IPPT") == "terpene/prenyl" and cat("", "IPP isomerase") == "terpene/prenyl"
    assert cat("XIPPZ") == "other"


def test_earlier_rules_unchanged():
    assert cat("SMCOG1262", "haloalkane dehalogenase") == "tailoring-other"
    assert cat("Trp_halogenase") == "tailoring-halogenation"
    assert cat("SMCOG1000: ABC transporter ATP-binding protein") == "transport"
    assert cat("TetR_N") == "regulatory"
