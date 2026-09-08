from mamey.mamey_markers import MAMEY_MARKERS
from mamey.mamey_cassettes import MAMEY_CASSETTES
from mamey.sapote_markers import SAPOTE_MARKERS
from mamey.sapote_cassettes import SAPOTE_CASSETTES


def ids(records):
    return [r.id for r in records]


def test_unique_ids():
    all_ids = ids(MAMEY_MARKERS) + ids(MAMEY_CASSETTES) + ids(SAPOTE_MARKERS) + ids(SAPOTE_CASSETTES)
    assert len(all_ids) == len(set(all_ids))


def test_prefixes():
    assert all(x.startswith("MMK-") for x in ids(MAMEY_MARKERS))
    assert all(x.startswith("MMC-") for x in ids(MAMEY_CASSETTES))
    assert all(x.startswith("SMK-") for x in ids(SAPOTE_MARKERS))
    assert all(x.startswith("SMC-") for x in ids(SAPOTE_CASSETTES))


def test_required_metadata_present():
    for record in MAMEY_MARKERS + MAMEY_CASSETTES + SAPOTE_MARKERS + SAPOTE_CASSETTES:
        assert record.id
        assert record.name
        assert record.evidence_tier
        assert record.claim_ceiling
        assert record.source_locator
        assert record.citation
        assert record.wet_lab_routes


def test_cassette_references_resolve():
    marker_ids = set(ids(MAMEY_MARKERS) + ids(SAPOTE_MARKERS))
    for cassette in MAMEY_CASSETTES + SAPOTE_CASSETTES:
        for ref in cassette.required_markers + cassette.optional_markers + cassette.forbidden_markers:
            assert ref in marker_ids, f"unresolved marker reference {ref} in {cassette.id}"


def test_validate_stable_ids_accepts_prefix_argument():
    from mamey.registry_schema import validate_stable_ids
    validate_stable_ids(MAMEY_MARKERS, "MMK-")
    validate_stable_ids(MAMEY_CASSETTES, "MMC-")
    validate_stable_ids(SAPOTE_MARKERS, "SMK-")
    validate_stable_ids(SAPOTE_CASSETTES, "SMC-")


def test_first_mamey_cassettes_are_wired_to_required_markers():
    by_id = {c.id: c for c in MAMEY_CASSETTES}
    assert by_id["MMC-001"].required_markers == ("MMK-DOM-005",)
    assert by_id["MMC-002"].required_markers == ("MMK-DOM-015",)
