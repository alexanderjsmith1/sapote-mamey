from mamey.class_architecture import product_family,with_family_labels
from mamey.p450_tailoring import _scaffold_of
from mamey.scoring import standing_rule_for
from mamey.dualpass_ledger import load_vocab,normalize_value
import pytest

@pytest.mark.parametrize("label",["redox-cofactor","redox_cofactor"])
def test_redox_family_is_ripp(label):
    assert product_family(label)=="ripp"
    assert _scaffold_of(label)=="RiPP"

@pytest.mark.parametrize("label",["quinone_isoprenoid_chain","quinone-isoprenoid-chain"])
def test_quinone_family_is_terpene(label):
    assert product_family(label)=="terpene"

def test_standing_rule_preserves_equivalent_redox_labels():
    a=standing_rule_for("redox-cofactor;saccharide","redox-cofactor;saccharide")
    b=standing_rule_for("redox_cofactor;saccharide","redox_cofactor;saccharide")
    assert a and b==a

def test_ledger_enum_was_already_normalized_and_stays_stable():
    v=load_vocab();assert normalize_value("ripp_subclass","redox-cofactor",v)==normalize_value("ripp_subclass","redox_cofactor",v)=="redox_cofactor"
