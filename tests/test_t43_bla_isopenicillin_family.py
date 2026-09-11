"""A4: T43-BLA must not fire on an 'isopenicillin N synthase FAMILY oxygenase'.

The IPNS fold is a widespread non-heme-iron / 2OG oxygenase family; a fold-family homolog (annotated
'... synthase family oxygenase') is a tailoring oxygenase, not a committed beta-lactam enzyme. The bare
`isopenicillin` token matched these and fired T43-BLA on a terpene locus (SID-XXX BGC003). The token now
requires a committed 'isopenicillin N synthase' and excludes the 'family' homolog form.
"""
import re
from mamey.source_scans import CCTT_PATTERNS

BLA = CCTT_PATTERNS["T43-BLA_betalactam"]

def _fires(text):
    return any(re.search(p, text, re.I) for p in BLA)

def test_family_oxygenase_does_not_fire():
    assert not _fires("isopenicillin N synthase family oxygenase")
    assert not _fires("Isopenicillin N synthase family protein")
    # newline-wrapped /product (GenBank continuation) must also be excluded
    assert not _fires("isopenicillin N synthase\n          family oxygenase")

def test_committed_ipns_still_fires():
    assert _fires("isopenicillin N synthase")
    assert _fires("isopenicillin N synthase (pcbC)")

def test_other_betalactam_markers_unaffected():
    assert _fires("ACV synthetase")
    assert _fires("nocardicin")
    assert _fires("clavaminate synthase")
