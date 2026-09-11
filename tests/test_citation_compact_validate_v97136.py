from __future__ import annotations

import csv
import json
from pathlib import Path

from mamey.validate import validate_citation_compact_outputs, validate_package


REQUIRED_SUFFIXES = [
    "manifest.json",
    "checksums_sha256.txt",
    "1_intake.json",
    "2_inventory.csv",
    "3_scan_states.json",
    "4A_RGGMCI_full.json",
    "4A_RGGMCI_ranked_pairs.csv",
    "4A_RGGMCI_evidence.csv",
    "4_triage_board.csv",
    "5_workbook.xlsx",
    "commit_receipt.json",
    "issue_log.md",
    "Project_Memory_Snapshot.json",
    "7_cell_provenance.csv",
]


def _write_minimal_package(tmp_path: Path, *, missing_workorder: bool = False) -> Path:
    pkg = tmp_path / "package"
    pkg.mkdir()
    for suffix in REQUIRED_SUFFIXES:
        p = pkg / f"AS_TEST_{suffix}" if suffix[0].isdigit() else pkg / suffix
        if suffix.endswith(".json"):
            p.write_text("{}", encoding="utf-8")
        elif suffix.endswith(".csv"):
            p.write_text("BGC_ID\nBGC001\n", encoding="utf-8")
        elif suffix.endswith(".xlsx"):
            p.write_bytes(b"placeholder workbook")
        else:
            p.write_text("placeholder\n", encoding="utf-8")

    # Overwrite core files needing valid structured content.
    (pkg / "manifest.json").write_text(json.dumps({
        "mode": "smoke",
        "bgcs": [{"bgc_id": "BGC001"}],
        "files": [],
    }, indent=2), encoding="utf-8")
    (pkg / "AS_TEST_4A_RGGMCI_full.json").write_text(json.dumps({
        "status": "NULL_NO_RGGMCI_PAIRS",
        "pairs_total": 0,
        "reference_record_count": 0,
    }), encoding="utf-8")

    cc = pkg / "citation_compact"
    cc.mkdir()
    compact_files = {
        "Citation_Ledger.csv": "citation_id,scope,source_status,citation_label\nCIT-BGC001-NEEDED,compound_family,citation_needed,primary citation needed\n",
        "Citation_Ledger.json": json.dumps({
            "schema_version": "citation_ledger_v1",
            "records": [{
                "citation_id": "CIT-BGC001-NEEDED",
                "scope": "compound_family",
                "source_status": "citation_needed",
                "citation_label": "primary citation needed",
            }]
        }),
        "citation_compact/Literature_Search_WorkOrder.md": "# Literature Search Work Order\n\ncitation_needed\n",
        "citation_compact/Literature_Search_WorkOrder.json": json.dumps({
            "schema_version": "literature_search_workorder_v1",
            "tasks": [{
                "task_id": "LIT-BGC001-001",
                "strain_id": "AS_TEST",
                "bgc_id": "BGC001",
                "stable_locus": "NODE_1",
                "candidate_class": "NRPS",
                "evidence_basis": ["Products: NRPS"],
                "citation_need": "primary citation needed",
                "search_instruction": "Find DOI/PMID. Do not infer activity.",
                "must_find": ["DOI", "PMID"],
                "do_not_infer": "Do not infer activity.",
                "output_format": "citation_id | citation_label | DOI | PMID | source_status | one-sentence relevance",
                "source_status": "citation_needed",
            }]
        }),
        "citation_compact/AS_TEST_technical_report_citation_compact.md": "GLOBAL\n",
        "citation_compact/CITATION_COMPACT_QA.json": json.dumps({
            "status": "PASS_STRUCTURE",
            "outputs": [
                "Citation_Ledger.csv",
                "Citation_Ledger.json",
                "citation_compact/Literature_Search_WorkOrder.md",
                "citation_compact/Literature_Search_WorkOrder.json",
                "citation_compact/AS_TEST_technical_report_citation_compact.md",
            ],
        }),
    }
    if missing_workorder:
        compact_files.pop("citation_compact/Literature_Search_WorkOrder.json")

    for rel, content in compact_files.items():
        p = pkg / rel
        p.parent.mkdir(exist_ok=True)
        p.write_text(content, encoding="utf-8")

    # Track compact outputs in manifest/checksums like a sealed package.
    tracked = sorted(compact_files)
    import hashlib as _hashlib

    def _sha256(p: Path) -> str:
        return _hashlib.sha256(p.read_bytes()).hexdigest()

    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"] = [
        {"path": rel, "sha256": _sha256(pkg / rel), "bytes": (pkg / rel).stat().st_size}
        for rel in tracked
    ]
    (pkg / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (pkg / "checksums_sha256.txt").write_text(
        "\n".join(f"{_sha256(pkg / rel)}  {rel}" for rel in tracked) + "\n",
        encoding="utf-8",
    )
    return pkg


def test_citation_compact_validator_not_requested_for_normal_package(tmp_path: Path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    result = validate_citation_compact_outputs(pkg)
    assert result["status"] == "NOT_REQUESTED"


def test_citation_compact_validator_passes_complete_outputs(tmp_path: Path):
    pkg = _write_minimal_package(tmp_path)
    result = validate_citation_compact_outputs(pkg)
    assert result["status"] == "PASS_STRUCTURE"
    assert result["citation_count"] == 1
    assert result["literature_task_count"] == 1


def test_citation_compact_validator_fails_missing_workorder_json(tmp_path: Path):
    pkg = _write_minimal_package(tmp_path, missing_workorder=True)
    result = validate_citation_compact_outputs(pkg)
    assert result["status"] == "FAIL"
    assert "citation_compact/Literature_Search_WorkOrder.json" in result["missing"]


def test_validate_package_blocks_broken_compact_outputs(tmp_path: Path):
    pkg = _write_minimal_package(tmp_path, missing_workorder=True)
    result = validate_package(pkg)
    assert result["citation_compact_gate"] == "FAIL"
    assert result["status"] == "FAIL"
