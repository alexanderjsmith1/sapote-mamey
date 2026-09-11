"""Regression test for `mamey/bgc_citation_gate.py::_NODE_RE` (v9.7.401, BC2, `.401` round
tick 12).

`_NODE_RE`'s last alternative was a bare `\\bcontig\\b` -- it matched the generic NOUN "contig"
with no accompanying number, so a decoy line that merely mentions the word ("BGC016 is on a
contig, exact node still needs to be checked") satisfied the "has a locating token" check and
was never reported. That is the exact WAC-01375 defect class this gate exists to mechanically
catch -- a strain+BGC citation with no actual locating value -- wearing a disguise: the line
LOOKS like it references assembly-level context, but names no specific node/contig/region ID.

Checked the full shipped corpus (every tracked `.md` file) for lines that currently rely on the
bare contig-word alternative to stay unflagged: zero found, so this tightening introduces no
known regression against real content.
"""
from mamey.bgc_citation_gate import find_nodeless_bgc_citations as f


def test_bare_contig_word_decoy_is_now_caught():
    """The actual regression this fix closes: a strain+BGC line that merely mentions the word
    'contig' with no actual locating value must be flagged, not waved through."""
    decoy = "AS-001 / BGC016 is on a contig, exact node still needs to be checked."
    hits = f(decoy)
    assert hits, "a bare mention of 'contig' with no number must not satisfy the node/region check"
    assert hits[0][1] == decoy


def test_genuinely_nodeless_citation_still_caught():
    assert f("AS-001 / BGC016 produces a capacity-level hit.")


def test_legit_node_citation_stays_clean():
    good = "AS-001 / NODE_35_length_128744_cov_42.1 / region001 / BGC016"
    assert f(good) == []


def test_legit_ctg_citation_stays_clean():
    assert f("AS-001 BGC016 driven by ctg35_27 (thioamide-NRPS)") == []


def test_legit_region_citation_stays_clean():
    assert f("AS-001 / region003 / BGC016") == []


def test_numbered_contig_citations_still_stay_clean():
    """No regression: 'contig' paired with an actual number, in any of the common spacing
    conventions, must still count as a real locating token."""
    for line in (
        "AS-001 / contig_12 / BGC016",
        "AS-001 / contig 12 / BGC016",
        "AS-001 / contig12 / BGC016",
        "AS-001 / contig-12 / BGC016",
    ):
        assert f(line) == [], line


def test_count_phrases_still_do_not_trip():
    assert f("AS-001 has 37 BGCs total; 30 are real BGCs after dedup.") == []
