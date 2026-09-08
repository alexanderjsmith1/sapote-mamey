"""test_bypass_guard_registry.py — v9.7.62

Guards against a recurrence of Audit Flag A: standing rules with action=none or action=flag
in the registry are not caught by _downgrade_rules() (which only matches rules with
action=downgrade). They are instead detected by the direct product-annotation scan in the
triage loop. That scan enforces the downgrade, but _BYPASS_COMMITTED_CLASS_GUARD must
also contain them so they fire on committed-class clusters.

If a new annotation-domain standing rule is added to the registry with action=none or
action=flag but is NOT added to _BYPASS_COMMITTED_CLASS_GUARD, Audit Flag A recurs:
the rule is enforced for non-committed clusters but silently skipped for committed ones.
"""
import json
from pathlib import Path
from mamey.scoring import _BYPASS_COMMITTED_CLASS_GUARD

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "mamey" / "data" / "rules_registry.json"

# These registry rules are explicitly excluded from the bypass requirement because they
# are either retired (BRYO-HGT-001), primary-metabolism (handled separately), or
# action=downgrade (caught by _downgrade_rules() on committed-class clusters).
_BYPASS_EXEMPT = {
    "BRYO-HGT-001",          # retired — patterns still in file but status=retired
    "ENEDIYNE-KCB",           # action=flag but handles enediyne veto, not standing-rule downgrade
    "PRIMARY-METABOLISM",     # handled by separate primary_metabolism scan, not bypass needed
    "SACCHARIDE",             # action=downgrade — caught by _downgrade_rules(), bypass not needed
}


def _load_registry_rules() -> list[dict]:
    data = json.loads(REGISTRY_PATH.read_text())
    return data.get("rules", [])


def test_bypass_guard_covers_all_non_blocking_registry_rules():
    """Every active registry rule with action=none or action=flag (annotation-domain rules)
    must be in _BYPASS_COMMITTED_CLASS_GUARD, unless explicitly exempt.

    This test prevents a recurrence of Audit Flag A: a rule that uses direct product-scan
    enforcement (because the registry marks it non-blocking for _downgrade_rules) but is
    not in the bypass set will silently fail on committed-class BGCs.
    """
    rules = _load_registry_rules()
    # Rules that need to be in the bypass set:
    # - action in {none, flag}: not caught by _downgrade_rules()
    # - status != retired: retired rules are inert
    # - id not in _BYPASS_EXEMPT: explicit carve-outs
    needs_bypass = {
        r["id"].upper()
        for r in rules
        if r.get("action", "") in {"none", "flag"}
        and r.get("status", "") != "retired"
        and r["id"].upper() not in _BYPASS_EXEMPT
    }
    missing = needs_bypass - _BYPASS_COMMITTED_CLASS_GUARD
    assert not missing, (
        f"Registry rules with action=none/flag are NOT in _BYPASS_COMMITTED_CLASS_GUARD:\n"
        f"  {sorted(missing)}\n"
        f"Add them to _BYPASS_COMMITTED_CLASS_GUARD in mamey/scoring.py, or add to "
        f"_BYPASS_EXEMPT in this test if they have a different enforcement path.\n"
        f"This prevents a recurrence of Audit Flag A (v9.7.58)."
    )


def test_bypass_guard_contains_no_phantom_rules():
    """Every rule ID in _BYPASS_COMMITTED_CLASS_GUARD must exist in the registry.
    Guards against stale entries after registry cleanup.
    """
    rules = _load_registry_rules()
    registry_ids = {r["id"].upper() for r in rules}
    phantom = {r.upper() for r in _BYPASS_COMMITTED_CLASS_GUARD} - registry_ids
    assert not phantom, (
        f"_BYPASS_COMMITTED_CLASS_GUARD contains IDs not in the registry:\n"
        f"  {sorted(phantom)}\n"
        f"Remove stale entries from _BYPASS_COMMITTED_CLASS_GUARD in mamey/scoring.py."
    )


def test_saccharide_is_not_in_bypass_guard():
    """SACCHARIDE uses action=downgrade and is handled by _downgrade_rules() for committed
    clusters via the OWN_PRODUCTS_ONLY path — it correctly does NOT need the bypass."""
    assert "SACCHARIDE" not in _BYPASS_COMMITTED_CLASS_GUARD, (
        "SACCHARIDE should not be in _BYPASS_COMMITTED_CLASS_GUARD — "
        "it fires via _downgrade_rules() which already respects the committed-class guard "
        "for SACCHARIDE (it's in _OWN_PRODUCTS_ONLY, not _BYPASS_COMMITTED_CLASS_GUARD)."
    )
