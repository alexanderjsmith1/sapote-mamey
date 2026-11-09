# Synthetic regression inputs only.
"""BGC rows outside the strain roster no longer steer the size profile's top-eight class choice.

Before: their length counted toward picking the eight classes, but they had no strain row, so they
vanished from every displayed total.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("size_profile_464r3b", ROOT / "tools/build_size_profile.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bank(tmp_path):
    bank = tmp_path / "bank"
    bank.mkdir()
    strains = {"S1": {"contigs": 5}, "S2": {"contigs": 50}}
    bgcs = []
    # nine rostered classes with small lengths
    for i, cls in enumerate(["NRPS", "T1PKS", "terpene", "lanthipeptide", "siderophore", "betalactone",
                             "T3PKS", "ectoine", "lassopeptide"]):
        bgcs.append({"sid": "S1", "bgc_id": f"BGC{i:03d}", "products": [cls], "length_kb": 10 + i})
    # a large unrostered row of a tenth class
    bgcs.append({"sid": "GHOST", "bgc_id": "BGC100", "products": ["phosphonate"], "length_kb": 500})
    (bank / "bgc_data.json").write_text(json.dumps({"strains": strains, "bgcs": bgcs}), encoding="utf-8")
    return bank


def test_unrostered_rows_do_not_choose_classes_and_are_reported(tmp_path):
    mod = _load()
    unmatched = {}
    strains, sids, cols, siz, cnt = mod.compute(str(_bank(tmp_path)), unmatched=unmatched)
    assert unmatched == {"GHOST": 1}
    assert "GHOST" not in siz
    assert not any("phosphonate" in c.lower() for c in cols)
    assert len(cols) == 8


def test_class_choice_ignores_unrostered_rows_without_the_report_argument(tmp_path):
    strains, sids, cols, siz, cnt = _load().compute(str(_bank(tmp_path)))
    assert not any("phosphonate" in c.lower() for c in cols)
