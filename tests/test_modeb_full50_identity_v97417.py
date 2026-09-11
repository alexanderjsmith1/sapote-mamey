"""Guards for mamey.modeb_full50_contract -- the canonical-contract identity helper.

The four 50-section consumers take their contract from an operator-supplied path pinned by a
sha256 the same config supplies, so a passing pin proves the file has not changed since that
config was written, not WHICH contract it is.  This helper makes the difference reportable.

These guards check that it actually distinguishes -- including against the exact synthetic
contract shape the existing consumer fixtures use, which must classify as NON_CANONICAL
rather than being mistaken for the project's contract.
"""

import json
from pathlib import Path

import pytest

from mamey import modeb_full50_contract as m

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "MODEB_50_SECTION_CONTRACT_CANDIDATE.md"

# The shape tests/test_evidence_disagreements.py writes for its fixture.
FIXTURE_TEXT = "\n".join(
    f"| {n} | Generic fixture requirement {n} |" for n in range(1, 51)
)


def test_canonical_contract_resolves_from_the_bundle():
    assert m.CONTRACT_PATH.is_file(), f"missing frozen contract {m.CONTRACT_PATH}"
    c = m.canonical_contract()
    assert c["schema_version"] == "modeb_current50_v1"
    assert c["section_count"] == 50


def test_canonical_requirements_are_the_fifty_sections():
    req = m.canonical_requirements()
    assert sorted(req) == list(range(1, 51))
    assert all(v.strip() for v in req.values())


def test_recorded_source_hash_matches_the_document_on_disk():
    import hashlib
    assert m.canonical_sha256() == hashlib.sha256(DOC.read_bytes()).hexdigest()


def test_parse_matches_the_consumers_own_expression():
    """The helper must parse the source document to exactly the canonical rows."""
    assert m.parse_requirements(DOC.read_text(encoding="utf-8")) == m.canonical_requirements()


def test_the_project_contract_identifies_as_canonical():
    r = m.identify(DOC.read_text(encoding="utf-8"))
    assert r["state"] == m.CANONICAL
    assert r["differing_sections"] == []
    assert r["canonical_source_sha256"] == m.canonical_sha256()


def test_a_generic_fifty_row_fixture_is_not_mistaken_for_the_contract():
    """This is the whole point: the fixture satisfies every existing consumer check."""
    r = m.identify(FIXTURE_TEXT)
    assert r["state"] == m.NON_CANONICAL
    assert len(r["differing_sections"]) == 50


def test_one_edited_row_is_detected():
    req = m.canonical_requirements()
    req[27] = req[27] + " (edited)"
    r = m.identify(req)
    assert r["state"] == m.NON_CANONICAL
    assert r["differing_sections"] == [27]


@pytest.mark.parametrize("drop", [1, 27, 50])
def test_a_missing_section_is_malformed_not_merely_different(drop):
    req = m.canonical_requirements()
    del req[drop]
    r = m.identify(req)
    assert r["state"] == m.MALFORMED
    assert r["missing"] == [drop]


def test_an_extra_section_is_malformed():
    req = m.canonical_requirements()
    req[51] = "an extra section"
    r = m.identify(req)
    assert r["state"] == m.MALFORMED
    assert r["unexpected"] == [51]


def test_identify_never_raises_on_contract_content():
    """Policy belongs at the call site; this helper reports, it does not block."""
    for bad in ["", "not a contract at all", "| 1 | only one row |"]:
        assert m.identify(bad)["state"] == m.MALFORMED


def test_helper_emits_nothing_to_the_terminal():
    """print_calls has 3 counts of headroom under the signed waiver; this module spends none."""
    import ast
    src = (ROOT / "mamey" / "modeb_full50_contract.py").read_text(encoding="utf-8")
    calls = [
        n for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) in {"print", "emit"}
    ]
    assert calls == [], "this helper must not spend print_calls headroom"
