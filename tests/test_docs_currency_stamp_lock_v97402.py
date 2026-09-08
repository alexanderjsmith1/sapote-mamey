"""Currency-stamp lock (.402, ROSTER_402 seed #2 — Black Cherry-4).

Verified field failure: `docs/EXTERNAL_TOOL_INVENTORY.md` carried a stale 9.7.400 currency
header through Black Cherry's .401 composition and was caught BY HAND at the seal gate — no
sync_version rule owned it and no test pinned it (the same rotting-field class that let
CURRENT_DOCS_INDEX.md freeze three times before v9.7.371 adopted it). Reproduced this
session: with the header staled to 9.7.400, the sealed `sync_version --check` still passed.

The paired sync_version rules adopt the "**Bundle vX · engine Mamey Y · compiled DATE**"
header (inventory + its wiki twin) so `--apply` re-stamps it at cut time and `--check` fails
on drift; these tests lock the stamps live-current the wiki-sidebar way, and a discovery
sweep forces any FUTURE doc that adopts the same header form into this gate instead of
starting a new unowned field.

Deliberately out of scope: table rows recording versions *actually run* (the inventory's
"Version (verified)" column) are provenance records, owned by the tool-master/human review —
a lock test must never machine-assert them current.
"""
from __future__ import annotations

import re
from pathlib import Path

import mamey

ROOT = Path(__file__).resolve().parents[1]

STAMPED = [
    "docs/EXTERNAL_TOOL_INVENTORY.md",
    "wiki/External-Tools-and-Databases.md",
]

HEADER = re.compile(
    r"\*\*Bundle v(\d+(?:\.\d+)*[a-z]*) · engine Mamey (\d+(?:\.\d+)*[a-z]*)"
    r" · compiled (\d{4}-\d{2}-\d{2})\*\*"
)


def _read(rel: str) -> str:
    p = ROOT / rel
    assert p.is_file(), f"{rel} missing from the bundle"
    return p.read_text(encoding="utf-8", errors="replace")


def test_currency_headers_present_and_unique():
    for rel in STAMPED:
        hits = HEADER.findall(_read(rel))
        assert len(hits) == 1, f"{rel}: expected exactly one currency header, found {len(hits)}"


def test_currency_headers_match_live_versions():
    """The stamp must match the LIVE versions, not merely exist (wiki-sidebar discipline)."""
    for rel in STAMPED:
        m = HEADER.search(_read(rel))
        assert m, f"{rel}: currency header missing"
        bundle, engine, _date = m.groups()
        assert bundle == mamey.BUNDLE_VERSION, (
            f"{rel}: stale bundle stamp v{bundle} (live is v{mamey.BUNDLE_VERSION})"
        )
        assert engine == mamey.__version__, (
            f"{rel}: stale engine stamp {engine} (live is {mamey.__version__})"
        )


def test_no_unregistered_doc_adopts_the_stamp_form():
    """Any new doc using this header form must join STAMPED (and a sync_version rule) —
    a currency stamp with no owner is how the .401 hand-catch happened."""
    offenders = []
    for p in ROOT.rglob("*.md"):
        rel = p.relative_to(ROOT).as_posix()
        if ".retired" in rel or rel in STAMPED:
            continue
        if HEADER.search(p.read_text(encoding="utf-8", errors="replace")):
            offenders.append(rel)
    assert not offenders, (
        "doc(s) carry the currency-header form but are not in the stamp gate "
        f"(add to STAMPED + tools/sync_version.py RULES): {offenders}"
    )


def test_sync_version_owns_both_stamps():
    """The stamps must be machine-bumped at cut time, not merely gated: both files appear
    in tools/sync_version.py RULES."""
    src = (ROOT / "tools" / "sync_version.py").read_text(encoding="utf-8")
    for rel in STAMPED:
        assert f'("{rel}"' in src, f"tools/sync_version.py has no rule for {rel}"


# --- v9.7.413 (Goldenrod) — the SECOND currency convention -------------------------------
# STAMPED/HEADER above govern one form: "**Bundle vX · engine Mamey Y · compiled DATE**".
# A parallel convention exists in prose — "current to bundle vX / engine Mamey Y" — and nothing
# owned it. Three wiki guides used it (a footer, a capitalised standalone line, and one
# MID-SENTENCE) and had drifted to v9.7.401 / 1.9.143 while the bundle shipped 9.7.412 / 1.9.150,
# eleven cuts apart. These are deliberately a separate registry: the two forms are different
# strings with different owners, and folding them together would make HEADER's tests fail.
CLAIM = re.compile(r"[Cc]urrent to bundle v(\d+(?:\.\d+)*[a-z]*) / engine Mamey (\d+(?:\.\d+)*[a-z]*)")
CLAIMED = [
    "wiki/User-Manual.md",
    "wiki/Concepts-Q-and-A.md",
    "wiki/Encyclopedia.md",
    "docs/GUIDE/01_User_Manual.md",
    "docs/GUIDE/06_Concepts_QandA.md",
]


def test_every_currency_claim_is_live_current():
    """A claim must carry the LIVE versions -- the failure this catches is silent drift."""
    for rel in CLAIMED:
        p = ROOT / rel
        if not p.exists():
            continue
        hits = list(CLAIM.finditer(p.read_text(encoding="utf-8", errors="replace")))
        assert hits, f"{rel}: currency claim vanished -- its sync_version rule would silently no-op"
        for m in hits:
            assert m.group(1) == mamey.BUNDLE_VERSION, f"{rel}: stale bundle in {m.group(0)!r}"
            assert m.group(2) == mamey.__version__, f"{rel}: stale engine in {m.group(0)!r}"


def test_no_unregistered_doc_makes_a_currency_claim():
    """Same discipline HEADER already has, applied to the prose form it does not match."""
    offenders = []
    for p in ROOT.rglob("*.md"):
        rel = p.relative_to(ROOT).as_posix()
        if ".retired" in rel or rel in CLAIMED:
            continue
        if CLAIM.search(p.read_text(encoding="utf-8", errors="replace")):
            offenders.append(rel)
    assert not offenders, (
        "doc(s) assert a currency claim with no owner "
        f"(add to CLAIMED + tools/sync_version.py RULES): {offenders}"
    )
