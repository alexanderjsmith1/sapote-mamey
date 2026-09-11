"""test_seal_strict_exit.py — H3 regression (v9.7.352).

seal_package() hardening:
  (a) strict=True + a blocking-gate FAIL exits 1; the non-strict path still exits 0 but now
      carries a loud `non_strict_warning` so a blocking FAIL can't hide behind exit 0.
  (b) a card-less package must NOT reach overall PASS — the claim-safety invariant is never
      exercised with zero cards, so that gate is WARN (not a silent SKIP).
  (c) one malformed card yields a FAIL row for that card and the seal still completes
      (per-card try/except) — the other cards keep evaluating.
"""
import csv
import json
import sys
from pathlib import Path

import openpyxl
import pytest

# claim_safety_linter lives in tools/ (imported lazily by the seal gate); tests add it to path.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "tools"))
import claim_safety_linter
from mamey.seal_package import seal_package
from mamey.judgment_store import init_register, record_mode_b


@pytest.fixture
def pkg(tmp_path):
    (tmp_path / "manifest.json").write_text(
        json.dumps({"strain_id": "AS-TEST", "mode": "gold", "bgcs": []})
    )
    return tmp_path


def _good_workbook(pkg):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name in ("BGC_Inventory", "Triage_Board", "WetLab_Decision_Matrix", "Mode_B_Summary"):
        ws = wb.create_sheet(name)
        ws.append(["BGC_ID", "Col"])
        ws.append(["BGC001", "value"])
    wb.save(str(pkg / "AS-TEST_5_workbook.xlsx"))


def _seed_triage(pkg, rows):
    with open(pkg / "AS-TEST_4_triage_board.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Rank", "BGC_ID", "Node_ID", "Contig", "antiSMASH_Region", "Products", "Misanchor_Flag"])
        for r in rows:
            w.writerow(r)


# ── (a) strict blocks; non-strict surfaces the banner ────────────────────────────────
def test_strict_exit_and_nonstrict_banner_on_blocking_fail(pkg):
    # header-only BGC_Inventory -> workbook_content blocking FAIL
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("BGC_Inventory")
    ws.append(["BGC_ID", "Col"])  # header only -> FAIL_empty
    for name in ("Triage_Board", "WetLab_Decision_Matrix", "Mode_B_Summary"):
        s = wb.create_sheet(name)
        s.append(["BGC_ID", "Col"]); s.append(["BGC001", "v"])
    wb.save(str(pkg / "AS-TEST_5_workbook.xlsx"))

    strict = seal_package(pkg, strict=True)
    assert strict["overall"] == "FAIL"
    assert strict["exit_code"] == 1
    assert strict["non_strict_warning"] is None  # strict path enforces, no banner

    # F05 (v9.7.354): the DEFAULT now enforces — a blocking FAIL exits 1 with no advisory banner.
    default = seal_package(pkg)
    assert default["overall"] == "FAIL"
    assert default["exit_code"] == 1
    assert default["non_strict_warning"] is None  # enforced by default -> no demotion banner

    # advisory (report-only) opt-in still exits 0, but never silently: it surfaces the banner.
    advisory = seal_package(pkg, advisory=True)
    assert advisory["overall"] == "FAIL"
    assert advisory["exit_code"] == 0
    assert advisory["non_strict_warning"], "advisory blocking FAIL must surface a banner"
    assert "exit forced to 0" in advisory["non_strict_warning"]


# ── (b) card-less package never reaches PASS ─────────────────────────────────────────
def test_cardless_package_is_not_pass(pkg):
    _good_workbook(pkg)
    result = seal_package(pkg, strict=False)
    cs = next(g for g in result["gates"] if g["name"] == "claim_safety")
    assert cs["status"] == "WARN", "card-less claim_safety must WARN, not silently SKIP to PASS"
    assert "no filed cards" in cs["detail"]
    assert result["overall"] != "PASS", "a card-less package must never seal PASS"


# ── (c) one malformed card fails that card only; seal still completes ─────────────────
def test_malformed_card_fails_row_not_whole_seal(pkg, monkeypatch):
    _good_workbook(pkg)
    _seed_triage(pkg, [
        ["1", "BGC001", "NODE_10", "NODE_10", "region001", "RiPP", ""],
        ["2", "BGC002", "NODE_10", "NODE_10", "region002", "RiPP", ""],
    ])
    init_register(pkg, "AS-TEST", ["BGC001", "BGC002"])
    record_mode_b(pkg, "BGC001", "## BGC001 (NODE_10 · region001)\n§1 EXPLODE content.")
    record_mode_b(pkg, "BGC002", "## BGC002 (NODE_10 · region002)\n§1 clean content.")

    real_lint = claim_safety_linter.lint_claim_safety

    def flaky_lint(card, compound_names=None):
        if "EXPLODE" in (card or ""):
            raise ValueError("synthetic malformed card")
        return real_lint(card, compound_names=compound_names)

    monkeypatch.setattr(claim_safety_linter, "lint_claim_safety", flaky_lint)

    # must not raise — the per-card guard turns the bad card into a FAIL row
    result = seal_package(pkg, strict=False)
    cs = next(g for g in result["gates"] if g["name"] == "claim_safety")
    bad = [f for f in cs["findings"] if f["bgc"] == "BGC001"]
    assert bad and bad[0]["severity"] == "FAIL"
    assert "card evaluation error" in bad[0]["detail"]
    # the clean card was still evaluated (no exception aborted the loop)
    assert cs["status"] == "FAIL"
