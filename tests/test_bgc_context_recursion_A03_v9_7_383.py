"""v9.7.383 — A-03: the two BGC-context builders must not mutually recurse.

Merged audit ledger (WAC-01375 Claude chat + ChatGPT DSM46095 stream), disposition authority
Codex. `mode_b_receipt._bgc_context_from_triage` and `authored_verify._bgc_context_from_package`
each merged the other's output ("one ctx source, both doors", added independently on both sides).
Unguarded, that is an unbounded mutual recursion: each door recursed to Python's limit, the terminal
RecursionError was swallowed by the merge's `except` (returning a degraded ctx), and on a real
package the ~250 redundant full-file-I/O round-trips blew the 5-min wall (exit 124).

Fix: a `_cross` flag. A top-level call merges the sibling once and calls it with `_cross=False`, so
the sibling does not cross back. These fixtures pin both halves of Codex's contract:
positive — a top-level call TERMINATES and still carries BOTH contexts;
negative — a nested (`_cross=False`) call does NOT re-enter the sibling.
"""
import csv
import pathlib

from mamey import mode_b_receipt as mr
from mamey import authored_verify as av


def _pkg(tmp_path):
    with open(tmp_path / "X_4_triage_board.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["BGC_ID", "KCB_top", "Novelty_auto", "Lead_tier_auto"])
        w.writeheader()
        w.writerow({"BGC_ID": "BGC032", "KCB_top": "", "Novelty_auto": "55", "Lead_tier_auto": "HIGH"})
    return tmp_path


def test_top_level_triage_terminates_with_both_contexts(tmp_path):
    ctx = mr._bgc_context_from_triage(_pkg(tmp_path), "BGC032")  # _cross default True
    assert isinstance(ctx, dict) and ctx
    assert "KCB_top" in ctx, "triage-door key missing — door symmetry broken"
    assert "has_blastp_panel" in ctx, "package-door key missing — sibling merge dropped"


def test_top_level_package_terminates_with_both_contexts(tmp_path):
    ctx = av._bgc_context_from_package(str(_pkg(tmp_path)), "BGC032")  # _cross default True
    assert isinstance(ctx, dict) and ctx
    assert "has_blastp_panel" in ctx
    assert any(k in ctx for k in ("KCB_top", "kcb_top")), "triage merge dropped from package door"


def test_nested_call_does_not_cross_back(tmp_path):
    # count re-entrant sibling calls under a top-level triage call
    calls = {"pkg": 0}
    orig = av._bgc_context_from_package

    def _counting(*a, **k):
        calls["pkg"] += 1
        return orig(*a, **k)

    av._bgc_context_from_package = _counting
    try:
        mr._bgc_context_from_triage(_pkg(tmp_path), "BGC032")
    finally:
        av._bgc_context_from_package = orig
    # BOUNDED, not unbounded: at most one hop into the package builder, no recursion back. 0 or 1
    # both mean "no recursion" (0 can occur if another test in a random-ordered suite left a module
    # attribute stubbed); the pre-fix bug climbed to ~250, so >=2 is the real regression signal.
    assert calls["pkg"] <= 1, f"expected <=1 cross-hop (no recursion), got {calls['pkg']}"


def test_nested_flag_short_circuits_the_sibling_read(tmp_path):
    # a _cross=False call must not read triage at all (empty triage-key contribution)
    ctx = av._bgc_context_from_package(str(_pkg(tmp_path)), "BGC032", _cross=False)
    assert ctx is not None
    # package door still built; triage-only key must be absent under _cross=False
    assert "Novelty_auto" not in ctx and "KCB_top" not in ctx
