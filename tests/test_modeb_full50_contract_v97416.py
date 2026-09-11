"""Drift guards for the frozen 50-section Mode-B contract (bundle v9.7.416).

Four modules in this bundle refuse to run unless they are handed a contract carrying
exactly sections 1..50.  The source Markdown already shipped in the bundle; each consumer
took the contract as an operator-supplied path and pinned it with a sha256 that the same
config supplied.  ``mamey/data/mode_b/modeb_full50_contract.json`` is that missing named
artifact.  These guards keep it identical to the document it was copied from and keep it
honest about the consumers that depend on the shape.

No biological claim is made or admitted here; a section requirement is a scope statement,
not evidence.  Judgment deferred.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "MODEB_50_SECTION_CONTRACT_CANDIDATE.md"
FROZEN = ROOT / "mamey" / "data" / "mode_b" / "modeb_full50_contract.json"
PROFILE48 = ROOT / "mamey" / "data" / "mode_b" / "modeb_full30_corrective_contract.json"

# The exact expression the consumers use (evidence_disagreements.py,
# cohort_enzyme_neighborhoods.py).  Copied deliberately: if the engine's parse changes,
# these guards must fail rather than quietly diverge.
ROW = re.compile(r'^\| (\d+) \| (.*?) \|$', re.M)

# path -> the shape assertion that module makes
CONSUMERS = {
    "mamey/evidence_disagreements.py": "set(range(1,51))",
    "mamey/cohort_enzyme_neighborhoods.py": "set(range(1,51))",
    "mamey/structured_domain_motif_extension.py": "!=50",
    "tools/cohort_tailoring/build_atlas.py": "list(range(1,51))",
}


def _doc_requirements():
    return {int(n): v.strip() for n, v in ROW.findall(DOC.read_text(encoding="utf-8"))}


def _frozen():
    return json.loads(FROZEN.read_text(encoding="utf-8"))


def test_source_document_present():
    assert DOC.is_file(), f"missing source document {DOC}"


def test_document_yields_exactly_fifty_contiguous_sections():
    req = _doc_requirements()
    assert sorted(req) == list(range(1, 51)), (
        f"document parsed to {len(req)} rows; the four consumers require 1..50"
    )
    assert all(v for v in req.values()), "a requirement row parsed to empty text"


def test_frozen_contract_is_well_formed():
    c = _frozen()
    assert c["schema_version"] == "modeb_current50_v1"
    assert c["status"] == "current"
    assert c["section_count"] == 50
    nums = [s["section_number"] for s in c["sections"]]
    assert nums == list(range(1, 51))


def test_frozen_matches_document_verbatim():
    c = _frozen()
    frozen = {s["section_number"]: s["requirement"] for s in c["sections"]}
    assert frozen == _doc_requirements(), (
        "frozen contract has drifted from docs/MODEB_50_SECTION_CONTRACT_CANDIDATE.md"
    )


def test_recorded_source_hash_matches_the_document_on_disk():
    c = _frozen()
    actual = hashlib.sha256(DOC.read_bytes()).hexdigest()
    assert c["source_document"]["sha256"] == actual, (
        "the source document changed but the frozen contract was not regenerated; "
        "consumer configs pin this document by sha256, so an in-place edit invalidates them"
    )


def test_forty_eight_section_profile_is_untouched():
    p = json.loads(PROFILE48.read_text(encoding="utf-8"))
    assert p["schema_version"] == "modeb_corrective_full48_v1"
    assert len(p["sections"]) == 48, "the 48-section corrective profile must not be rewritten"
    c = _frozen()
    assert c["does_not_supersede"]["sections"] == 48


@pytest.mark.parametrize("rel", sorted(CONSUMERS))
def test_named_consumer_still_exists_and_still_requires_fifty(rel):
    """Keeps this contract from becoming an orphan.

    If a consumer is refactored away or stops requiring 50, this guard fails and the
    frozen artifact's stated consumer list must be corrected -- rather than the contract
    silently outliving its only reason to exist.
    """
    p = ROOT / rel
    assert p.is_file(), f"consumer named by the frozen contract is gone: {rel}"
    body = p.read_text(encoding="utf-8")
    assert "50" in body and ("range(1,51)" in body or "range(1, 51)" in body or "!=50" in body), (
        f"{rel} no longer asserts a 50-section shape; update modeb_full50_contract.json"
    )
    listed = {c["path"] for c in _frozen()["consumers_requiring_exactly_50"]}
    assert rel in listed


def test_frozen_contract_satisfies_each_consumer_predicate():
    """Reference row shape only; this JSON is not a consumer integration test."""
    c = _frozen()
    nums = {s["section_number"] for s in c["sections"]}
    assert nums == set(range(1, 51))                      # evidence_disagreements
    assert nums == set(range(1, 51))                      # cohort_enzyme_neighborhoods
    assert len(c["sections"]) == 50                       # structured_domain_motif_extension
    assert [s["section_number"] for s in c["sections"]] == list(range(1, 51))  # build_atlas
