"""--release operator override (resolve_release): make the documented flag real, leak guard preserved.

A public reference genome (named species / NCBI accession) is not matched by PUBLIC_PATTERN, so it fail-safes
to PRIVATE — wrong for a published genome. --release PUBLIC lets the operator assert PUBLIC on such an
UNRECOGNIZED shape. But the operator must NOT be able to force an AS/AJS/PENDING strain public.

Fixtures note: synthetic identifiers are built by concatenation so the public-tier ID scrub (which rewrites a
literal AS-NNN / AJS-NNN / SIDNNNN to a placeholder) does NOT mangle them — these tests assert the refusal
flag, which requires the REAL pattern at runtime to trip the guard. Synthetic numbers never collide with real
strains.
"""
from mamey.dedup_and_guard import resolve_release, derive_release

_AS   = "AS-" + "9001"        # private-identifier shapes, scrub-evading in source, real at runtime
_AJS  = "AJS-" + "9002"
_PEND = "PENDING-" + "SYNTH"
_SID  = "SID" + "9001"        # a known public-pattern shape (SID\d+)


def test_default_is_failsafe_derivation():
    assert resolve_release("Nocardia_fusca") == (derive_release("Nocardia_fusca"), False)
    assert resolve_release("Nocardia_fusca")[0] == "PRIVATE"   # unrecognized -> PRIVATE by default


def test_public_override_on_unrecognized_shape():
    # a named reference genome / accession -> operator may assert PUBLIC
    assert resolve_release("Nocardia_fusca", "PUBLIC") == ("PUBLIC", False)
    assert resolve_release("CP109162", "PUBLIC") == ("PUBLIC", False)
    assert resolve_release("Nocardia_NBC01730", "PUBLIC") == ("PUBLIC", False)


def test_public_override_REFUSED_on_private_identifier():
    # the leak guard wins — operator cannot force a private-identifier strain public.
    # v9.7.236: AS- is PUBLIC per PI decision (.219/.229); AJS-/PENDING- remain the guarded shapes.
    assert resolve_release(_AJS, "PUBLIC") == ("PRIVATE", True)
    assert resolve_release(_PEND, "PUBLIC") == ("PRIVATE", True)
    assert resolve_release(_AS, "PUBLIC") == ("PUBLIC", False)   # AS- now honored public


def test_private_override_always_honored():
    assert resolve_release("Nocardia_fusca", "PRIVATE") == ("PRIVATE", False)
    assert resolve_release(_SID, "PRIVATE") == ("PRIVATE", False)   # even a public-pattern strain


def test_registry_membership_blocks_public_override():
    assert resolve_release("mysecret", "PUBLIC", private_registry=frozenset({"mysecret"})) == ("PRIVATE", True)


def test_known_public_pattern_still_public_by_default():
    assert resolve_release(_SID)[0] == "PUBLIC"
    assert resolve_release("SCLAV")[0] == "PUBLIC"
