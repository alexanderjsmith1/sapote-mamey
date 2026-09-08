#!/usr/bin/env python3
"""tier_vocabulary.py — the single owner of release-tier names, zip labels and aliases.

WHY THIS EXISTS
---------------
Before v9.7.408 the tier vocabulary was spread across at least four places that had to agree by
hand: a `case` statement in `tools/make_public_tier.sh` (twice — once for the zip name, once for
the strip rule), `REQUIRED_TIERS` in `tools/check_tier_parity.py`, the `TIER_ARCHIVE_RE` that parses
a zip filename back into a tier, and prose in `TIER_SET_EXPLAINER.md` / `TIER_DIFFERENCES.md` /
the wiki. Renaming one tier therefore meant a sweep across ~100 files with no way to prove the sweep
was complete. This module is that proof: every consumer reads the vocabulary from here.

THE v9.7.408 RENAME (owner ruling 2026-09-04)
---------------------------------------------
The tier formerly called `sid` is now `cohort`. The old name was specific to one lab's strain series
(the Chevrette 2019 attine `SID####` set) and distracted users of a general-purpose tool. The new
name states what the tier actually does: it is the tier that KEEPS the `cohort/` data banks where
`code` strips them. A label that matches its own strip rule cannot drift from its behaviour.

Note what did NOT change, because it is data rather than presentation:
  * `SID####` strain identifiers — real, public (Chevrette 2019), and legitimately retained;
    `mamey.dedup_and_guard.PUBLIC_PATTERN` admits `^SID\\d+$`.
  * the `'sid'` key used across `strains.json`, the master workbook and `build_id_resolver.py` to
    mean "strain id" — renaming it would break the producer/consumer data contract.
A textual `sid` -> `cohort` substitution would have corrupted both. The rename is scoped to tier
tokens only, and `tests/test_tier_vocabulary_v97408.py` fails if either of the above ever moves.

The tier's BEHAVIOUR was already generic and is unchanged by this rename. The `SID` uniformity scrub
that once made it series-specific was REMOVED at v9.7.364 (PI instruction 2026-08-12) because it was
both destructive — it rewrote `Amycolatopsis sp. SID8362`, an NCBI BLASTp *subject organism* that was
never ours to redact — and ineffective. Every `redact_public_tier.py` call in the cut passes
`--as-only`; SID is public and stays.

DEPRECATION
-----------
`sid` remains accepted as an alias for at least one cut. Every bundle sealed up to and including
v9.7.407 carries `-SID-public-` in its zip name and `tier=sid` in `BUILD_STAMP.txt`, so tools that
read historical bundles must keep resolving it. `resolve()` returns the canonical name and reports
whether an alias was used, so callers can warn once rather than silently accepting a retired name.
"""
from __future__ import annotations

from typing import NamedTuple

__all__ = [
    "TIERS", "CANONICAL", "ALIASES", "REQUIRED_TIERS", "OPTIONAL_PROMOTION_TIERS",
    "resolve", "archive_label", "archive_labels_including_historical", "describe",
]


class Tier(NamedTuple):
    name: str            # canonical token, as used on the command line and in BUILD_STAMP tier=
    label: str           # the zip-name segment: sapote-mamey-v{VERSION}-{label}-{STAMP}.zip
    required: bool       # part of the standard four-tier cut set
    summary: str         # one line, user-facing


TIERS: tuple[Tier, ...] = (
    Tier("code", "CODE", True,
         "The full runnable pipeline: engine code, tools, docs, examples and the Wheelhouse. "
         "Private cohort data and internal working notes removed."),
    Tier("clean", "CODE-analysis-free", True,
         "The code tier with worked strain-by-strain outputs also removed — the machinery without "
         "any of the analyses run through it."),
    Tier("cohort", "COHORT-public", True,
         "The code tier plus the public reference cohort data banks. Private material still removed. "
         "This is the tier that keeps cohort/ where code strips it."),
    Tier("merged", "MERGED-PRIVATE-scaffold", True,
         "Everything, withheld from nobody: the full internal working scaffold including any private/ "
         "tree and real strain identifiers. The operator's own copy."),
    Tier("public", "PUBLIC-RELEASE", False,
         "The public release artifact. Same content as the code tier; an explicit promotion, not part "
         "of the standard cut set."),
)

CANONICAL: dict[str, Tier] = {t.name: t for t in TIERS}

#: Retired tier names, kept resolvable so historical bundles stay readable.
#: value = the canonical name it now means; the comment is the cut that retired it.
ALIASES: dict[str, str] = {
    "sid": "cohort",   # retired v9.7.408 — lab-specific strain-series name in a general-purpose tool
}

#: Zip-name segments that a *historical* bundle may carry for a tier that has since been renamed.
#: Consumers that parse a filename back into a tier must accept these; producers must never emit one.
HISTORICAL_LABELS: dict[str, str] = {
    "SID-public": "cohort",
}

REQUIRED_TIERS: frozenset[str] = frozenset(t.name for t in TIERS if t.required)
OPTIONAL_PROMOTION_TIERS: frozenset[str] = frozenset(t.name for t in TIERS if not t.required)


class UnknownTier(ValueError):
    """Raised for a token that is neither canonical nor a known alias."""


def resolve(token: str) -> tuple[str, bool]:
    """Return (canonical_tier_name, used_deprecated_alias).

    Raises UnknownTier for anything unrecognised — a typo must never fall through to a default,
    because the tier decides what is stripped from a release.
    """
    t = (token or "").strip().lower()
    if t in CANONICAL:
        return t, False
    if t in ALIASES:
        return ALIASES[t], True
    raise UnknownTier(
        f"unknown tier {token!r}; expected one of {sorted(CANONICAL)} "
        f"(deprecated aliases still accepted: {sorted(ALIASES)})"
    )


def archive_label(tier: str) -> str:
    """The zip-name segment a NEW cut must emit for this tier (never a historical label)."""
    name, _ = resolve(tier)
    return CANONICAL[name].label


def archive_labels_including_historical(tier: str) -> list[str]:
    """Every zip-name segment that has ever denoted this tier, current label first.

    Use this when PARSING an existing archive name; use `archive_label` when NAMING a new one.
    """
    name, _ = resolve(tier)
    out = [CANONICAL[name].label]
    out += [lbl for lbl, canon in HISTORICAL_LABELS.items() if canon == name]
    return out


def describe(tier: str) -> str:
    name, _ = resolve(tier)
    return CANONICAL[name].summary


def _main() -> int:
    import argparse
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _console import emit  # noqa: E402

    p = argparse.ArgumentParser(description="Print the canonical release-tier vocabulary.")
    p.add_argument("tier", nargs="?", help="resolve a single tier token (canonical or alias)")
    a = p.parse_args()
    if a.tier:
        try:
            name, aliased = resolve(a.tier)
        except UnknownTier as exc:
            emit(f"ERROR: {exc}", file=sys.stderr)
            return 2
        note = f"  (deprecated alias for {name!r})" if aliased else ""
        emit(f'{a.tier} -> {name}{note}', f'  label   : {archive_label(name)}', f"  parses  : {', '.join(archive_labels_including_historical(name))}", f'  summary : {describe(name)}', sep="\n")
        return 0
    for t in TIERS:
        kind = "required" if t.required else "promotion"
        emit(f"{t.name:<8} {t.label:<26} {kind:<10} {t.summary}")
    if ALIASES:
        emit('', 'deprecated aliases (still resolvable so historical bundles stay readable):', sep="\n")
        for old, new in sorted(ALIASES.items()):
            emit(f"  {old} -> {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
