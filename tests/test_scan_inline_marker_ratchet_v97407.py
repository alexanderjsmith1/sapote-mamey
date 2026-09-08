"""Prevent expansion of known inline detection-marker literals outside B2 registry coverage."""
from __future__ import annotations

import ast
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "mamey" / "source_scans.py"

# Measured from sealed v9.7.406.  The ten registry-backed libraries are
# deliberately excluded: their in-source literals are a tested fallback,
# not a second active definition.  Lower this ceiling whenever a remaining
# inline family is migrated only with a byte-identical parity receipt.
INLINE_MARKER_ASSIGNMENTS = frozenset({
    "PRIMARY_METABOLISM_PATTERNS", "VETO_CONTEXT_PATTERNS", "MOBILE_ELEMENT_PATTERNS",
    "_KS_ACTIVE_SITE", "_AT_ACTIVE_SITE", "QS_PRODUCT_LABELS", "QS_CDS_PATTERNS",
    "GLYCOSYLATED_COMPOUND_KEYWORDS", "_AMINOGLYCOSIDE_ANCHOR", "_DOIS_GENE",
    "_POLYENE_ANCHOR", "_ENEDIYNE_SPECIFIC", "_ENEDIYNE_GENERIC", "_PREV001_SIGNAL",
    "_KCB_CLASS_COMPAT",
})
BASELINE_INLINE_MARKER_LITERAL_COUNT = 264


def _assignment_name(node: ast.stmt) -> str | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _inline_marker_literals() -> dict[str, int]:
    parsed = ast.parse(SOURCE.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for node in parsed.body:
        name = _assignment_name(node)
        if name not in INLINE_MARKER_ASSIGNMENTS:
            continue
        value = node.value  # assignment types above always carry a value here
        counts[name] = sum(
            isinstance(item, ast.Constant) and isinstance(item.value, str)
            for item in ast.walk(value)
        )
    return counts


def test_no_new_inline_marker_assignment_is_added_outside_registry():
    assert set(_inline_marker_literals()) == INLINE_MARKER_ASSIGNMENTS


def test_inline_marker_literal_count_only_moves_down_with_registry_migration():
    assert sum(_inline_marker_literals().values()) <= BASELINE_INLINE_MARKER_LITERAL_COUNT
