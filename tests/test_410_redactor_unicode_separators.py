"""v9.7.410 hostile audit (round 4) — private cohort ids written with a non-ASCII hyphen survived
the public-tier redactor: `AJS‑12` (U+2011), `AJS–12` (en dash), `AS-​999` (zero-width space next
to the hyphen), `AS&#45;999`. AJS is unconditionally private (mamey.cohort_figures.is_private), so
this was a live leak vector for any prose that went through a word processor."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

import mamey

ROOT = Path(mamey.__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import redact_public_tier as R  # noqa: E402


@pytest.mark.parametrize("text", [
    "strain AJS‑12 sample",        # non-breaking hyphen
    "strain AJS–12 sample",        # en dash
    "strain AJS—12 sample",        # em dash
    "strain AJS−12 sample",        # minus sign
    "strain AJS-​12 sample",       # zero-width space after the hyphen
    "strain AJS­-12 sample",       # soft hyphen before the hyphen
    "strain AJS&#45;12 sample",         # HTML entity hyphen
    "strain AJS&ndash;12 sample",
    "strain AS‑999 sample",
    "strain as–999 sample",        # lowercase, en dash
])
def test_unicode_separator_variants_are_redacted(text):
    out = R.redact_text(text)
    assert "12" not in out and "999" not in out, out
    assert "AS-XXX" in out
    assert R.private_id_matches(text), "audit must see it too"


@pytest.mark.parametrize("text", [
    "AS-1 prose",           # 1-digit carve-out
    "AS15 public",          # 2-digit dashless carve-out
    "AJS327 mibig",         # public MIBiG organism
    "LAS-123 compound",     # trailing-tail carve-out
    "CAS-12 cassette",
    "enterocin AS-48",      # KNOWN_PUBLIC_AS
    "an AS – 999 range",  # spaces around the dash are prose, not an id
])
def test_carve_outs_are_untouched(text):
    assert R.redact_text(text) == text
