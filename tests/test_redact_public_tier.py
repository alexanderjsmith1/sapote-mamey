"""v9.7.115: AS_RE digit-range widening — 5+-digit cohort IDs redact as a whole token.

The old AS_RE {2,4}/{3,4} bounds left 'AS-70531' -> 'AS-XXX1' (trailing digit) and missed dashless
'AS70531' entirely. Widened to {2,}/{3,}. Width fixtures are authored detector inputs. Genuine public-reference controls below
are not synthetic declarations. No family-wide disclosure or registry-absence claim is made.
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import redact_public_tier as R  # noqa: E402


def test_redact_5plus_digit_as_whole_token():
    assert R.redact_text("AS-70531") == "AS-XXX"   # was AS-XXX1 (partial) under old {2,4}
    assert R.redact_text("AS70531") == "AS-XXX"    # was unredacted under old {3,4}(?![0-9])


def test_redact_5digit_carveouts_unchanged():
    assert R.redact_text("AS-48") == "AS-48"       # public enterocin AS-48 preserved
    assert R.redact_text("LAS-705") == "LAS-705"   # compound tail, L-prefixed, not a strain
    assert R.redact_text("CAS-705") == "CAS-705"   # cassette stable-ID, never redacted
    assert R.redact_text("AJS327") == "AJS327"     # dashless AJS public MIBiG organism
