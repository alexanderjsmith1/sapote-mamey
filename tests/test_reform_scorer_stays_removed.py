"""v9.7.355 — regression pin: `_reform_scorer.py` and the `kcb_source_precedence_and_rank_fix.patch`
must STAY removed.

History: both were removed once, then reappeared in the .352 -> .353 hygiene miss, and were finally
removed at BASE level in the .354 candidate (see CHANGELOG: "completes a premature .353 claim"). This test
pins that removal so a future re-vendor or a stale patch-apply can't quietly bring either back — the failure
mode that cost two cuts. It asserts on three surfaces: the file tree, and both authoritative manifests.

Cheap, offline, no imports of the module under test (it must not exist).
"""
from __future__ import annotations
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The two artifacts that must never come back.
# v9.7.355 seal fix: anchor on the exact artifact FILENAMES. A bare `_reform_scorer` substring also
# matches this test's own path (`tests/test_reform_scorer_stays_removed.py`) once TIER_MANIFEST and
# SOURCE_CHECKSUMS are regenerated at seal — a self-referential false positive that is invisible in a
# candidate tree carrying the previous cut's stale manifests, and only fires in the shipped artifact.
_FORBIDDEN = re.compile(r"_reform_scorer\.py|kcb_source_precedence_and_rank_fix\.patch", re.IGNORECASE)

_MANIFESTS = ("TIER_MANIFEST.txt", "SOURCE_CHECKSUMS_SHA256.txt", "MODULE_MANIFEST.txt")


def test_reform_scorer_module_absent():
    """The engine module must not exist under mamey/."""
    assert not (ROOT / "mamey" / "_reform_scorer.py").exists(), \
        "mamey/_reform_scorer.py reappeared — it was removed at base in the .354 cut; do not re-vendor it."


def test_kcb_precedence_patch_absent():
    """No kcb_source_precedence patch/diff anywhere in the tree."""
    hits = [p for p in ROOT.rglob("*kcb_source_precedence*")]
    assert not hits, f"kcb_source_precedence patch reappeared: {[str(p.relative_to(ROOT)) for p in hits]}"


def test_manifests_do_not_list_removed_artifacts():
    """Neither artifact may be listed in TIER_MANIFEST / SOURCE_CHECKSUMS / MODULE_MANIFEST."""
    offenders = []
    for name in _MANIFESTS:
        f = ROOT / name
        if not f.exists():
            continue
        for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            if _FORBIDDEN.search(line):
                offenders.append(f"{name}:{i}: {line.strip()}")
    assert not offenders, "removed artifacts re-listed in a manifest:\n" + "\n".join(offenders)
