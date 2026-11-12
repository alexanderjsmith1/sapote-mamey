"""cohort_enzyme_catalog.classify: halogenation is decided by the halogenation domain."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import cohort_enzyme_catalog as cec  # noqa: E402

NAMES = {"SMCOG1119": "halogenase", "SMCOG1246": "monooxygenase FAD-binding"}


def call(smcog, doms):
    gf = f"biosynthetic-additional (smcogs) {smcog} (E-value: 1e-90, bitscore: 300, seeds: 1)" if smcog else ""
    return cec.classify(dict(gene_functions=gf, sec_met_domains=doms), NAMES)


def test_trp_halogenase_domain_beats_fad_monooxygenase_label():
    # AS-441 ctg36_45, AS-200 ctg59_29, AS-701 ctg35_15 pattern
    fam, cat_, _ = call("SMCOG1246: monooxygenase FAD-binding", ["Trp_halogenase"])
    assert cat_ == "tailoring-halogenation" and fam.startswith("SMCOG1246")


def test_halogenase_label_without_domain_is_oxidoreduction():
    # AS-162 ctg12_103 (no domain), AS-441 ctg47_5 (NAD_binding_8 only)
    assert call("SMCOG1119: halogenase", [])[1] == "tailoring-oxidoreduction"
    assert call("SMCOG1119: halogenase", ["NAD_binding_8"])[1] == "tailoring-oxidoreduction"
    # the 24 SMCOG1119 genes with FAD_binding_3 stay oxidoreduction
    assert call("SMCOG1119: halogenase", ["FAD_binding_3"])[1] == "tailoring-oxidoreduction"


def test_label_and_domain_agreeing_and_earlier_cores_unchanged():
    assert call("SMCOG1119: halogenase", ["Trp_halogenase"])[1] == "tailoring-halogenation"
    assert call("SMCOG1119: halogenase", ["Trp_halogenase", "FAD_binding_3"])[1] == "tailoring-halogenation"
    assert call("", ["Trp_halogenase", "PKS_KS"])[1] == "PKS-core"
    assert call("SMCOG1246: monooxygenase FAD-binding", ["FAD_binding_3"])[1] == "tailoring-oxidoreduction"
