"""T43-PHO §5.1 — catabolic phn genes must not be read as biosynthetic phosphonate signal.

The v9.7.30 redesign removed the carboxyphosphonate/ICL-label false driver, but the SID-XXX verification
showed a residual over-call: the `phosphonate` token still fired on phosphonate CATABOLISM / transport
genes — the phn operon (C-P lyase PhnG-M), alkylphosphonate utilization, ABC transporter. These are
housekeeping phosphorus scavenging, never natural-product C-P bond biosynthesis. They must NOT fire T43-PHO.
Real biosynthetic phosphonate signal must still fire.
"""
import re
import pytest
from mamey.source_scans import CCTT_PATTERNS

PHO0 = CCTT_PATTERNS["T43-PHO_phosphonate"][0]   # the `phosphonate` product/qualifier token


def fires(s):
    return bool(re.search(PHO0, s, flags=re.I))


@pytest.mark.parametrize("s", [
    "alkylphosphonate utilization protein",
    "phosphonate ABC transporter permease",
    "phosphonate ABC transporter ATP-binding protein",
    "phosphonate C-P lyase system protein PhnG",
    "phosphonate C-P lyase system protein PhnH",
    "phosphonate C-P lyase system protein PhnJ",
    "phosphonate C-P lyase system protein PhnK",
    "phosphonate C-P lyase system protein PhnL",
])
def test_catabolic_phn_does_not_fire_t43_pho(s):
    assert not fires(s), f"catabolic phn gene wrongly fired T43-PHO: {s!r}"


@pytest.mark.parametrize("s", [
    "phosphonate",                                  # antiSMASH product class label
    "2-aminoethylphosphonate biosynthesis",
    "phosphonate biosynthesis protein PhpC",
    "phosphonoglycan-associated phosphonate",
])
def test_real_biosynthetic_phosphonate_still_fires(s):
    assert fires(s), f"real biosynthetic phosphonate signal failed to fire: {s!r}"


def test_carboxyphosphonate_still_excluded():
    # the original v9.7.30 driver stays excluded
    assert not fires("carboxyvinyl-carboxyphosphonate synthase")


def test_token_has_no_internal_pipe():
    # internal '|' would be mangled by the registry pipe-join/split round-trip (the bug caught in patch)
    assert "|" not in PHO0
