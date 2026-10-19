"""COMP-P01/P02: gcf-network strain match must be token-anchored, not a bare substring.

Real-data motivation: the AS+Type+SID cohort has both AS-74 and AS-747, so a `%AS-74%`
substring match pulled AS-747's 44 regions into AS-74's figure.
"""
from mamey.bigscape_figures import _strain_token_match as m


def test_no_bleed_prefix_strain():
    # Fabricated shared-prefix pair: the shorter token must not match its extension.
    assert m("SYNTHETIC-CASE-021_NODE_5_length_1000.region001.gbk", "SYNTHETIC-CASE-021") is True
    assert m("SYNTHETIC-CASE-0210_NODE_9_length_2000.region001.gbk", "SYNTHETIC-CASE-021") is False


def test_longer_strain_matches_its_own():
    assert m("SYNTHETIC-CASE-0210_NODE_9_length_2000.region001.gbk", "SYNTHETIC-CASE-0210") is True


def test_token_embedded_in_longer_prefix():
    # SID token inside a long underscored stem still matches
    assert m("Streptomyces_sp._SID8374_GCA_009865135.1_WWGH01000001.1.region013.gbk", "SID8374") is True


def test_spaced_strain_name():
    assert m("Actinomadura citrea DSM 43461_NZ_XXXX.1.region006.gbk", "Actinomadura citrea DSM 43461") is True


def test_unrelated_strain_rejected():
    assert m("SYNTHETIC-CASE-005_NODE_2_length_3.region001.gbk", "SYNTHETIC-CASE-012") is False


def test_fabricated_prefix_pair_exercises_substring_counterexample():
    short, longer = "SYNTHETIC-CASE-021", "SYNTHETIC-CASE-0210"
    filename = longer + "_NODE_9_length_2000.region001.gbk"
    assert longer.startswith(short) and short in filename
    assert m(filename, short) is False
    assert m(filename, longer) is True
