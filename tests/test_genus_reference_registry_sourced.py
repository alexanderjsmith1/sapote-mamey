"""v9.7.101 P3: genus_reference's STANDING_EXCLUSIONS must derive from the rules
registry (the SSOT), not a hardcoded set that can drift from it.

The pre-v9.7.101 hardcode wrongly excluded NAPAA (now registry-neutral) and
hgle-ks (registry "noted/flag", not excluded). These tests pin the registry as
the determinant so that split-brain can't recur.
"""
import json
from pathlib import Path

import mamey.genus_reference as g

REG = Path(g.__file__).resolve().parent / "data" / "rules_registry.json"


def _registry_status(target_id):
    reg = json.loads(REG.read_text(encoding="utf-8"))
    found = {}

    def walk(o):
        if isinstance(o, dict):
            if o.get("id") == target_id:
                found["status"] = o.get("status")
                found["action"] = o.get("action")
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(reg)
    return found


def test_saccharide_excluded_because_registry_says_so():
    st = _registry_status("SACCHARIDE")
    assert st.get("status") == "excluded" or st.get("action") == "drop"
    assert "saccharide" in g.STANDING_EXCLUSIONS


def test_napaa_not_excluded_because_registry_neutral():
    st = _registry_status("NAPAA")
    assert st.get("status") == "neutral", "registry NAPAA is expected to be neutral"
    assert "NAPAA" not in g.STANDING_EXCLUSIONS, (
        "NAPAA is registry-neutral and must not be in the derived exclusion set"
    )


def test_hgleks_not_excluded_because_registry_flag_only():
    st = _registry_status("HGLE-KS-PREV-001")
    # noted/flag, not excluded
    assert st.get("status") != "excluded" and st.get("action") != "drop"
    assert "hgle-ks" not in g.STANDING_EXCLUSIONS


def test_primary_metabolism_excluded_keeps_fatty_acid():
    st = _registry_status("PRIMARY-METABOLISM")
    assert st.get("status") == "excluded" or st.get("action") == "drop"
    assert "fatty_acid" in g.STANDING_EXCLUSIONS


def test_nocardia_bank_filtering_unchanged_by_derivation():
    # The bank uses no NAPAA/hgle-ks bgc_class token, so the corrected exclusion set
    # filters exactly the same rows — the card's byte-identical requirement.
    classes = {r["bgc_class"] for r in g.nocardia_class_prevalence()}
    assert "NAPAA" not in classes and "hgle-ks" not in classes
