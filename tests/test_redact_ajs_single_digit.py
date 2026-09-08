"""Regression test — AJS single-digit identifiers must not escape redaction.

Found 2026-07-08 while auditing release-tier policy drift.

`AS_RE` was `(?<![A-Za-z])(?:A(?:JS|S)-\\d{2,}|AS\\d{3,})`. The `\\d{2,}` floor exists for the
deliberate 1-digit **AS-N** carve-out (prose such as "AS-1" must not be corrupted), but the
shared `A(?:JS|S)-` alternation applied that floor to **AJS** as well. Result: `AJS-9` — an
unconditionally private identifier per `mamey.cohort_figures.is_private()` — passed straight
through the public-tier scrub.

Latent rather than live: no single-digit AJS strain exists in the current registry, and the AS
scrub is deactivated by default (`AS_SCRUB=0`, PI decision 2026-07-06). But the redactor is the
release SSOT and must not leave a private ID un-tokenised.

Fix: split the alternation — `AJS-\\d+` (no floor) vs `AS-\\d{2,}` (floor retained).

This test pins BOTH directions: private ids always redact; every documented carve-out survives.
"""
import importlib.util
import os

HERE = os.path.dirname(__file__)
MOD = os.path.join(HERE, "..", "tools", "redact_public_tier.py")

spec = importlib.util.spec_from_file_location("redact_public_tier_mod", MOD)
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def test_single_digit_ajs_is_redacted():
    """The bug. AJS-9 is private and must never survive a scrub."""
    assert R.AS_RE.search("AJS-9"), "single-digit AJS must match the private-id pattern"
    assert R.private_id_matches("strain AJS-9 sample") == ["AJS-9"]
    assert "AJS-9" not in R.redact_text("strain AJS-9 sample")


def test_multi_digit_ajs_still_redacted():
    for tok in ["AJS-09", "AJS-123", "AJS-4567"]:
        assert R.AS_RE.search(tok), f"{tok} must still redact"


def test_pending_ids_still_redacted():
    assert "PENDING-3" not in R.redact_text("cohort PENDING-3 pending")


def test_documented_carveouts_survive():
    """Every carve-out the module docstring promises. None may regress."""
    # 1-digit AS-N is prose, not a strain id
    assert not R.AS_RE.search("AS-1")
    # dashless 2-digit AS15 is public
    assert not R.AS_RE.search("AS15")
    # dashless AJS327 is a public MIBiG organism
    assert not R.AS_RE.search("AJS327")
    # compound-name tails and cassette stable-IDs
    assert not R.AS_RE.search("LAS-30")
    assert not R.AS_RE.search("CAS-12")


def test_enterocin_as48_is_not_corrupted():
    """AS-48 is the bacteriocin enterocin AS-48 (MIBiG BGC0000489), never a strain."""
    assert R.redact_text("enterocin AS-48") == "enterocin AS-48"
    assert R.private_id_matches("enterocin AS-48") == []


def test_as_series_ids_still_tokenise_when_scrub_is_armed():
    """AS scrub is call-site gated (make_public_tier.sh AS_SCRUB=0 by default), but when the
    machinery IS invoked it must still tokenise whole AS ids — the pattern stays reusable for a
    future private cohort."""
    assert R.redact_text("strain AS-815") == "strain AS-XXX"
    assert R.redact_text("strain AS-81567") == "strain AS-XXX"  # whole token, no partial tail
