"""H3-followup: per-BGC -cidal/-static phenotype claims must flag.

Hostile audit of the shipped H3 bioactivity_phenotype check found a false-negative:
the regex matched antibacterial/antifungal/... but not bactericidal/fungicidal/
bacteriostatic/fungistatic — so "BGC is bactericidal against S. aureus" (a per-BGC
phenotype claim) slipped through clean. These terms are now covered; exemptions
(extract-level / negated / capacity / hedged) still apply.
"""
import tools.claim_safety_linter as L


def _decide(s: str) -> str:
    for m in L._BIOACTIVITY_RE.finditer(s):
        c = s.lower()
        if L._NEGATION_RX.search(c):
            return "exempt"
        if any(f in c for f in L._CAPACITY_FRAME):
            return "exempt"
        if L._HEDGE_RX.search(c):
            return "exempt"
        if any(h in c for h in L._EXTRACT_LEVEL_HINTS):
            return "exempt"
        return "FLAG"
    return "no-match"


def test_cidal_static_phenotype_flags():
    assert _decide("This cluster is bactericidal against S. aureus") == "FLAG"
    assert _decide("BGC is fungicidal toward Candida") == "FLAG"
    assert _decide("BGC shows bacteriostatic action") == "FLAG"
    assert _decide("The region is fungistatic") == "FLAG"


def test_cidal_static_exemptions_still_apply():
    assert _decide("The crude extract is bactericidal") == "exempt"        # extract-level
    assert _decide("BGC003 does not appear bactericidal") == "exempt"      # negated
    assert _decide("may be fungicidal") == "exempt"                        # hedged
