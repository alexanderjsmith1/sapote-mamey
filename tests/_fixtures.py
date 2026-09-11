"""Shared test fixture helpers (v9.7.405).

`stamp()` builds a BUILD_STAMP `build=` token that `tools/gen_release_manifest.py::date_from_stamp`
accepts — the format is `<YYYYMMDD>v<digits><letter>` (e.g. `20260902v97405a`). A bare
`20200101a` is REJECTED by that parser; that mismatch produced seven false failures in a peer lane
at .404, so the helper exists to make the right shape the easy one.
"""
from __future__ import annotations


def stamp(date: str = "20200101", n: int = 1, rev: str = "a") -> str:
    """Return a parser-valid build stamp: `{date}v{n}{rev}`."""
    assert len(date) == 8 and date.isdigit(), "date must be YYYYMMDD"
    assert len(rev) == 1 and rev.isalpha(), "rev must be one letter"
    return f"{date}v{int(n)}{rev}"
