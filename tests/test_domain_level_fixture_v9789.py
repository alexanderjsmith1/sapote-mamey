"""v9.7.89: domain-level schema/claim-safety regression against the vendored synthetic fixture.

The fixture (tests/fixtures/domain_level_minimal_antismash.zip) is a tiny synthetic antiSMASH
GBK with NRPS, PKS, RiPP(lanthi), siderophore, and accessory-only loci — no real strain data."""
from __future__ import annotations
import json, os
import pytest

FIX = "tests/fixtures/domain_level_minimal_antismash.zip"
EXP = "tests/fixtures/domain_level_expected_counts.json"


@pytest.mark.skipif(not os.path.exists(FIX), reason="fixture missing")
def test_fixture_parses_to_expected_domains():
    from mamey.parsers import extract_domain_features
    expected = json.load(open(EXP))
    feats = extract_domain_features(FIX)
    assert len(feats) == expected["n_domains"]
    assert sorted({f.domain for f in feats}) == expected["domain_names"]


@pytest.mark.skipif(not os.path.exists(FIX), reason="fixture missing")
def test_fixture_role_counts_match_expected():
    from collections import Counter
    from mamey.parsers import extract_domain_features
    from mamey.domain_level import load_rules, role_for_domain
    expected = json.load(open(EXP))
    tax, _ = load_rules()
    feats = extract_domain_features(FIX)
    roles = dict(Counter(role_for_domain(f.domain, tax) for f in feats))
    assert roles == expected["role_counts"]


@pytest.mark.skipif(not os.path.exists(FIX), reason="fixture missing")
def test_fixture_has_each_required_class():
    """Request §10: fixture must contain NRPS, PKS, RiPP, siderophore, and accessory signals."""
    from collections import Counter
    from mamey.parsers import extract_domain_features
    from mamey.domain_level import load_rules, role_for_domain
    tax, _ = load_rules()
    feats = extract_domain_features(FIX)
    roles = set(role_for_domain(f.domain, tax) for f in feats)
    assert "NRPS A-domain / loading" in roles
    assert "PKS ketosynthase" in roles
    assert "Lanthipeptide maturation" in roles
    assert "Siderophore uptake/export" in roles
    assert "Unknown/repeat/accessory" in roles  # the accessory-only locus
