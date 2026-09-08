"""test_tier_vocabulary_v97408.py — the tier rename must not touch data.

WHY THIS EXISTS
---------------
v9.7.408 renamed the release tier `sid` -> `cohort` (owner ruling 2026-09-04) because the old name
was specific to one lab's strain series in a general-purpose tool. `sid` means THREE different
things in this codebase and only the first is a tier:

  1. the tier token            -- renamed
  2. `SID####` strain IDs      -- real identifiers, public (Chevrette 2019); MUST NOT change
  3. the `'sid'` data key      -- "strain id" in strains.json, the master workbook and
                                  build_id_resolver.py's ("strain","sid","cohort_id") lookup;
                                  renaming it breaks the producer/consumer data contract

A textual `sid` -> `cohort` substitution would have corrupted (2) and (3). The rename was scoped to
tier-token positions, and this file is the proof: it fails if either data meaning ever moves. The
diff for a rename like this is too large to review by eye, which is exactly how a string-literal
corruption survived undetected in the v9.7.407 cut until a generated surface disagreed with the tree.
"""
from __future__ import annotations

import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import tier_vocabulary as tv  # noqa: E402


# ---------------------------------------------------------------- the vocabulary itself

def test_cohort_is_canonical_and_sid_is_a_deprecated_alias():
    assert "cohort" in tv.CANONICAL
    assert "sid" not in tv.CANONICAL, "sid must no longer be a canonical tier name"
    name, aliased = tv.resolve("sid")
    assert (name, aliased) == ("cohort", True)
    name, aliased = tv.resolve("cohort")
    assert (name, aliased) == ("cohort", False)


def test_required_tier_set_is_still_four():
    assert tv.REQUIRED_TIERS == {"code", "clean", "cohort", "merged"}
    assert tv.OPTIONAL_PROMOTION_TIERS == {"public"}


def test_unknown_tier_never_falls_through_to_a_default():
    # A typo must refuse, not silently pick a tier -- the tier decides what is stripped.
    with pytest.raises(tv.UnknownTier):
        tv.resolve("cohorts")
    with pytest.raises(tv.UnknownTier):
        tv.resolve("")


def test_new_cuts_emit_the_new_label_but_old_archives_still_parse():
    assert tv.archive_label("cohort") == "COHORT-public"
    assert tv.archive_label("sid") == "COHORT-public", "the alias must not resurrect the old label"
    parses = tv.archive_labels_including_historical("cohort")
    assert parses[0] == "COHORT-public"
    assert "SID-public" in parses, (
        "every bundle sealed up to v9.7.407 carries -SID-public-; dropping it from the parse set "
        "would make historical bundles unreadable by current tools"
    )


def test_labels_are_unique_and_prefix_collisions_are_resolved_longest_first():
    """`CODE` IS a prefix of `CODE-analysis-free`, and that is fine — but only because the archive
    regex tries the longer label first. This pins the ordering guarantee rather than forbidding the
    prefix, which the tier set has always had and does not need to lose."""
    labels = [t.label for t in tv.TIERS] + list(tv.HISTORICAL_LABELS)
    assert len(labels) == len(set(labels)), "two tiers share a zip label"

    prefixed = [(a, b) for a in labels for b in labels if a != b and b.startswith(a)]
    assert prefixed, "expected at least the known CODE / CODE-analysis-free pair"

    import importlib.util
    spec = importlib.util.spec_from_file_location("_ctp2", ROOT / "tools" / "check_tier_parity.py")
    ctp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ctp)
    ordered = ctp._ALL_ARCHIVE_LABELS
    for short, long in prefixed:
        assert ordered.index(long) < ordered.index(short), (
            f"{long!r} must be tried before {short!r} or a filename would bind to the wrong tier"
        )


# ---------------------------------------------------------------- the consumers agree

def test_check_tier_parity_reads_the_vocabulary_not_its_own_copy():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_ctp", ROOT / "tools" / "check_tier_parity.py")
    ctp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ctp)
    assert ctp.REQUIRED_TIERS == set(tv.REQUIRED_TIERS)
    # both the current and the historical archive name must bind to the same tier
    for fname, expect in (
        ("sapote-mamey-v9.7.408-COHORT-public-20260904v97408a.zip", "cohort"),
        ("sapote-mamey-v9.7.407-SID-public-20260903v97407a.zip", "cohort"),
        ("sapote-mamey-v9.7.407-CODE-analysis-free-20260903v97407a.zip", "clean"),
        ("sapote-mamey-v9.7.407-CODE-20260903v97407a.zip", "code"),
    ):
        m = ctp.TIER_ARCHIVE_RE.match(fname)
        assert m, f"archive name did not parse: {fname}"
        assert ctp.TIER_LABELS[m.group("tier").lower()] == expect, fname


def test_cut_script_names_the_new_tier_and_still_accepts_the_alias():
    sh = (ROOT / "tools" / "make_public_tier.sh").read_text(encoding="utf-8")
    assert 'cohort) NAME="sapote-mamey-v${VERSION}-COHORT-public-${STAMP}.zip"' in sh
    assert "TIER=cohort" in sh, "the sid alias must still resolve inside the cut script"
    assert 'NAME="sapote-mamey-v${VERSION}-SID-public-' not in sh, \
        "a new cut must never emit the retired label"


# ---------------------------------------------------------------- the data must not have moved

_SHIPPED_DIRS = ("mamey", "tools", "deliverable_tools", "tests", "docs")


def _shipped_files():
    for d in _SHIPPED_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in (".py", ".md", ".json", ".tsv", ".csv", ".sh"):
                if "__pycache__" in p.parts or "_vendor" in p.parts:
                    continue
                yield p


def test_strain_identifiers_were_not_renamed():
    """SID#### identifiers are real, public data. The rename must not have touched one."""
    survivors = 0
    for p in _shipped_files():
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        survivors += len(re.findall(r"\bSID\d{3,}\b", text))
        assert not re.search(r"\bCOHORT\d{3,}\b", text), (
            f"{p.relative_to(ROOT)} contains a COHORT#### token — a strain identifier was rewritten "
            f"by the tier rename. SID#### is data, not a tier name."
        )
    assert survivors > 0, (
        "expected SID#### strain identifiers to survive the rename somewhere in the shipped tree; "
        "finding none suggests they were rewritten wholesale"
    )


def test_the_sid_data_key_was_not_renamed():
    """`sid` as a dict/column key means "strain id" and is a producer/consumer contract.

    Deliberately NOT anchored to a list of filenames. An earlier draft of this test named three
    known consumers, which (a) made it brittle against an unrelated rename and (b) tripped the
    orphan-gate wiring invariant, because naming an OPERATOR_ONLY tool inside a test file is how
    that invariant detects a tool gaining tests. Counting the behaviour instead of naming the files
    is both more robust and honest about what is being asserted -- and it avoids the very
    name-anchoring defect this cut's findings are about.
    """
    key_access = re.compile(r"""\[['"]sid['"]\]|['"]sid['"]\s*[,:)]""")
    cohort_key_access = re.compile(r"""\[['"]cohort['"]\]""")

    users, wrongly_renamed = 0, []
    for p in (ROOT / "tools").glob("*.py"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if key_access.search(text):
            users += 1
        elif cohort_key_access.search(text) and "cohort_id" not in text:
            # a file that lost its 'sid' key and gained a bare 'cohort' one is the exact corruption
            # a textual rename would cause
            wrongly_renamed.append(p.name)

    assert not wrongly_renamed, (
        f"these files appear to have had the 'sid' STRAIN-ID key rewritten to 'cohort' by the tier "
        f"rename: {wrongly_renamed}. The tier is named cohort; the data key is still sid."
    )
    assert users >= 3, (
        f"only {users} tools still read the 'sid' strain-id key; before the rename several did. "
        f"A drop here means the data contract moved when only the tier label should have."
    )


def test_no_shipped_file_claims_the_tier_runs_a_sid_scrub():
    """The SID uniformity scrub was removed at v9.7.364; no shipped text may still describe it.

    The stale comment that survived in make_public_tier.sh sent a v9.7.408 design review down the
    wrong path before the live code was read. A comment describing deleted behaviour is a check that
    stopped checking, in prose.
    """
    sh = (ROOT / "tools" / "make_public_tier.sh").read_text(encoding="utf-8")
    for claim in ("sid does its own SID", "anonymization pass (3c below)"):
        assert claim not in sh, f"stale behaviour claim still present in the cut script: {claim!r}"
