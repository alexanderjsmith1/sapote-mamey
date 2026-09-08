"""BLACK_CHERRY wave 19 — case-sensitivity false negative in bgc_citation_gate.py.

`_BGC_RE` was compiled without re.I, so a node-less citation written as `bgc016` or `Bgc016`
(lowercase/mixed-case BGC label — plausible in hand-typed Mode B prose, which is exactly what
this gate exists to catch) silently bypasses the gate entirely: it is never even recognized as
a BGC citation, so the fail-closed check never fires. This is the dangerous direction (a real
unsafe node-less citation is NOT flagged) for the exact WAC-01375 failure class the gate's own
docstring describes.

Also pins that the count-phrase claim in the docstring/comment ("Count phrases … never trip")
still holds after the case-insensitivity fix — lowercasing must not turn "bgcs" (no digit) into
a false-positive BGC-label match.
"""
from mamey.bgc_citation_gate import find_nodeless_bgc_citations as f


def test_lowercase_bgc_label_is_flagged():
    assert f("atratumycin (AS-162 bgc011), AB 94") != []


def test_mixed_case_bgc_label_is_flagged():
    assert f("AS-162 Bgc016 mentioned here, no node token") != []


def test_uppercase_bgc_label_still_flagged():
    assert f("atratumycin (AS-162 BGC011), AB 94") != []


def test_lowercase_node_region_form_still_clean():
    good = "as-162 / node_35_length_72712_cov_100.179280 / region001 / bgc016 — atratumycin-family"
    assert f(good) == []


def test_lowercase_count_phrase_still_does_not_trip():
    assert f("as-385 has 37 bgcs total; 30 are real bgcs after dedup.") == []
