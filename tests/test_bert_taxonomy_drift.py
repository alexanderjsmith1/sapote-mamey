"""Bert-Taxonomy-Drift: the reconciled Bert Mode surface must carry the four-tier
status vocabulary and must NOT reintroduce the retired v9.4 three-bucket taxonomy.

Context: the Bert Mode status vocabulary was reconciled from the old three-bucket
form (Verified / Partially verified / Unverified leads) to the current four-tier
form (Verified / Partial / Policy / GenBank), which matches the standalone
`literature-digest` skill. This test is a drift anchor: if the retired phrases
reappear in the reconciled files, or the four tiers go missing from the SSOT doc,
STOP and reconcile before shipping.

The gate pins the vocabulary IN-BUNDLE. It cannot diff the external
`literature-digest` skill (not shipped in the bundle by design — self-containment),
so the sync direction is skill -> docs/BERT_MODE_PROTOCOL.md -> this pattern list.

Out of scope (known-divergent, pending a separate whole-section reconciliation —
do NOT add to RECONCILED until reconciled, or this gate blocks every cut):
  - docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md   (its own 5-section Eden workbook spec)
  - examples/citation_library_exemplar.md  (worked example organized by 3 buckets)
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# The SSOT for the Bert Mode status vocabulary.
SSOT = ROOT / "docs" / "BERT_MODE_PROTOCOL.md"

# Files reconciled to the four-tier vocabulary. Extend this list as more
# consumers (monolith, exemplar) are reconciled.
RECONCILED = [
    SSOT,
    ROOT / "docs" / "user_guides" / "operational_reference.md",
    ROOT / "prompts" / "CLAUDE_SYSTEM_PROMPT.md",
]

# Retired three-bucket phrases that must not appear in the reconciled surface.
STALE_PATTERNS = [
    r"partially verified",
    r"unverified lead",
]

# The current four-tier vocabulary the SSOT must define.
FOUR_TIERS = ["Verified", "Partial", "Policy", "GenBank"]


def _supersedes_lineset(lines):
    """Line numbers (1-indexed) inside the SSOT's `**Supersedes:**` paragraph.

    That note legitimately names the retired terms once to document the doc's own
    history; it runs from the `**Supersedes:**` line to the next blank line.
    """
    exempt, in_block = set(), False
    for lineno, line in enumerate(lines, 1):
        if "**Supersedes:**" in line:
            in_block = True
        if in_block:
            if line.strip() == "":
                break
            exempt.add(lineno)
    return exempt


def test_no_retired_taxonomy_in_reconciled_files():
    """None of the reconciled files may reintroduce the retired three-bucket terms."""
    hits = []
    for path in RECONCILED:
        if not path.exists():
            hits.append(f"MISSING FILE: {path.relative_to(ROOT)}")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        exempt = _supersedes_lineset(lines) if path == SSOT else set()
        for lineno, line in enumerate(lines, 1):
            if lineno in exempt:
                continue
            for pat in STALE_PATTERNS:
                if re.search(pat, line, re.IGNORECASE):
                    hits.append(f"{path.relative_to(ROOT)}:{lineno}: /{pat}/ -> {line.strip()}")
    assert not hits, "Retired three-bucket taxonomy present in reconciled files:\n" + "\n".join(hits)


def test_ssot_defines_four_tiers():
    """BERT_MODE_PROTOCOL.md must define all four current status tiers."""
    assert SSOT.exists(), f"SSOT missing: {SSOT}"
    text = SSOT.read_text(encoding="utf-8")
    missing = [t for t in FOUR_TIERS if f"**{t}**" not in text]
    assert not missing, f"Four-tier vocabulary incomplete in SSOT; missing: {missing}"
