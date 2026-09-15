"""v9.7.432 — an EMPTY published roster must mean "nothing is published", not "feature off".

Owner ruling 2026-09-15 (GOVERNANCE_RULING_release_class_2026-09-15.md): *"The bee strains are not
published YET."*  The `published_registry` parameter (v9.7.331) is the designated mechanism for
expressing that, but it is tested for TRUTHINESS, so an empty roster is indistinguishable from an
unconfigured one and both yield PUBLIC — the mechanism fails OPEN, contradicting
`derive_release`'s own docstring ("Fail-safe to PRIVATE").

The distinction this pins:
    published_registry=None        -> not configured; legacy v9.7.236 blanket AS->PUBLIC preserved
    published_registry=frozenset() -> configured, nothing published; every AS strain -> PRIVATE
"""
import pytest

from mamey.dedup_and_guard import derive_release, resolve_release

BEE = ["AS-188", "AS-190", "AS-678", "AS-815", "AS-932"]


@pytest.mark.parametrize("strain", BEE)
def test_empty_roster_means_nothing_published(strain):
    """THE RULING. An explicitly empty roster must privatise every AS strain."""
    assert derive_release(strain, published_registry=frozenset()) == "PRIVATE"


@pytest.mark.parametrize("strain", BEE)
def test_unconfigured_roster_preserves_legacy_behaviour(strain):
    """None = not configured. The v9.7.236 PI decision still governs; no existing run changes."""
    assert derive_release(strain) == "PUBLIC"
    assert derive_release(strain, published_registry=None) == "PUBLIC"


def test_populated_roster_still_discriminates():
    reg = frozenset({"AS-188"})
    assert derive_release("AS-188", published_registry=reg) == "PUBLIC"
    assert derive_release("AS-190", published_registry=reg) == "PRIVATE"


def test_empty_roster_refuses_a_public_override():
    """An operator must not be able to force PUBLIC once the roster says nothing is published."""
    rel, refused = resolve_release("AS-188", override="PUBLIC", published_registry=frozenset())
    assert (rel, refused) == ("PRIVATE", True)


def test_unconfigured_roster_still_honours_a_public_override():
    rel, refused = resolve_release("AS-188", override="PUBLIC")
    assert (rel, refused) == ("PUBLIC", False)


@pytest.mark.parametrize("strain", ["AJS-001", "PENDING-x"])
@pytest.mark.parametrize("reg", [None, frozenset(), frozenset({"AJS-001", "PENDING-x"})])
def test_private_prefixes_unconditional_under_every_roster_state(strain, reg):
    """The leak guard outranks the roster in all three configurations, including a roster that
    (wrongly) lists them as published."""
    assert derive_release(strain, published_registry=reg) == "PRIVATE"


@pytest.mark.parametrize("reg", [None, frozenset()])
def test_non_as_shapes_unaffected_by_the_roster(reg):
    """The roster narrows the AS branch only; it must not touch cleared or unrecognized shapes."""
    assert derive_release("SID001", published_registry=reg) == "PUBLIC"
    assert derive_release("Nocardia_fusca", published_registry=reg) == "PRIVATE"
