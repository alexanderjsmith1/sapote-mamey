from __future__ import annotations

import csv
import json
from pathlib import Path

from mamey.citation_compact import (
    CitationRecord,
    GLOBAL_BGC_CAVEAT,
    caveat_count,
    validate_global_caveat_count,
    validate_priority_citation_coverage,
    write_citation_ledger_csv,
    write_citation_ledger_json,
)


def test_priority_lead_requires_citation_basis():
    leads = [
        {
            "lead_id": "AF-01",
            "lead_priority": "HIGH",
            "citation_basis": [],
        }
    ]
    errors = validate_priority_citation_coverage(leads)
    assert errors
    assert errors[0]["error"] == "priority lead missing citation_basis"


def test_priority_lead_allows_explicit_citation_needed():
    leads = [
        {
            "lead_id": "AF-01",
            "lead_priority": "HIGH",
            "citation_basis": [
                {
                    "citation_id": "CIT-001",
                    "source_status": "citation_needed",
                    "citation_label": "primary family reference needed",
                }
            ],
        }
    ]
    assert validate_priority_citation_coverage(leads) == []


def test_global_caveat_can_appear_once_but_not_repeated():
    once = GLOBAL_BGC_CAVEAT + "\n\nLead table here."
    twice = GLOBAL_BGC_CAVEAT + "\n\nLead table here.\n\n" + GLOBAL_BGC_CAVEAT
    assert caveat_count(once) == 1
    assert validate_global_caveat_count(once) == []
    errors = validate_global_caveat_count(twice)
    assert errors
    assert errors[0]["error"] == "global BGC caveat repeated"


def test_citation_ledger_csv_and_json_roundtrip(tmp_path: Path):
    records = [
        CitationRecord(
            citation_id="CIT-001",
            scope="method",
            source_status="verified",
            citation_label="antiSMASH method",
            doi="10.1093/nar/gkaf334",
            supports=["BGC class extraction", "KCB interpretation"],
        )
    ]
    csv_path = write_citation_ledger_csv(records, tmp_path / "Citation_Ledger.csv")
    json_path = write_citation_ledger_json(
        records,
        tmp_path / "Citation_Ledger.json",
        bundle_version="9.7.136",
        strain_id="AS-TEST",
    )

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["citation_id"] == "CIT-001"
    assert "BGC class extraction" in rows[0]["supports"]

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "citation_ledger_v1"
    assert payload["bundle_version"] == "9.7.136"
    assert payload["records"][0]["citation_id"] == "CIT-001"


def test_citation_compact_templates_do_not_repeat_claim_ceiling():
    root = Path(__file__).resolve().parents[1]
    template_dir = root / "templates" / "citation_compact"
    assert template_dir.exists()
    for path in template_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert text.count("{{GLOBAL_BGC_CAVEAT}}") <= 1
        assert "claim ceiling" not in text.lower()
        assert "claim_ceiling" not in text.lower()
    assert "Citation_Ledger" in (template_dir / "technical_report.md").read_text(encoding="utf-8")
