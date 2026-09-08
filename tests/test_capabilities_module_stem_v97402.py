"""Capabilities module-stem indexing (.402, ROSTER_402 seed #3 — Black Cherry-4).

Verified field failure (sealed v9.7.401, 2026-09-02): `search_capabilities(["rggmci"])`
returned ten modules that merely MENTION rggmci in their docstrings while the owner module
`mamey/rggmci.py` itself was absent — its docstring spells the concept "RG-GMCI", so the
substring never matched, and the module's own NAME was not part of the match corpus. The
exact failure shape the capabilities subcommand exists to prevent (a session re-deriving a
shipped capability because the search could not surface its owner).

Fix under test: the module stem joins the match corpus (a stem hit counts one occurrence and
is flagged in matched_lines), and ranking prefers stem-matching modules within equal keyword
coverage — the likely owner outranks passing mentions. Engineering search plumbing only.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from gen_tools_inventory import search_capabilities  # noqa: E402


def test_rggmci_query_surfaces_the_owner_module():
    rows = search_capabilities(["rggmci"], root=ROOT)
    paths = [row["path"] for row in rows]
    assert "mamey/rggmci.py" in paths, (
        "the owner module is invisible to its own name; got: %r" % paths
    )


def test_stem_match_outranks_prose_mentions():
    """Within equal keyword coverage, stem-matching modules lead the result list."""
    rows = search_capabilities(["rggmci"], root=ROOT)
    top_two = {row["path"] for row in rows[:2]}
    assert {"mamey/rggmci.py", "tools/rggmci_cohort_rollup.py"} <= top_two, (
        "stem-matching owners should lead: %r" % [row["path"] for row in rows[:4]]
    )


def test_stem_hit_is_visible_in_matched_lines():
    rows = search_capabilities(["rggmci"], root=ROOT)
    owner = next(row for row in rows if row["path"] == "mamey/rggmci.py")
    assert any("module name" in line for line in owner["matched_lines"])


def test_docstring_only_matches_still_returned_deterministically():
    """No regression: prose matches keep ranking by coverage, occurrences, then path."""
    rows = search_capabilities(["rggmci"], root=ROOT)
    prose = [row for row in rows if row["stem_match_count"] == 0]
    assert prose, "docstring-only matches disappeared"
    ordered = sorted(
        prose,
        key=lambda row: (-row["matched_keyword_count"], -row["match_count"], row["path"]),
    )
    assert prose == ordered


def test_unmatched_query_still_empty():
    assert search_capabilities(["zz-no-such-capability-zz"], root=ROOT) == []
