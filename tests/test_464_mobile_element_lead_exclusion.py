"""A mobile-element exclusion keeps a BGC out of every top-lead surface, like the other two.

scoring.is_lead_excluded covers standing rule, primary metabolism and mobile element. Several
surfaces filtered on the first two only, so a region withheld for mobile-element machinery
reached list-bgcs, manifest_short top 3, Mode B, lead figures and gene tables.
"""
import re
from pathlib import Path

from mamey.package_inspector import _select_bgc_rows
from mamey.report_mode import _flags

ROOT = Path(__file__).resolve().parents[1]


def _row(bgc, ab, mobile=""):
    return {"BGC_ID": bgc, "AB_auto": str(ab), "AF_auto": "0", "Standing_rule": "",
            "Primary_metab_flag": "", "Mobile_element_flag": mobile}


def test_list_bgcs_drops_a_mobile_element_only_row():
    rows = [_row("BGC001", 90, mobile="IS_TRANSPOSASE_DOMINANT"), _row("BGC002", 50)]
    assert [r["BGC_ID"] for r in _select_bgc_rows(rows, axis="ab")] == ["BGC002"]
    assert len(_select_bgc_rows(rows, axis="ab", include_dropped=True)) == 2


def test_terse_board_names_the_mobile_element_flag():
    assert "MOBILE-ELEMENT:IS_TRANSPOSASE_DOMINANT" in _flags({"mobile_element_flag": "IS_TRANSPOSASE_DOMINANT"})


def test_no_two_flag_lead_filter_is_left_in_the_engine():
    # The old filter tested Standing_rule and Primary_metab_flag and nothing else.
    two_flag = re.compile(
        r"if not r\.get\(\"(Standing_rule|Primary_metab_flag)\"\)\s*\n?\s*"
        r"and (not )?r\.get\(\"(Standing_rule|Primary_metab_flag)\"\)")
    hits = [str(p.relative_to(ROOT)) for p in (ROOT / "mamey").rglob("*.py")
            if two_flag.search(p.read_text(encoding="utf-8"))]
    assert hits == []


def test_no_means_not_flagged():
    from mamey.scoring import is_lead_excluded
    assert not is_lead_excluded({"Standing_rule": "", "Primary_metab_flag": "NO", "Mobile_element_flag": ""})
    assert is_lead_excluded({"Primary_metab_flag": "YES"})


def test_domain_level_fails_closed_when_board_and_manifest_disagree(tmp_path):
    import csv, json
    from mamey.domain_level import _top_bgcs_from_package
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "STRAINX", "bgcs": [
        {"bgc_id": "BGC001", "mobile_element_flag": ""},
        {"bgc_id": "BGC002", "mobile_element_flag": "IS_TRANSPOSASE_DOMINANT"},
        {"bgc_id": "BGC003", "mobile_element_flag": ""}]}))
    with open(tmp_path / "STRAINX_4_triage_board.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["BGC_ID", "AB_auto", "AF_auto", "Standing_rule",
                                           "Primary_metab_flag", "Mobile_element_flag"])
        w.writeheader()
        w.writerow({"BGC_ID": "BGC001", "AB_auto": "90", "AF_auto": "0", "Mobile_element_flag": "IS_TRANSPOSASE_DOMINANT"})
        w.writerow({"BGC_ID": "BGC002", "AB_auto": "80", "AF_auto": "0", "Mobile_element_flag": ""})
        w.writerow({"BGC_ID": "BGC003", "AB_auto": "50", "AF_auto": "0", "Primary_metab_flag": "NO"})
    _, top = _top_bgcs_from_package(tmp_path, 3)
    assert [b["bgc_id"] for b in top] == ["BGC003"]


def test_terse_board_and_s6_read_no_as_unflagged():
    import pandas as pd
    from mamey.scoring import _lx_truthy
    cells = pd.Series(["NO", "", None, "YES", "IS_TRANSPOSASE_DOMINANT"])
    assert list(cells.fillna("").map(_lx_truthy)) == [False, False, False, True, True]
