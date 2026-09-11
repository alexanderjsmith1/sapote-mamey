"""test_manifest_schema.py — canonical manifest accessor + phantom-schema guard.

The session_resume-class bug: code read `manifest.json["assembly_tier"]` (a field
that isn't there) and silently got None. These tests pin the accessor's behavior,
prove the guard raises on a hallucinated field, and (AST lint) flag any NEW raw
manifest field access that bypasses the canonical accessor with an undeclared key.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from mamey.manifest_schema import (
    read_manifest_field,
    validate_manifest_keys,
    UnknownManifestField,
    MANIFEST_FIELDS,
    MANIFEST_SHORT_FIELDS,
    F_ASSEMBLY_TIER,
    F_CORRECTED_BGCS,
)

MAMEY = Path(__file__).resolve().parent.parent / "mamey"


# ---------------- accessor behavior ----------------

def test_reads_flat_from_manifest_short():
    ms = {"assembly_tier": "GOOD", "corrected_bgcs": 44}
    assert read_manifest_field(F_ASSEMBLY_TIER, manifest_short=ms) == "GOOD"
    assert read_manifest_field(F_CORRECTED_BGCS, manifest_short=ms) == 44


def test_falls_back_to_canonical_full_manifest_locations():
    """Use the locations written by MameyRun.to_dict(), not a fabricated shape."""
    man = {
        "assembly": {"n50": 5000, "contigs": 12},
        "bgc_counts": {"assembly_tier": "MODERATE", "interior_pct": 73.5},
    }
    assert read_manifest_field(F_ASSEMBLY_TIER, manifest=man) == "MODERATE"
    assert read_manifest_field("interior_pct", manifest=man) == 73.5
    assert read_manifest_field("n50", manifest=man) == 5000
    assert read_manifest_field("contigs", manifest=man) == 12


def test_falls_back_to_nested_bgc_counts():
    man = {"bgc_counts": {"corrected": 28.5, "raw": 51}}
    assert read_manifest_field(F_CORRECTED_BGCS, manifest=man) == 28.5
    assert read_manifest_field("raw_bgcs", manifest=man) == 51


def test_manifest_short_wins_over_nested():
    ms = {"assembly_tier": "GOOD"}
    man = {"assembly": {"tier": "POOR"}}
    assert read_manifest_field(F_ASSEMBLY_TIER, manifest=man, manifest_short=ms) == "GOOD"


def test_default_when_absent():
    assert read_manifest_field(F_ASSEMBLY_TIER, manifest={}, default="UNKNOWN") == "UNKNOWN"


# ---------------- the phantom-schema guard (the core fix) ----------------

def test_hallucinated_field_raises():
    """A typo'd / invented field name fails LOUD, not silent-None."""
    with pytest.raises(UnknownManifestField):
        read_manifest_field("assembly_teir")  # typo
    with pytest.raises(UnknownManifestField):
        read_manifest_field("assemblyTier")   # wrong casing/name
    with pytest.raises(UnknownManifestField):
        read_manifest_field("tier")            # the bare nested key is not the canonical name


def test_declared_fields_do_not_raise():
    for f in list(MANIFEST_FIELDS)[:5] + list(MANIFEST_SHORT_FIELDS)[:5]:
        # should return None/default, never raise
        read_manifest_field(f, manifest={}, manifest_short={})


# ---------------- real-package validation ----------------

def _find_real_manifest():
    """Use a real gold package if present in the run tree; else skip."""
    for base in [Path("/data/mamey-local/laur/runs_wired/S_laurentii/package"),
                 Path("/data/mamey-local/laur/runs_gold/S_laurentii/package")]:
        m = base / "manifest.json"
        if m.exists():
            return m
    return None


def test_real_manifest_keys_are_declared():
    """Every top-level key in a real gold manifest must be in the declared schema."""
    m = _find_real_manifest()
    if m is None:
        pytest.skip("no real gold package available in this environment")
    manifest = json.loads(m.read_text(encoding="utf-8"))
    unknown = validate_manifest_keys(manifest)
    assert unknown == [], f"real manifest has keys not in MANIFEST_FIELDS: {unknown}"


def test_real_manifest_short_keys_are_declared():
    m = _find_real_manifest()
    if m is None:
        pytest.skip("no real gold package available")
    ms_path = m.parent / "manifest_short.json"
    if not ms_path.exists():
        pytest.skip("no manifest_short.json")
    ms = json.loads(ms_path.read_text(encoding="utf-8"))
    unknown = [k for k in ms if k not in MANIFEST_SHORT_FIELDS]
    assert unknown == [], f"real manifest_short has undeclared keys: {unknown}"


# ---------------- AST lint: the guard that would have caught session_resume ----------------

# field names that, if accessed as a RAW literal on a manifest-like var, are the
# session_resume trap (top-level manifest.json access to a field that isn't there).
_TRAP_LITERALS = {"assembly_tier", "interior_pct", "corrected_bgcs", "raw_bgcs", "n50", "contigs"}
_MANIFEST_VARNAMES = {"manifest", "man", "ms", "manifest_short", "short", "_manifest"}
# files allowed to reference the trap literals (the schema module defines them;
# the accessor + tests legitimately use them)
_ALLOWED = {"manifest_schema.py"}


def _raw_manifest_trap_hits(pyfile: Path) -> list[str]:
    """Find `<manifestvar>.get("assembly_tier")` / `<manifestvar>["assembly_tier"]`
    for trap literals — raw access that should go through read_manifest_field()."""
    try:
        tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    hits = []

    # collect subscript nodes that are assignment TARGETS (writes, not manifest reads)
    # e.g. `ms["assembly_tier"] = ...` builds a local dict; it is not a manifest read.
    _assign_targets = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            tgts = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in tgts:
                if isinstance(t, ast.Subscript):
                    _assign_targets.add(id(t))

    class V(ast.NodeVisitor):
        def visit_Subscript(self, node):
            # var["assembly_tier"] — but not when it is an assignment target (a write)
            if (id(node) not in _assign_targets
                    and isinstance(node.value, ast.Name)
                    and node.value.id in _MANIFEST_VARNAMES):
                key = getattr(node.slice, "value", None)
                if isinstance(key, str) and key in _TRAP_LITERALS:
                    hits.append(f"{node.value.id}[{key!r}] @L{node.lineno}")
            self.generic_visit(node)

        def visit_Call(self, node):
            # var.get("assembly_tier")
            if (isinstance(node.func, ast.Attribute) and node.func.attr == "get"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in _MANIFEST_VARNAMES
                    and node.args and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value in _TRAP_LITERALS):
                hits.append(f"{node.func.value.id}.get({node.args[0].value!r}) @L{node.lineno}")
            self.generic_visit(node)

    V().visit(tree)
    return hits


def test_ast_lint_reports_raw_trap_access():
    """Inventory raw trap-field access across mamey/. This is the drift detector:
    it does not hard-fail today (the codebase predates the accessor) but pins the
    current set so a NEW raw access is visible in review. The list is the migration
    backlog for Cut A follow-up.
    """
    offenders = {}
    for py in MAMEY.rglob("*.py"):
        if py.name in _ALLOWED or "__pycache__" in str(py):
            continue
        h = _raw_manifest_trap_hits(py)
        if h:
            offenders[py.name] = h
    # The guard's job right now: make the backlog visible and bounded. Assert it
    # doesn't GROW past the known set by pinning a ceiling; tighten to 0 after migration.
    total = sum(len(v) for v in offenders.values())
    # v9.7.160: migrated 27 of 28 raw accesses to read_manifest_field() across 7 modules
    # (session_resume, compile_report, cohort_figures, cohort_figures_d, package_addons_html,
    # package_inspector, modeb_template_emitter). Lint now skips assignment targets (dict
    # construction is not a manifest read). The 1 remaining reads a locally RECONSTRUCTED
    # dict (cohort_figures `if ms["raw_bgcs"] is None`), not a manifest source. Ceiling 2 =
    # that 1 + headroom; a NEW raw manifest-source read trips this immediately.
    assert total <= 2, (
        f"raw manifest trap-field access count rose to {total}; "
        f"new code should use read_manifest_field(). Offenders: {offenders}")
