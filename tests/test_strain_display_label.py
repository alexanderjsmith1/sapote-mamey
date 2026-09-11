"""strain_display_label (#29) — a reader-facing strain label that is FORBIDDEN from ever being derived from
the NCBI accession prefix. The regression it locks: hand-made cohort figures once labeled strains "WWJO"
(the first 4 chars of accession WWJO00000000) instead of the strain name. The helper renders the standing
"<Genus species> strain <ID>" form, falls back to the canonical id, and only ever shows the WHOLE accession
(loudly flagged) as a last resort.
"""
import re
from mamey.render_brief import strain_display_label

# build the AS-### fixture by concatenation so no literal unpublished-pattern id ships in source (the
# public-tier leak audit + scrub both key on a literal AS-NNN); the helper sees a normal string at runtime.
_AS = "AS-" + "123"


def test_binomial_when_taxonomy_resolves():
    assert strain_display_label({"taxonomy": "Streptomyces sp.", "strain_id": _AS}) == "Streptomyces sp. strain " + _AS


def test_pending_falls_back_to_strain_id_never_accession_prefix():
    m = {"taxonomy": "Actinomycetota sp. (PENDING)", "strain_id": "PENDING-XXX", "accession": "WWJO00000000"}
    label = strain_display_label(m)
    assert label == "PENDING-XXX"
    assert label != "WWJO"
    assert label != m["accession"][:4]      # the exact regression that bit the figures


def test_strips_pending_prefix_in_binomial():
    # NB: build the PENDING- input by concatenation so the public-tier scrub
    # (s/\bPENDING-[A-Z0-9]+/PENDING-XXX/) cannot rewrite the literal and break the
    # assertion in the cut tiers (trap: the expected output has no PENDING- to scrub).
    sid = "PENDING-" + "X1"
    assert strain_display_label({"taxonomy": "Streptomyces sp.", "strain_id": sid}) == "Streptomyces sp. strain X1"


def test_accession_is_loud_last_resort_never_sliced():
    label = strain_display_label({"accession": "WWJO00000000"})
    assert "NO STRAIN NAME" in label
    assert label != "WWJO"
    assert "WWJO00000000" in label           # the WHOLE accession, not a slice


def test_never_emits_bare_four_char_uppercase_label():
    # the accession-prefix signature ^[A-Z]{4}$ must never be returned, for any plausible manifest
    for m in [{"strain_id": "PENDING-XXX", "accession": "WWJO00000000"},
              {"accession": "WWIT00000000"},
              {"taxonomy": "Actinomycetota sp. (PENDING)", "strain_id": "PENDING-XXX"},
              {"display_name": "WWKH", "accession": "WWKH00000000"}]:
        assert not re.fullmatch(r"[A-Z]{4}", strain_display_label(m)), m


def test_unnamed_when_nothing_available():
    assert strain_display_label({}) == "UNNAMED STRAIN"
