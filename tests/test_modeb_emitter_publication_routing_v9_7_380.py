from __future__ import annotations

import json
from pathlib import Path

from mamey.modeb_publication_gate import publication_quality_findings
from mamey.modeb_structure_gate import lint_card
from mamey.modeb_template_emitter import emit_card_template


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "TEST-001" / "package"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps({
        "strain_id": "TEST-001", "taxonomy": "Streptomyces testii", "source": "public fixture",
    }))
    (package / "manifest_short.json").write_text(json.dumps({
        "strain_id": "TEST-001", "assembly_tier": "GOOD", "interior_pct": 90.0,
    }))
    (package / "TEST-001_4_triage_board.csv").write_text(
        "BGC_ID,Node_ID,Contig,antiSMASH_Region,Products,Boundary,Assembly_Locator,"
        "Length_kb,AB_auto,AF_auto,Novelty_auto,Lead_tier_auto,Corrected_rank,KCB_top,"
        "KCB_score,CCTT_triggers,Standing_rule,UMED_gap\n"
        "BGC001,NODE_1_length_10000_cov_20.000000,NODE_1_length_10000_cov_20.000000,"
        "region001,NRPS,Interior,Interior,10.0,40,20,MED,HIGH,1,,,T43-IDC,,\n"
    )
    rows = {
        "bgc_id": "BGC001",
        "cds": [
            {"locus_tag": "ctg1_1", "contig": "NODE_1_length_10000_cov_20.000000",
             "start": 100, "end": 900, "strand": 1, "aa_length": 266,
             "sec_met_domains": ["AMP-binding"], "gene_kind": "biosynthetic",
             "tta_codons": 0, "product": "adenylation-domain protein"},
            {"locus_tag": "ctg1_2", "contig": "NODE_1_length_10000_cov_20.000000",
             "start": 1000, "end": 1800, "strand": -1, "aa_length": 266,
             "sec_met_domains": [], "gene_kind": "other", "tta_codons": 0,
             "product": "hypothetical protein"},
        ],
    }
    (package / "TEST-001_gene_context.jsonl").write_text(json.dumps(rows) + "\n")
    return package


def test_fresh_template_is_structure_scaffold_not_publication_candidate(tmp_path: Path) -> None:
    card = emit_card_template(_package(tmp_path), "BGC001")
    assert [f for f in lint_card(card) if f["severity"] == "ERROR"] == []
    codes = {f["code"] for f in publication_quality_findings(
        card, canonical_loci=["ctg1_1", "ctg1_2"]
    )}
    assert "PUBLICATION_GENE_TABLE_MISSING" not in codes
    assert "EVIDENCE_STREAM_DISPOSITION" in codes
    assert "SECTION_RECONCILIATION_STATE" in codes
    assert "authoring scaffold, not a publication candidate" in card


def test_emitter_supplies_canonical_channel_matrix_scaffold(tmp_path: Path) -> None:
    card = emit_card_template(_package(tmp_path), "BGC001")
    assert card.count("#### Complete named-match, channel-separated table") == 1
    assert "| Gene | NCBI nr top hit | NCBI nr identity |" in card
    assert card.count("| `ctg1_1` | <accession · matched protein · organism · state>") == 1
    assert card.count("| `ctg1_2` | <accession · matched protein · organism · state>") == 1


def test_route_document_says_gate_saved_authored_bytes() -> None:
    docs = Path(__file__).resolve().parents[1] / "docs"
    route = (docs / "MODEB_GATE_CLEAN_AUTHORING.md").read_text(encoding="utf-8")
    contract = (docs / "MODEB_PUBLICATION_SECTION_REQUIREMENTS_v9_7_372.md").read_text(encoding="utf-8")
    assert "`emit-modeb-template` result is an **unfilled authoring scaffold**" in contract
    assert "Gate the actual saved candidate" in route
    assert "without surrounding backticks" in route
