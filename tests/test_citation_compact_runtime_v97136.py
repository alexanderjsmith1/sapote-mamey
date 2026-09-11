from __future__ import annotations

import csv
import json
from pathlib import Path

from mamey.cli import build_parser
from mamey.citation_compact import emit_citation_compact_outputs, GLOBAL_BGC_CAVEAT


def _fake_package(tmp_path: Path) -> Path:
    pkg = tmp_path / "package"
    pkg.mkdir()
    triage = pkg / "AS_TEST_4_triage_board.csv"
    with triage.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "BGC_ID", "Contig", "Products", "Lead_tier_auto", "AB_auto", "AF_auto",
            "KCB_top", "Boundary", "Standing_rule", "Primary_metab_flag",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "BGC_ID": "BGC001",
            "Contig": "NODE_1",
            "Products": "NRPS",
            "Lead_tier_auto": "High",
            "AB_auto": "82.5",
            "AF_auto": "12.0",
            "KCB_top": "knownclusterblast comparator",
            "Boundary": "Interior",
            "Standing_rule": "",
            "Primary_metab_flag": "",
        })
    return pkg


def test_cli_accepts_token_budget_citation_compact():
    parser = build_parser()
    args = parser.parse_args([
        "run",
        "--strain", "AS_TEST",
        "--input-zip", "dummy.zip",
        "--token-budget", "citation-compact",
    ])
    assert args.token_budget == "citation-compact"


def test_emit_citation_compact_outputs_writes_ledger_and_reports(tmp_path: Path):
    pkg = _fake_package(tmp_path)
    result = emit_citation_compact_outputs(pkg, strain_id="AS_TEST", bundle_version="9.7.136")

    assert result["status"] == "PASS_STRUCTURE"
    assert (pkg / "Citation_Ledger.csv").exists()
    assert (pkg / "Citation_Ledger.json").exists()

    payload = json.loads((pkg / "Citation_Ledger.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "citation_ledger_v1"
    assert payload["bundle_version"] == "9.7.136"
    assert payload["records"]

    outdir = pkg / "citation_compact"
    expected = [
        "AS_TEST_technical_report_citation_compact.md",
        "AS_TEST_bench_guide_citation_compact.md",
        "AS_TEST_layperson_guide_citation_compact.md",
        "AS_TEST_lead_table_citation_compact.md",
        "Literature_Search_WorkOrder.md",
        "Literature_Search_WorkOrder.json",
        "CITATION_COMPACT_QA.json",
    ]
    for name in expected:
        assert (outdir / name).exists(), name

    tech = (outdir / "AS_TEST_technical_report_citation_compact.md").read_text(encoding="utf-8")
    assert GLOBAL_BGC_CAVEAT in tech
    assert "Citation_Ledger.csv" in tech
    assert "BGC001" in tech


def test_citation_compact_reports_use_one_caveat_per_package(tmp_path: Path):
    pkg = _fake_package(tmp_path)
    emit_citation_compact_outputs(pkg, strain_id="AS_TEST", bundle_version="9.7.136")

    texts = []
    for path in (pkg / "citation_compact").glob("*_citation_compact.md"):
        if path.name.endswith("lead_table_citation_compact.md"):
            continue
        texts.append(path.read_text(encoding="utf-8"))
    assert "\n\n".join(texts).count(GLOBAL_BGC_CAVEAT) == 1


def test_missing_citation_generates_literature_search_workorder(tmp_path: Path):
    pkg = _fake_package(tmp_path)
    # Remove KCB/comparator text so the compact emitter cannot even carry an
    # operator-supplied similarity anchor; it must create a citation_needed task.
    triage = pkg / "AS_TEST_4_triage_board.csv"
    rows = []
    with triage.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            row["KCB_top"] = ""
            rows.append(row)
    with triage.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    result = emit_citation_compact_outputs(pkg, strain_id="AS_TEST", bundle_version="9.7.136")
    assert result["literature_task_count"] == 1
    assert result["literature_workorder_md"] == "citation_compact/Literature_Search_WorkOrder.md"
    assert result["literature_workorder_json"] == "citation_compact/Literature_Search_WorkOrder.json"

    payload = json.loads((pkg / "citation_compact" / "Literature_Search_WorkOrder.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "literature_search_workorder_v1"
    assert payload["bundle_version"] == "9.7.136"
    task = payload["tasks"][0]
    assert task["source_status"] == "citation_needed"
    assert task["bgc_id"] == "BGC001"
    assert "Do not infer activity" in task["do_not_infer"]
    assert "Return only:" in task["search_instruction"]

    md = (pkg / "citation_compact" / "Literature_Search_WorkOrder.md").read_text(encoding="utf-8")
    assert "LIT-BGC001-001" in md
    assert "citation_needed" in md
    assert "DOI" in md and "PMID" in md


def test_templates_link_literature_workorder():
    root = Path(__file__).resolve().parents[1]
    for path in (root / "templates" / "citation_compact").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert "Literature_Search_WorkOrder" in text, path.name


def test_workorder_md_contains_real_newlines_not_escaped(tmp_path: Path):
    pkg = _fake_package(tmp_path)
    triage = pkg / "AS_TEST_4_triage_board.csv"
    rows = []
    with triage.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            row["KCB_top"] = ""
            rows.append(row)
    with triage.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    emit_citation_compact_outputs(pkg, strain_id="AS_TEST", bundle_version="9.7.136")
    md = (pkg / "citation_compact" / "Literature_Search_WorkOrder.md").read_text(encoding="utf-8")

    assert md.startswith("# Literature Search Work Order")
    assert len(md.splitlines()) >= 5
    assert "\\n" not in md


def test_workorder_md_search_instruction_is_human_readable(tmp_path: Path):
    pkg = _fake_package(tmp_path)
    triage = pkg / "AS_TEST_4_triage_board.csv"
    rows = []
    with triage.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            row["KCB_top"] = ""
            rows.append(row)
    with triage.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    emit_citation_compact_outputs(pkg, strain_id="AS_TEST", bundle_version="9.7.136")
    md = (pkg / "citation_compact" / "Literature_Search_WorkOrder.md").read_text(encoding="utf-8")
    payload = json.loads((pkg / "citation_compact" / "Literature_Search_WorkOrder.json").read_text(encoding="utf-8"))
    instruction = payload["tasks"][0]["search_instruction"]

    assert "\\n" not in instruction
    assert "Strain: AS_TEST" in instruction.splitlines()
    assert "BGC: BGC001" in instruction.splitlines()
    assert "Return only:" in instruction
    assert "Strain: AS_TEST" in md
    assert "BGC: BGC001" in md
