"""Regression guards for two scan/scoring defects (v9.7.7 patch chat).

BUG 1 — halogenase false positive. The bare regex ``r"halogenase"`` substring-
matches "dehalogenase", so a haloalkane *de*halogenase (a catabolic housekeeping
enzyme) fired the halogenation [E-signal]. Fixed to ``r"(?<!de)halogenase"`` at
every site (source_scans DOMAIN_CLASS/CCTT/CASSETTE patterns + the marker/cassette
mirrors). Matching is case-insensitive (re.I).

BUG 2 — AB/AF inflation. ``score_keywords`` used a bare ``key in text`` substring
test, so (a) "polyene" matched inside "arylpolyene" (a pigment scored as an
antifungal), (b) "t2pks" matched inside "hr-t2pks" (one locus counted twice), and
(c) every nested token stacked. Fixed to delimited-word matching + pigment
exclusion + subclass subsumption.

Standalone:  python3 tests/test_scan_scoring_bugfixes.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.source_scans import DOMAIN_CLASS_PATTERNS, CCTT_PATTERNS, CASSETTE_PATTERNS
from mamey.scoring import score_keywords, AB_KEYWORDS, AF_KEYWORDS


def _all_halogenase_patterns():
    """Every shipped regex in a halogenation-related pattern group."""
    pats = list(DOMAIN_CLASS_PATTERNS.get("Halogenase", []))
    pats += CCTT_PATTERNS.get("T43-HAL_halogenase", [])
    pats += CASSETTE_PATTERNS.get("halogenation", [])
    return pats


def test_dehalogenase_does_not_fire_halogenase():
    """The catabolic dehalogenase family must not trigger any halogenase pattern,
    in any case (re.I) — this is the diagnosed false positive."""
    false_positives = [
        "haloalkane dehalogenase",
        "dehalogenase",
        "DEHALOGENASE",
        "2-haloacid dehalogenase family protein",
        "haloacetate dehalogenase",
    ]
    for txt in false_positives:
        for pat in _all_halogenase_patterns():
            assert re.search(pat, txt, flags=re.I) is None, \
                f"pattern {pat!r} wrongly fired on {txt!r}"


def test_real_halogenase_still_fires():
    """Genuine biosynthetic halogenases (incl. plural and tailored names) must
    still trigger at least one halogenase pattern."""
    true_positives = [
        "halogenase",
        "halogenases",
        "flavin-dependent halogenase",
        "tryptophan 7-halogenase",
        "FADH2-dependent halogenase",
    ]
    pats = _all_halogenase_patterns()
    for txt in true_positives:
        assert any(re.search(p, txt, flags=re.I) for p in pats), \
            f"no halogenase pattern fired on {txt!r}"


def test_scan_patterns_end_to_end_excludes_dehalogenase():
    """Through the real _scan_patterns path: a CDS annotated 'haloalkane
    dehalogenase' yields zero Halogenase hits; 'tryptophan halogenase' yields one."""
    from mamey.source_scans import _scan_patterns
    from mamey.models import CDSFeature
    def cds(product):
        return CDSFeature(contig="c1", start=1, end=900, strand="+",
                          locus_tag="c1_1", product=product)
    neg = _scan_patterns([cds("haloalkane dehalogenase family protein")],
                         {"Halogenase": DOMAIN_CLASS_PATTERNS["Halogenase"]})
    assert neg["counts"]["Halogenase"] == 0
    pos = _scan_patterns([cds("tryptophan halogenase")],
                         {"Halogenase": DOMAIN_CLASS_PATTERNS["Halogenase"]})
    assert pos["counts"]["Halogenase"] == 1


def test_arylpolyene_pigment_not_scored_as_antifungal():
    """Arylpolyene is an APE-type pigment; it must contribute 0 to the AF axis
    (it previously banked 18 via a 'polyene' substring match)."""
    assert score_keywords("arylpolyene", AF_KEYWORDS) == 0.0
    # and a real polyene macrolide still scores
    assert score_keywords("polyene", AF_KEYWORDS) == AF_KEYWORDS["polyene"]


def test_ab_inflation_no_subclass_double_count():
    """A multi-product region must bank each class once. The canonical inflation
    case (arylpolyene + nrps + hr-t2pks + saccharide) must not also count t2pks
    inside hr-t2pks, nor the pigment."""
    text = "arylpolyene nrps hr-t2pks saccharide"
    expected = AB_KEYWORDS["nrps"] + AB_KEYWORDS["hr-t2pks"] + AB_KEYWORDS["saccharide"]
    assert score_keywords(text, AB_KEYWORDS) == float(expected)
    # explicit: t2pks weight must NOT be added on top of hr-t2pks
    assert score_keywords("hr-t2pks", AB_KEYWORDS) == float(AB_KEYWORDS["hr-t2pks"])
    assert score_keywords("transat-pks", AF_KEYWORDS) == float(AF_KEYWORDS["transat-pks"])


def test_delimited_subtypes_still_match():
    """Legitimate hyphen/prefix-delimited subtypes must keep matching their class."""
    assert score_keywords("azole-containing-ripp", AB_KEYWORDS) == float(AB_KEYWORDS["azole"] + AB_KEYWORDS["ripp"])
    assert score_keywords("ni-siderophore", AF_KEYWORDS) == float(AF_KEYWORDS["siderophore"])
    assert score_keywords("nrps-like", AB_KEYWORDS) == float(AB_KEYWORDS["nrps"])


if __name__ == "__main__":
    fns = [test_dehalogenase_does_not_fire_halogenase, test_real_halogenase_still_fires,
           test_scan_patterns_end_to_end_excludes_dehalogenase,
           test_arylpolyene_pigment_not_scored_as_antifungal,
           test_ab_inflation_no_subclass_double_count, test_delimited_subtypes_still_match]
    passed = 0
    for fn in fns:
        try:
            fn(); passed += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{passed}/{len(fns)} passed")


# ── BH-005 / BH-010 (v9.7.122) — token-split membership tests ──────────────────
# Two bare-substring membership tests over a joined product string were splitting
# words mid-token: "thioamide" matched inside "thioamide-NRP" (scan_umed), and
# "furan" matched inside "furanomycin" (QS labels). Both now token-split first.

def _umed_needs_maturation(product_text: str) -> bool:
    toks = {t.strip() for t in re.split(r"[;,/|]+|\s+", product_text.lower()) if t.strip()}
    return any(x in toks for x in ["ripp", "lanthipeptide", "lassopeptide", "thioamide", "azole", "nucleoside"])


def test_bh005_thioamide_nrp_not_maturation_gated():
    # thioamide-NRP has its own assembly-line logic, not RiPP-style maturation
    assert _umed_needs_maturation("thioamide-NRP") is False
    assert _umed_needs_maturation("nucleoside-sugar") is False


def test_bh005_true_positives_preserved():
    assert _umed_needs_maturation("thioamide") is True
    assert _umed_needs_maturation("RiPP; azole-containing-RiPP") is True   # 'ripp' token
    assert _umed_needs_maturation("lanthipeptide") is True


def _is_qs(product_text: str) -> bool:
    from mamey.source_scans import QS_PRODUCT_LABELS
    toks = {t.strip() for t in re.split(r"[;,/|]+|\s+", product_text.lower()) if t.strip()}
    return any(label in toks for label in QS_PRODUCT_LABELS)


def test_bh010_furanomycin_not_qs():
    # furanomycin / furopyridine are PKS classes, not quorum-sensing signals
    assert _is_qs("furanomycin") is False


def test_bh010_qs_true_positives_preserved():
    assert _is_qs("furan") is True
    assert _is_qs("butyrolactone") is True
    assert _is_qs("furan; bdsf") is True
