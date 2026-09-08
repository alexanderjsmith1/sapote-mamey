"""v9.7.379 (BLACK_CHERRY_379) — regression: _top_bgcs_from_package must exclude a BGC the engine
demoted purely for mobile/IS-element dominance, mirroring scoring.is_lead_excluded()'s 3-flag gate.

The triage CSV has no Mobile_element_flag column (cli.py triage_headers), so the check must read
mobile_element_flag from the manifest bgcs (bgcs_by_id), which carry it since v9.7.374 (models.py:369).
Before the fix, such a BGC (no standing_rule, no primary_metab) still entered the domain-level top-N.
"""
from __future__ import annotations
import csv as _csv
import json

from mamey.domain_level import _top_bgcs_from_package


def _build_pkg(tmp_path):
    pkg = tmp_path / "STRAINM" / "package"
    pkg.mkdir(parents=True)
    strain = "STRAINM"
    # manifest bgcs carry mobile_element_flag (models.py:369, v9.7.374). BGC002 is mobile-element-
    # demoted; BGC001 is a clean lead. Both have high AB+AF so BGC002 would out-rank BGC001 if the
    # exclusion were skipped.
    (pkg / "manifest.json").write_text(json.dumps({
        "strain_id": strain,
        "bgcs": [
            {"bgc_id": "BGC001", "contig": "NODE_1", "start": 0, "end": 12000,
             "region_number": 1, "products": ["NRPS"], "mobile_element_flag": ""},
            {"bgc_id": "BGC002", "contig": "NODE_2", "start": 0, "end": 12000,
             "region_number": 1, "products": ["T1PKS"], "mobile_element_flag": "IS3,Tn3-family"},
        ],
    }), encoding="utf-8")
    with open(pkg / f"{strain}_4_triage_board.csv", "w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=["BGC_ID", "Contig", "AB_auto", "AF_auto",
                                            "Novelty_auto", "Standing_rule", "Primary_metab_flag"])
        w.writeheader()
        # BGC002 ranks higher by AB+AF, but is mobile-element-demoted (no standing_rule/primary_metab).
        w.writerow({"BGC_ID": "BGC001", "Contig": "NODE_1", "AB_auto": "40", "AF_auto": "30",
                    "Novelty_auto": "10", "Standing_rule": "", "Primary_metab_flag": "NO"})
        w.writerow({"BGC_ID": "BGC002", "Contig": "NODE_2", "AB_auto": "90", "AF_auto": "80",
                    "Novelty_auto": "10", "Standing_rule": "", "Primary_metab_flag": "NO"})
    return pkg


def test_mobile_element_bgc_excluded_from_domain_level_topn(tmp_path):
    pkg = _build_pkg(tmp_path)
    strain_id, rows = _top_bgcs_from_package(pkg, top_n=5)
    ids = [r["bgc_id"] for r in rows]
    assert "BGC002" not in ids, (
        "mobile-element-demoted BGC002 leaked into the domain-level top-N "
        f"(3-flag gate not applied): {ids}")
    assert "BGC001" in ids, f"clean lead BGC001 should be present: {ids}"


def test_clean_lead_still_included_when_no_mobile_flag(tmp_path):
    # control: a BGC with an EMPTY mobile_element_flag is not excluded.
    pkg = _build_pkg(tmp_path)
    _sid, rows = _top_bgcs_from_package(pkg, top_n=5)
    assert any(r["bgc_id"] == "BGC001" for r in rows)
