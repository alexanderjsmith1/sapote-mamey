"""mamey.domain_reference.categorize: a dehalogenase is a hydrolase, not a halogenase."""
from mamey import domain_reference as DR


def test_dehalogenase_names_are_hydrolases():
    assert DR.categorize("", "haloalkane dehalogenase")[0] == "tailoring-other"
    assert DR.categorize("Dehalogenase")[0] == "tailoring-other"
    assert DR.categorize("SMCOG1262", "haloalkane dehalogenase")[0] == "tailoring-other"


def test_halogenases_stay_in_halogenation():
    for name, desc in (("Trp_halogenase", ""), ("", "halogenase"), ("some_halogenase", ""), ("", "flavin-dependent halogenase")):
        assert DR.categorize(name, desc)[0] == "tailoring-halogenation", (name, desc)
