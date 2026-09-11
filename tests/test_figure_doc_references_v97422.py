"""SEXTANT_422n — the figure docs must name files that exist, and must not call
the CURRENT deliverable menu retired.

Two defects motivated this, both found in v9.7.421:

1. Four pages wrote "the legacy Diner Menu (`docs/DELIVERABLE_MENU.md`) is retired".
   `docs/DELIVERABLE_MENU.md` is CANONICAL_MENU_PATH — generated from
   mamey/data/deliverables_registry.json, stamped with the current bundle, and
   fail-closed by tools/generate_deliverables_menu.py --check.  The retired file
   is LEGACY_MENU_PATH = docs/DELIVERABLE_MENU_v97146.md.  The prose named the
   wrong one, so a reader was told the live menu was dead.

2. The same pages referenced `sapote_ggplot2.R` / `sapote_ggtree.R` by bare
   filename.  A bare filename cannot be checked by the repo's relative-link
   screen, which is why two authored deliverables could be promised for seven
   cuts without anyone noticing they had never landed.  Referencing them by
   their `tools/` path makes the promise falsifiable.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    "CURRENT_DOCS_INDEX.md",
    "docs/FIGURE_FACTORY_NEXT.md",
    "docs/figure_factory/README.md",
    "wiki/Figure-Factory-Preflight-and-Methods-Manual.md",
]
_R_PATH = re.compile(r"`(tools/[A-Za-z0-9_./-]+\.R)`")
_BARE_R = re.compile(r"`(sapote_gg[a-z0-9_]*\.R)`")


def _present():
    missing = [rel for rel in DOCS if not (ROOT / rel).is_file()]
    assert not missing, missing
    return DOCS


def test_referenced_r_scripts_exist():
    missing = []
    for rel in _present():
        for hit in _R_PATH.findall((ROOT / rel).read_text(encoding="utf-8")):
            if not (ROOT / hit).is_file():
                missing.append(f"{rel} -> {hit}")
    assert not missing, "docs reference R scripts that do not ship: " + "; ".join(missing)


def test_no_bare_r_filenames():
    bare = []
    for rel in _present():
        for hit in _BARE_R.findall((ROOT / rel).read_text(encoding="utf-8")):
            bare.append(f"{rel} -> {hit}")
    assert not bare, "reference R templates by their tools/ path so the claim is checkable: " + "; ".join(bare)


def test_current_menu_is_not_called_retired():
    """The retirement claim must attach to the version-pinned file, not the live one.

    Line-level matching is too crude here: the wiki manual is one long paragraph
    that legitimately names both files.  Anchor on the canonical path itself and
    look only at the text that immediately follows it.
    """
    canonical = re.compile(r"`docs/DELIVERABLE_MENU\.md`")
    bad = []
    for rel in _present():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for m in canonical.finditer(text):
            window = text[m.end():m.end() + 100]
            if "retire" in window.lower():
                bad.append(f"{rel}: ...{window.strip()[:90]}")
    assert not bad, (
        "docs/DELIVERABLE_MENU.md is CANONICAL_MENU_PATH and is current; the retired "
        "file is docs/DELIVERABLE_MENU_v97146.md. Offending text: " + " | ".join(bad)
    )
