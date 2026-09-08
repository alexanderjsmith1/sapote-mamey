"""v9.7.95 AUDIT (P-A6): no NEW dangling `examples/` reference may enter the live docs.

`examples/` is empty, so every live-doc reference under it is currently a dead pointer. The full set
is documented in EXAMPLES_REFERENCE_LEDGER.md and is pending your restore-vs-rewrite decision. This
guard does not force that decision — it freezes the *known* set as a baseline and fails the moment a
reference to a NEW (non-baselined) missing examples/ file appears. As you fix entries, the dangling set
shrinks below the baseline (still green); remove fixed entries from DANGLING_BASELINE to tighten it.

Detector lives in tools/check_dangling_refs.py (single source of truth for the scan).
"""
from __future__ import annotations
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_dangling_refs import scan  # noqa: E402

# Known-pending dangling examples/ targets as of v9.7.95 (see EXAMPLES_REFERENCE_LEDGER.md).
# These are tracked, not accepted as correct — the ledger holds the restore/rewrite plan.
DANGLING_BASELINE = frozenset()  # v9.7.97: all 8 restored from v9.7.72 CODE tier; guard now enforces zero


def test_no_new_dangling_examples_refs():
    current = set(scan(ROOT).keys())
    new = current - DANGLING_BASELINE
    assert not new, (
        "NEW dangling examples/ reference(s) introduced (the target file does not exist; either ship it "
        "or fix the reference): " + ", ".join(sorted(new))
    )


def test_baseline_has_no_stale_entries():
    # Keeps the baseline honest: if a baselined target has been restored/rewritten away, prompt a trim
    # so the guard can be tightened toward zero.
    current = set(scan(ROOT).keys())
    resolved = DANGLING_BASELINE - current
    assert not resolved, (
        "these baselined targets are no longer dangling — remove them from DANGLING_BASELINE to tighten "
        "the guard: " + ", ".join(sorted(resolved))
    )
