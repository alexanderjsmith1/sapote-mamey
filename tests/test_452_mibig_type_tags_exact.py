"""'Polyketide:Type I' does not shadow the Type II and Type III MIBiG class tags."""
from mamey import architecture_first as af


def _lookup(text):
    return next((t for k, t in af.MIBIG_CLASS_MAP.items() if af._mibig_tag_present(k, text)), None)


def test_roman_numeral_types_map_to_their_own_class():
    assert _lookup("Polyketide:Type I") is af.PathwayType.CIS_AT_PKS
    assert _lookup("Polyketide:Type II") is af.PathwayType.T2PKS
    assert _lookup("Polyketide:Type III") is af.PathwayType.T3PKS
    assert _lookup("Polyketide:Iterative type I") is af.PathwayType.CIS_AT_PKS


def test_whole_tag_match_is_case_insensitive_and_allows_lists():
    assert _lookup("polyketide:type ii, NRP") is af.PathwayType.T2PKS
    assert _lookup("NRP:Glycopeptide") is af.PathwayType.NRPS
    assert af._mibig_tag_present("Polyketide:Type I", "Polyketide:Type II") is False
