"""KS module placement refuses duplicate tip labels and malformed trees before counting tips (P300-091)."""
import pytest

from mamey import ks_phylogeny as kp


def test_repeated_query_label_is_refused_not_collapsed():
    # Three query sequences share one label beside one reference KS. Collapsed to a set they would
    # count as one query and read as PLACED; three distinct sequences there are a module family.
    tree = "((q1:0.1,q1:0.1,q1:0.1,MIBiG__R_KS01:0.1)99:0.1,(a:0.1,b:0.1)99:0.1,MIBiG__R_KS02:0.1);"
    with pytest.raises(ValueError, match="duplicate tip labels"):
        kp.place_on_reference_modules(tree)


def test_repeated_reference_label_is_refused():
    tree = "((q1:0.1,MIBiG__R_KS01:0.1)99:0.1,(q2:0.1,MIBiG__R_KS01:0.1)99:0.1,x:0.1);"
    with pytest.raises(ValueError, match="duplicate tip labels"):
        kp.place_on_reference_modules(tree)


def test_blank_tip_label_is_refused():
    with pytest.raises(ValueError, match="blank label"):
        kp.place_on_reference_modules("((q1:0.1,MIBiG__R_KS01:0.1)99:0.1,:0.1,x:0.1);")


@pytest.mark.parametrize("tree", [
    "((q1:0.1,MIBiG__R_KS01:0.1)99:0.1,x:0.1,y:0.1)",          # truncated: no closing ';'
    "((q1:0.1,MIBiG__R_KS01:0.1)99:0.1,x:0.1,y:0.1;",          # unbalanced '('
    "((q1:0.1,MIBiG__R_KS01:0.1)99:0.1,x:0.1,y:0.1));",        # unbalanced ')'
    "((q1:0.1,MIBiG__R_KS01:0.1)99:0.1,x:0.1,y:0.1);(a,b);",   # a second tree after ';'
    "(('q1:0.1,MIBiG__R_KS01:0.1)99:0.1,x:0.1,y:0.1);",        # unterminated quote
])
def test_malformed_tree_is_refused(tree):
    with pytest.raises(ValueError, match="malformed Newick"):
        kp.place_on_reference_modules(tree)


def test_valid_tree_still_places():
    tree = "(('iso__NODE_1__region001__t1__ks1':0.1,MIBiG__R_KS07:0.1)95.3/100:0.2,x:0.1,y:0.2);\n"
    rows = {r["query"]: r for r in kp.place_on_reference_modules(tree)}
    assert rows["iso__NODE_1__region001__t1__ks1"]["verdict"] == kp.PLACED
    assert rows["iso__NODE_1__region001__t1__ks1"]["module"] == 7
