"""GF3-2 adversarial identity families (gene-first v2 successor r2 — V4 §3.3).

The nine-fixture differential gate proves candidate/shipped verdict equivalence; these
families pin the convergent semantics adversarially: normalization edges, refusal edges,
canonical-token collision (distinct raw spellings of one locus must yield ONE canonical
token), and normalized request-vs-components conflict. Where both paths are expressible,
every expectation here was cross-checked against the shipped owner
(`mamey/mode_b/gene_first_explore.py`) semantics.

Engineering identity plumbing only; no scientific claim; judgment deferred.
"""
from __future__ import annotations

import pytest

from mamey.mode_b.gene_first_stage_v2 import StageHold, canonical_identity, identity_token

GOOD_NODE = "NODE_7_length_120000_cov_42.5"


def _identity(**overrides):
    raw = {
        "strain": "SYNTH-001",
        "full_node": GOOD_NODE,
        "region": "region002",
        "bgc_alias": "BGC007",
    }
    raw.update(overrides)
    return raw


def _accepts(**overrides):
    return canonical_identity(_identity(**overrides))


def _refuses(**overrides):
    with pytest.raises(StageHold) as exc:
        canonical_identity(_identity(**overrides))
    assert exc.value.code == "MODEB_GF2_IDENTITY_HOLD"


# --- region family ------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("region7", "region007"),
    ("region_7", "region007"),
    ("region 7", "region007"),
    ("Region7", "region007"),
    ("REGION-12", "region012"),
    ("region0001", "region001"),
    ("region9999", "region9999"),  # %03d never truncates: 4 digits stay 4 digits
    ("region0", "region000"),
])
def test_region_normalizes(raw, expected):
    assert _accepts(region=raw)["region"] == expected


@pytest.mark.parametrize("raw", [
    "", "region", "region1.5", "region12345", "region--1", "7", "reg7", "regionx",
])
def test_region_refuses(raw):
    _refuses(region=raw)


# --- BGC alias family ---------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("BGC013", "BGC013"),
    ("bgc013", "BGC013"),
    ("BGC0134", "BGC0134"),
    ("bgc0134", "BGC0134"),
])
def test_alias_normalizes(raw, expected):
    assert _accepts(bgc_alias=raw)["bgc_alias"] == expected


@pytest.mark.parametrize("raw", [
    "", "BGC7", "BGC12", "BGC12345", "BGC 13", "BGC-13", "BGC1.3", "BGC+13",
    "ВGC013",  # Cyrillic VE lookalike for 'B'
    "bgc", "13",
])
def test_alias_refuses(raw):
    _refuses(bgc_alias=raw)


# --- NODE / contig family -----------------------------------------------------------------

@pytest.mark.parametrize("raw", [
    GOOD_NODE,
    "node_7_length_120000_cov_42.5",   # complete grammar in lowercase is admissible
    "NODE_162_length_54321_cov_3",     # integer coverage is within [0-9.]+
])
def test_complete_node_forms_accepted_case_preserved(raw):
    assert _accepts(full_node=raw)["full_node"] == raw


@pytest.mark.parametrize("raw", [
    "NODE_7",
    "NODE_9_length_100",
    "NODE_7_length_120000_cov_",
    "NODE_7_cov_42.5",
    "NODE_7_length__cov_42.5",
    "node_7",
    "NODE_7_length_120000_cov_42.5/extra",
    "..",
    "../NODE_7_length_120000_cov_42.5",
    "NODE_7_length_120000_cov_42.5\x01",
    "node",
    "contig",
    "",
])
def test_shortened_malformed_or_unsafe_nodes_refuse(raw):
    _refuses(full_node=raw)


def test_plain_contig_still_admissible():
    assert _accepts(full_node="contig00042")["full_node"] == "contig00042"


# --- canonical-token collision ------------------------------------------------------------

def test_distinct_raw_spellings_collapse_to_one_canonical_token():
    """region7 / region_7 / region 7 / Region7 / REGION-7 and bgc007/BGC007 are ONE locus
    and must produce ONE canonical token — never two content-addressed identities."""
    tokens = {
        identity_token(_identity(region=r, bgc_alias=a))
        for r in ("region7", "region_7", "region 7", "Region7", "REGION-7", "region007")
        for a in ("BGC007", "bgc007")
    }
    assert tokens == {f"SYNTH-001__{GOOD_NODE}__region007__BGC007"}


# --- normalized request vs components conflict --------------------------------------------

def test_raw_spelled_exact_identity_accepted_when_it_normalizes_to_components():
    ident = _accepts(
        region="region7",
        bgc_alias="bgc007",
        exact_identity=f"SYNTH-001 / {GOOD_NODE} / region7 / bgc007",
    )
    assert ident["exact_identity"] == f"SYNTH-001 / {GOOD_NODE} / region007 / BGC007"


def test_conflicting_exact_identity_refuses_after_normalization():
    _refuses(exact_identity=f"SYNTH-001 / {GOOD_NODE} / region008 / BGC007")


def test_malformed_exact_identity_refuses():
    _refuses(exact_identity=f"SYNTH-001 / {GOOD_NODE} / region002")
