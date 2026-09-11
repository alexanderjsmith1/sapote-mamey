"""v9.7.345 next-cut candidate: governed 200-set Codex figure registry."""

from __future__ import annotations

import csv
import json

from mamey.interactive_figures.figure_set_registry import (
    FAMILIES,
    GLOBAL_CLAIM_CEILING,
    LENSES,
    build_registry,
    emit_registry,
    validate_registry,
)


def test_registry_is_exactly_25_families_by_8_lenses():
    records = build_registry()
    assert len(FAMILIES) == 25
    assert len(LENSES) == 8
    assert len(records) == 200
    assert validate_registry(records) == []
    assert len({record["figure_set_id"] for record in records}) == 200
    assert len({record["title"] for record in records}) == 200


def test_registry_explicitly_includes_strain_and_cohort_sets():
    records = build_registry()
    strain = [record for record in records if record["lens_id"] == "STR"]
    cohort = [record for record in records if record["lens_id"] == "OVR"]
    assert len(strain) == len(cohort) == 25
    assert all("every included strain" in record["label_policy"] for record in strain)
    assert all("governed cohort" in record["scientific_question"] for record in cohort)


def test_every_set_has_provenance_gate_missing_policy_and_claim_ceiling():
    for record in build_registry():
        assert record["source_artifacts"]
        assert record["required_gates"]
        assert "missing" in record["missing_policy"]
        assert "not identity" in record["claim_ceiling"].lower()
        assert GLOBAL_CLAIM_CEILING in record["caption_template"]
        assert "Source artifacts:" in record["methods_template"]


def test_gated_families_do_not_claim_implementation():
    records = build_registry()
    mpg = [record for record in records if record["family_id"] == "MPG"]
    assert len(mpg) == 8
    assert all(record["status"] == "REQUIRES_CURATED_INGRESS" for record in mpg)
    lead = [record for record in records if record["lens_id"] == "LED"]
    assert all("LEAD_LEDGER" in record["status"] or record["status"].startswith("REQUIRES_") for record in lead)


def test_emit_registry_outputs_all_contracts(tmp_path):
    result = emit_registry(tmp_path)
    assert result["status"] == "PASS"
    assert result["registry_count"] == 200
    assert result["family_count"] == 25
    assert result["lens_count"] == 8
    expected = {
        "FIGURE_SET_REGISTRY_200.json", "FIGURE_SET_REGISTRY_200.csv",
        "CAPTIONS_METHODS_200.md", "OPEN_200_FIGURE_SET_REGISTRY.html",
        "REGISTRY_QA_RECEIPT.json",
    }
    assert expected <= {path.name for path in tmp_path.iterdir()}
    data = json.loads((tmp_path / "FIGURE_SET_REGISTRY_200.json").read_text())
    assert len(data) == 200
    with (tmp_path / "FIGURE_SET_REGISTRY_200.csv").open(newline="") as stream:
        assert len(list(csv.DictReader(stream))) == 200
    html = (tmp_path / "OPEN_200_FIGURE_SET_REGISTRY.html").read_text()
    assert "25 scientific families × 8 analytical lenses" in html
    assert "Per-strain labelled landscape" in html


def test_cli_parser_registers_catalog_command():
    from mamey.cli import build_parser

    args = build_parser().parse_args([
        "codex-figure-catalog", "--outdir", "catalog", "--family", "MPG"
    ])
    assert args.command == "codex-figure-catalog"
    assert args.family == "MPG"
