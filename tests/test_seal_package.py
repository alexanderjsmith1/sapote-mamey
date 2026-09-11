"""test_seal_package.py — the one final sealing layer (v9.7.125, audit P0).

seal_package() composes every QC gate (package validate, workbook content, Mode B quality,
locator reconciliation, claim safety) into one pass and emits DEBUG_RECEIPT.md / seal_status.json
/ seal_findings.csv. Strict mode makes blocking-gate failures exit 1.
"""
import csv
import json
from pathlib import Path

import openpyxl
import pytest

from mamey.seal_package import seal_package, write_receipts
from mamey.judgment_store import init_register, record_mode_b


@pytest.fixture
def pkg(tmp_path):
    (tmp_path / "manifest.json").write_text(
        json.dumps({"strain_id": "AS-TEST", "mode": "gold", "bgcs": []})
    )
    return tmp_path


def _seed_triage(pkg, rows):
    with open(pkg / "AS-TEST_4_triage_board.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Rank", "BGC_ID", "Node_ID", "Contig", "antiSMASH_Region", "Products", "Misanchor_Flag"])
        for r in rows:
            w.writerow(r)


def _good_workbook(pkg):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name in ("BGC_Inventory", "Triage_Board", "WetLab_Decision_Matrix", "Mode_B_Summary"):
        ws = wb.create_sheet(name)
        ws.append(["BGC_ID", "Col"])
        ws.append(["BGC001", "value"])
    wb.save(str(pkg / "AS-TEST_5_workbook.xlsx"))


def test_seal_runs_all_gates_and_writes_receipts(pkg):
    result = seal_package(pkg)
    gate_names = {g["name"] for g in result["gates"]}
    assert gate_names == {
        "package_validate", "workbook_content", "mode_b_quality",
        "locator_reconciliation", "claim_safety",
        "figure_references", "deliverable_status",
    }
    paths = write_receipts(result, pkg)
    assert paths["receipt"].exists()
    assert paths["status"].exists()
    assert paths["findings"].exists()


def test_seal_status_json_is_valid(pkg):
    result = seal_package(pkg)
    paths = write_receipts(result, pkg)
    loaded = json.loads(paths["status"].read_text())
    assert loaded["overall"] in ("PASS", "WARN", "FAIL")
    assert "gates" in loaded


def test_strict_mode_blocks_on_workbook_fail(pkg):
    """A workbook with missing sheets is a blocking FAIL; strict exit_code = 1."""
    # no workbook present at all -> workbook gate SKIPs, but make a bad one to force FAIL
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("BGC_Inventory")
    ws.append(["BGC_ID", "Col"])  # header only, no data -> FAIL_empty
    for name in ("Triage_Board", "WetLab_Decision_Matrix", "Mode_B_Summary"):
        s = wb.create_sheet(name)
        s.append(["BGC_ID", "Col"])
        s.append(["BGC001", "v"])
    wb.save(str(pkg / "AS-TEST_5_workbook.xlsx"))

    strict = seal_package(pkg, strict=True)
    assert strict["gates"][1]["name"] == "workbook_content"
    assert strict["overall"] == "FAIL"
    assert strict["exit_code"] == 1
    # F05 (v9.7.354): the DEFAULT now enforces — a blocking FAIL exits non-zero.
    default = seal_package(pkg)
    assert default["overall"] == "FAIL"
    assert default["exit_code"] == 1
    # advisory (report-only) opt-in reports the same overall but does not block
    advisory = seal_package(pkg, advisory=True)
    assert advisory["overall"] == "FAIL"
    assert advisory["exit_code"] == 0


def test_seal_locator_mismatch_is_blocking(pkg):
    """A filed card with a drifted node is a blocking locator FAIL in strict mode."""
    _good_workbook(pkg)
    _seed_triage(pkg, [["1", "BGC001", "NODE_10", "NODE_10", "region001", "RiPP", ""]])
    init_register(pkg, "AS-TEST", ["BGC001"])
    # file a card whose heading node drifts from the triage row
    record_mode_b(
        pkg, "BGC001",
        "# Mode B — AS-TEST / NODE_99 / region001 / BGC001\n§1 content.",
    )
    result = seal_package(pkg, strict=True)
    loc = next(g for g in result["gates"] if g["name"] == "locator_reconciliation")
    assert loc["status"] == "FAIL"
    assert result["exit_code"] == 1


def test_seal_clean_package_passes(pkg):
    """A package with good workbook, matching card, and clean prose seals PASS."""
    _good_workbook(pkg)
    _seed_triage(pkg, [["1", "BGC001", "NODE_10", "NODE_10", "region001", "RiPP", ""]])
    init_register(pkg, "AS-TEST", ["BGC001"])
    card = ("# Mode B — AS-TEST / NODE_10 / region001 / BGC001\n"
            "§1 §2 §3 §4 §5 §6 §7 §8 Biosynthetic capacity consistent with a RiPP-like compound.")
    record_mode_b(pkg, "BGC001", card)
    result = seal_package(pkg, strict=True)
    loc = next(g for g in result["gates"] if g["name"] == "locator_reconciliation")
    cs = next(g for g in result["gates"] if g["name"] == "claim_safety")
    assert loc["status"] == "PASS"
    assert cs["status"] == "PASS"
    # workbook + package validate may still warn, but locator & claim-safety are clean


# ── v9.7.125b: claim-safety identity rule promoted to FAIL-blocking (post-AS-901) ──
def _kcb_workbook_and_triage(pkg, kcb_top="BGC0001.1 | colibrimycin | kcb"):
    _good_workbook(pkg)
    _seed_triage(pkg, [["1", "BGC001", "NODE_1", "NODE_1", "region001", "RiPP", ""]])
    # add KCB_top so the compound-set robust path is active
    import csv as _csv
    rows = list(_csv.reader(open(pkg / "AS-TEST_4_triage_board.csv")))
    rows[0] += ["KCB_top"]
    rows[1] += [kcb_top]
    with open(pkg / "AS-TEST_4_triage_board.csv", "w", newline="") as f:
        _csv.writer(f).writerows(rows)


def test_seal_blocks_on_real_identity_overclaim(pkg):
    """A card asserting 'produces <compound>' makes the claim-safety gate FAIL and blocks strict seal."""
    _kcb_workbook_and_triage(pkg)
    init_register(pkg, "AS-TEST", ["BGC001"])
    record_mode_b(pkg, "BGC001", "## BGC001 (NODE_1 · region001)\n§1 This cluster produces colibrimycin.")
    result = seal_package(pkg, strict=True)
    cs = next(g for g in result["gates"] if g["name"] == "claim_safety")
    assert cs["status"] == "FAIL"
    assert result["exit_code"] == 1


def test_seal_does_not_block_on_descriptive_prose(pkg):
    """AS-901 regression: a card full of descriptive 'is X' predicates must NOT block the seal."""
    _kcb_workbook_and_triage(pkg)
    init_register(pkg, "AS-TEST", ["BGC001"])
    card = ("## BGC001 (NODE_1 · region001)\n"
            "§1 §2 §3 §4 §5 §6 §7 §8 This BGC is Edge-status. No activity is assumed at the "
            "extract level. The boundary is interior. These are routing priors. "
            "KCB anchor: colibrimycin — similarity anchor, not a product identity.")
    record_mode_b(pkg, "BGC001", card)
    result = seal_package(pkg, strict=True)
    cs = next(g for g in result["gates"] if g["name"] == "claim_safety")
    assert cs["status"] == "PASS", cs["findings"]


# ── v9.7.126: figure-reference validation + deliverable-status table (audit P1) ──
def _make_png(path, valid=True):
    """Write a minimal file with (or without) PNG magic bytes."""
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" if valid else b"NOTPNG__")
        f.write(b"\x00" * 32)


def test_figure_gate_passes_with_companion_csvs(pkg):
    """Every figure PNG with a companion _data.csv and valid magic bytes → figure gate PASS."""
    _make_png(pkg / "AS-TEST_8a_fig_landscape.png")
    (pkg / "AS-TEST_8a_fig_landscape_data.csv").write_text("x,y\n1,2\n")
    result = seal_package(pkg)
    fig = next(g for g in result["gates"] if g["name"] == "figure_references")
    assert fig["status"] == "PASS"


def test_figure_gate_warns_on_missing_companion_csv(pkg):
    """A figure PNG without its companion _data.csv → WARN (non-blocking)."""
    _make_png(pkg / "AS-TEST_8b_fig_composition.png")
    # no companion csv
    result = seal_package(pkg)
    fig = next(g for g in result["gates"] if g["name"] == "figure_references")
    assert fig["status"] == "WARN"
    assert any("missing companion" in f["detail"] for f in fig["findings"])
    # figures are supplementary → must NOT make the seal FAIL on their own
    assert fig["blocking"] is False


def test_figure_gate_warns_on_invalid_png(pkg):
    """A file named *fig*.png that lacks PNG magic bytes → WARN."""
    _make_png(pkg / "AS-TEST_8c_fig_bad.png", valid=False)
    (pkg / "AS-TEST_8c_fig_bad_data.csv").write_text("x\n1\n")
    result = seal_package(pkg)
    fig = next(g for g in result["gates"] if g["name"] == "figure_references")
    assert fig["status"] == "WARN"
    assert any("not a valid PNG" in f["detail"] for f in fig["findings"])


def test_figure_gate_warns_on_missing_referenced_figure(pkg):
    """A markdown report referencing a figure that doesn't exist → WARN."""
    (pkg / "REPORT.md").write_text("See ![landscape](AS-TEST_nonexistent_fig.png) for detail.")
    result = seal_package(pkg)
    fig = next(g for g in result["gates"] if g["name"] == "figure_references")
    assert fig["status"] == "WARN"
    assert any("references missing figure" in f["detail"] for f in fig["findings"])


def test_deliverable_status_gate_reports_presence(pkg):
    """The deliverable-status gate reports PASS/PARTIAL per artifact and folds in gate statuses."""
    result = seal_package(pkg)
    deliv = next(g for g in result["gates"] if g["name"] == "deliverable_status")
    details = [f["detail"] for f in deliv["findings"]]
    assert any("manifest.json: present" in d for d in details)
    assert any(d.startswith("gate:") for d in details)  # folds in live gate statuses


def test_named_csvs_written(pkg):
    """write_receipts emits the two audit-named CSVs."""
    _make_png(pkg / "AS-TEST_8a_fig.png")
    (pkg / "AS-TEST_8a_fig_data.csv").write_text("x\n1\n")
    result = seal_package(pkg)
    paths = write_receipts(result, pkg)
    assert paths["figure_csv"].name == "figure_reference_validation.csv"
    assert paths["deliverable_csv"].name == "deliverable_status_table.csv"
    assert paths["figure_csv"].exists() and paths["deliverable_csv"].exists()


def test_figure_gate_skips_cleanly_with_no_figures(pkg):
    """A package with no figures → figure gate PASS (nothing to validate), no error."""
    result = seal_package(pkg)
    fig = next(g for g in result["gates"] if g["name"] == "figure_references")
    assert fig["status"] == "PASS"
