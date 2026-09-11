"""Test the First-Pass-Scans page renderer (tools/build_first_pass_scans.py).

Verifies it renders all eight scan sections from a manifest dict, flags KCB truncation-inflation
(≤3-protein anchor), and surfaces the bldA tier distribution + claim ceilings — without re-scanning.

Standalone: python3 tests/test_first_pass_scans.py
"""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

_TOOL = Path(__file__).resolve().parent.parent / "tools" / "build_first_pass_scans.py"
_spec = importlib.util.spec_from_file_location("build_first_pass_scans", _TOOL)
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)

_MANIFEST = {
    "display_name": "Test strain", "workflow_version": "Mamey v1.9.15",
    "bgcs": [
        {"bgc_id": "BGC01", "kcb_top": "Realistic whole-cluster | Type: NRPS", "kcb_cumulative": 20000, "kcb_protein_hits": 25},
        {"bgc_id": "BGC02", "kcb_top": "Inflated anchor | Type: T1PKS", "kcb_cumulative": 33000, "kcb_protein_hits": 2},
    ],
    "hallucination_traps_triggered": [],
    "resistance_gene_summary": {"counts": {"APH_AAC": 7, "VanHAX_like": 0, "Erm_methylase": 1}},
    "source_scans": {
        "flbr": {"counts": {"mod_KS": 5}, "flbr_grade": "STRONG", "genome_wide_ks_like_count": 12,
                 "claim_safety": "confirm with HMMER"},
        "umed": {"counts": {"LanP_S8_protease": 3}, "per_bgc": {"BGC01": {"needs_maturation": True}}},
        "cctt": {"counts": {"T43-NUC_nucleoside": 4, "T43-HAL_halogenase": 0},
                 "bgc_coupling": {"BGC01": ["T43-NUC_nucleoside"]}},
        "chitinase": {"counts": {"GH18": 2, "AA10_LPMO": 1}},
        "resistance_tiers": {"tier_counts": {"T3_TRANSPORTER_ONLY_ROUTING": 4}},
        "blda_tta": {"per_bgc": {
            "BGC01": {"bldA_tier": "T1", "tta_codons": 0},
            "BGC02": {"bldA_tier": "T4", "tta_codons": 9}}},
    },
}


def test_renders_all_eight_sections():
    md = _m.render(_MANIFEST)
    for n, name in [(1, "KCB Sweep"), (2, "Hallucination-Trap"), (3, "FLBR"), (4, "UMED"),
                    (5, "CCTT"), (6, "CGAD"), (7, "Resistance"), (8, "bldA")]:
        assert f"### {n} ·" in md, f"missing section {n}"
        assert name in md, f"missing section name {name}"


def test_kcb_inflation_flagged_for_low_protein_anchor():
    md = _m.render(_MANIFEST)
    # BGC02: 33000 on 2 proteins -> INFLATED; BGC01: 20000 on 25 -> not
    kcb = md.split("### 2")[0]
    assert "BGC02" in kcb and "INFLATED" in kcb
    bgc01_line = [ln for ln in kcb.splitlines() if "BGC01" in ln][0]
    assert "INFLATED" not in bgc01_line


def test_blda_tier_distribution_and_flag():
    md = _m.render(_MANIFEST)
    assert "T1=1" in md and "T4=1" in md           # tier distribution
    assert "BGC02" in md.split("### 8")[1] and "T4" in md.split("### 8")[1]


def test_claim_ceilings_present():
    md = _m.render(_MANIFEST)
    assert "similarity, not identity" in md          # KCB
    assert "HMMER" in md                              # CGAD
    assert "bitscore floor" in md.lower()             # CCTT
    assert "Tier-3" in md or "HGT guard" in md        # resistance


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
