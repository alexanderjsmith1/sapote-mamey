"""Affiliation guard.

Confirms the institutional affiliation has been removed from CITATION.cff per
operator decision 2026-07-12: the bundle identifies as "Sapote-Mamey" plus the
version number only. This guard prevents re-introduction. Author names (including
the Developer or User) are unaffected and remain.
"""
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_citation_cff_has_no_institutional_affiliation():
    cff = ROOT / "CITATION.cff"
    assert cff.exists(), "CITATION.cff missing"
    text = cff.read_text(encoding="utf-8")
    assert "the source institution" not in text, "CITATION.cff must not name the source institution (affiliation removed)"
    assert "the source lab" not in text, "CITATION.cff must not name the source lab (affiliation removed)"
