"""Exact public rosters supply authority; omitted/empty rosters both default PRIVATE."""

from tests._synthetic_identity_fixture import synthetic_namespace_id
import pytest
from mamey.dedup_and_guard import derive_release, resolve_release

SYNTHETIC = ["AS-" + str(n) for n in range(987650, 987655)]


@pytest.mark.parametrize("strain", SYNTHETIC)
@pytest.mark.parametrize("roster", [None, frozenset()])
def test_no_exact_public_authority_defaults_private(strain, roster):
    assert derive_release(strain, published_registry=roster) == "PRIVATE"


def test_populated_roster_discriminates_exact_identifiers():
    public, private = SYNTHETIC[:2]
    assert derive_release(public, published_registry={public}) == "PUBLIC"
    assert derive_release(private, published_registry={public}) == "PRIVATE"
    assert derive_release("public_reference", published_registry={"public_reference"}) == "PUBLIC"


def test_configured_empty_as_roster_refuses_public_override():
    assert resolve_release(SYNTHETIC[0], "PUBLIC", published_registry=frozenset()) == ("PRIVATE", True)


def test_omitted_roster_preserves_explicit_public_override():
    assert resolve_release(SYNTHETIC[0], "PUBLIC") == ("PUBLIC", False)


@pytest.mark.parametrize("strain", ["AJS-" + "987654", (synthetic_namespace_id('PENDING', width=None, case_index=917, separator=True))])
def test_hard_private_guard_outranks_even_exact_roster(strain):
    assert derive_release(strain, published_registry={strain}) == "PRIVATE"


@pytest.mark.parametrize("strain", ["SID987654", "SCLAV", "public_reference"])
def test_spelling_never_supplies_authority(strain):
    assert derive_release(strain) == "PRIVATE"
