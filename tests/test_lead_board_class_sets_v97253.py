"""PC-4 (v9.7.253 Bunny Hop session 2): pin lead_board's product-class set invariants.

Original framing ("HIGH consistent with source_scans CCTT trigger names") was mis-scoped:
`lead_board.HIGH` is a set of antiSMASH *product classes* (phosphonate, lanthipeptide, ...),
while source_scans CCTT triggers are `T43-*` codes — different vocabularies that need not be
equal. What IS a real, checkable invariant is the internal relationship between HIGH,
COMPLETE_OK and PRIMMET, plus token format. Pinning these catches accidental drift when a
future edit adds a class to one set.

NOTE (flagged for the Developer or User): this test documents — it does NOT bless — the current fact that
'betalactone' is in BOTH HIGH (specialized lead) and PRIMMET (primary-metabolism suspect),
which are meant to be opposite buckets. See KNOWN_HIGH_PRIMMET_OVERLAP below.
"""
import importlib.util
from pathlib import Path

_LB = Path(__file__).resolve().parent.parent / "tools" / "lead_board.py"
_spec = importlib.util.spec_from_file_location("lead_board_under_test", _LB)
lb = importlib.util.module_from_spec(_spec)
# lead_board imports `_wbio` (a sibling in tools/); make that importable.
import sys
sys.path.insert(0, str(_LB.parent))
_spec.loader.exec_module(lb)

# The single overlap that currently exists between the "specialized lead" and "primary-metabolism
# suspect" buckets. Kept explicit so that (a) any NEW accidental overlap fails this test, and
# (b) this contradiction stays visible until the Developer or User decides which bucket betalactone belongs in.
KNOWN_HIGH_PRIMMET_OVERLAP = {"betalactone"}


def test_high_is_subset_of_complete_ok():
    # COMPLETE_OK is defined as {real biosynthetic classes} | HIGH, so this must hold; it breaks
    # if the `| HIGH` union is ever dropped.
    assert lb.HIGH <= lb.COMPLETE_OK


def test_high_primmet_overlap_is_only_the_known_flagged_one():
    overlap = lb.HIGH & lb.PRIMMET
    assert overlap == KNOWN_HIGH_PRIMMET_OVERLAP, (
        f"unexpected HIGH/PRIMMET overlap {overlap - KNOWN_HIGH_PRIMMET_OVERLAP} — a product "
        f"class is tagged as both a specialized lead and a primary-metabolism suspect"
    )


def test_class_tokens_have_no_stray_whitespace():
    # A token with surrounding whitespace would silently never match a real antiSMASH product
    # label. (Underscores are fine — antiSMASH does emit e.g. 'fatty_acid'.)
    for token in (lb.HIGH | lb.PRIMMET | lb.COMPLETE_OK):
        assert token == token.strip(), f"{token!r} has surrounding whitespace"
        assert token, "empty token in a lead_board class set"
