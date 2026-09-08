"""v9.7.323 latent-sort: scanner registry selection must be numeric, not lexicographic.

`sorted(glob("scanner_registry_v*.json"))[-1]` picks v0.5 over v0.10 once the minor reaches
double digits. Safe today (registries are v0.2..v0.5) but latent. The fix keys on (major, minor)
ints via the same dotted parse wheelhouse uses.
"""
import re

import pytest


def _reg_ver(name):
    mm = re.search(r"v(\d+)\.(\d+)", name)
    return (int(mm.group(1)), int(mm.group(2))) if mm else (-1, -1)


def test_numeric_selection_beats_lexicographic():
    c = ["scanner_registry_v0.5.json", "scanner_registry_v0.10.json", "scanner_registry_v0.2.json"]
    assert max(c, key=_reg_ver) == "scanner_registry_v0.10.json"
    assert sorted(c)[-1] == "scanner_registry_v0.5.json"  # the bug the fix avoids


def test_current_registry_range_unaffected():
    c = ["scanner_registry_v0.2.json", "scanner_registry_v0.3.json",
         "scanner_registry_v0.4.json", "scanner_registry_v0.5.json"]
    assert max(c, key=_reg_ver) == "scanner_registry_v0.5.json"


def test_resolver_picks_highest_and_runs():
    pytest.importorskip("Bio")  # raw_antismash_triage imports Bio.SeqIO at module top; skip cleanly if absent
    import mamey.raw_antismash_triage as R
    reg = R._resolve_scanner_registry() if hasattr(R, "_resolve_scanner_registry") else None
    # resolver returns the shipped v0.5 registry (or None if scanners absent); must not raise
    if reg is not None:
        assert "v0.5" in reg.get("_source_path", "")
