from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from mamey.mode_b.availability import (
    BINDING_SCORE,
    build_availability,
    discover_evidence,
    load_contract,
    load_evidence_index,
    load_inventory,
    write_outputs,
)


def _write_inventory(path: Path) -> None:
    path.write_text(
        "strain\tbgc\tfull_node\tregion\texact_locus\n"
        "REF-001\tBGC001\tNODE_7_length_50000_cov_20.5\tregion001\t"
        "REF-001|NODE_7_length_50000_cov_20.5|region001\n"
        "REF-001\tBGC002\tNODE_8_length_40000_cov_18.0\tregion001\t"
        "REF-001|NODE_8_length_40000_cov_18.0|region001\n",
        encoding="utf-8",
    )


def _fixture(tmp_path: Path):
    inventory = tmp_path / "per_bgc_index.tsv"
    _write_inventory(inventory)
    root = tmp_path / "evidence"
    bgc = root / "REF-001" / "BGC001"
    bgc.mkdir(parents=True)
    (bgc / "REF-001_BGC001_NODE_7_length_50000_cov_20.5.region001.gbk").write_text(
        "LOCUS       TEST 50000 bp\n",
        encoding="utf-8",
    )
    (bgc / "BGC001_top_hit_per_gene.csv").write_text(
        "strain,bgc_id,assembly_locator,antismash_region,locus_tag,percent_identity,query_coverage_pct\n"
        "REF-001,BGC001,NODE_7_length_50000_cov_20.5,region001,gene_1,71.2,98.0\n",
        encoding="utf-8",
    )
    (bgc / "MIBIG_per_gene.csv").write_text("strain,bgc_id,locus_tag\nREF-001,BGC001,gene_1\n", encoding="utf-8")
    (bgc / "BGC001_domain.tsv").write_text("locus_tag\tdomain\ngene_1\tPKS_KS\n", encoding="utf-8")
    (bgc / "BGC001_locus_map.png").write_bytes(b"not-a-render-test")
    (root / "REF-001" / "REF-001_thesis_context.md").write_text("cohort context only\n", encoding="utf-8")
    return inventory, root


def test_contract_is_unique_and_claim_safe():
    contract = load_contract()
    ids = [stream["id"] for stream in contract["streams"]]
    assert len(ids) == len(set(ids))
    assert "missing or unbound evidence is not biological absence" in contract["claim_ceiling"].lower()


def test_discovery_uses_header_rows_and_typed_binding(tmp_path):
    inventory, root = _fixture(tmp_path)
    loci = load_inventory(inventory)
    observations = discover_evidence(loci, load_contract(), [("fixture", root)])

    blastp = [row for row in observations if row.channel == "blastp_per_gene"]
    assert len(blastp) == 1
    assert blastp[0].binding_state == "EXACT_LOCUS"
    assert blastp[0].record_count == 1

    kcb = [row for row in observations if row.channel == "kcb_mibig"]
    assert kcb and kcb[0].binding_state == "ALIAS_BOUND"

    thesis = [row for row in observations if row.channel == "thesis_context"]
    assert thesis and thesis[0].binding_state == "STRAIN_ONLY"


def test_availability_separates_authoring_and_promotion(tmp_path):
    inventory, root = _fixture(tmp_path)
    loci = load_inventory(inventory)
    observations = discover_evidence(loci, load_contract(), [("fixture", root)])
    bgc_rows, strain_rows, section_rows = build_availability(loci, observations, load_contract())
    by_bgc = {row["bgc"]: row for row in bgc_rows}

    assert by_bgc["BGC001"]["writing_gate"] == "PASS_FOR_GAP_AWARE_AUTHORING"
    assert by_bgc["BGC001"]["promotion_gate"] == "HOLD_BLASTP_FRESHNESS_UNVERIFIED"
    assert by_bgc["BGC001"]["work_state"] == "EVIDENCE_RICH_REVIEW_CANDIDATE"
    assert by_bgc["BGC002"]["writing_gate"] == "HOLD_MISSING_GENE_LEVEL_SOURCE"
    assert len(strain_rows) == 1
    assert len(section_rows) == 60
    assert BINDING_SCORE[by_bgc["BGC001"]["thesis_context_state"]] < BINDING_SCORE["ALIAS_BOUND"]


def test_normalized_index_requires_truthful_binding_and_can_mark_current(tmp_path):
    inventory, root = _fixture(tmp_path)
    loci = load_inventory(inventory)
    artifact = root / "REF-001" / "BGC001" / "BGC001_top_hit_per_gene.csv"
    index = tmp_path / "evidence_index.tsv"
    index.write_text(
        "channel\tsource_path\tstrain\tbgc\tfull_node\tregion\tbinding_state\tfreshness_state\n"
        f"blastp_per_gene\t{artifact.relative_to(tmp_path)}\tREF-001\tBGC001\tNODE_7_length_50000_cov_20.5\t"
        "region001\tEXACT_LOCUS\tCURRENT\n",
        encoding="utf-8",
    )
    rows = load_evidence_index(index, loci)
    assert rows[0].binding_state == "EXACT_LOCUS"
    assert rows[0].freshness_state == "CURRENT"


def test_inventory_rejects_exact_locus_conflict(tmp_path):
    inventory = tmp_path / "bad.tsv"
    inventory.write_text(
        "strain\tbgc\tfull_node\tregion\texact_locus\n"
        "REF-001\tBGC001\tNODE_7_length_50000_cov_20.5\tregion001\t"
        "REF-001|NODE_8_length_40000_cov_18.0|region001\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="exact_locus conflicts"):
        load_inventory(inventory)


def test_write_outputs_is_additive_and_manifested(tmp_path):
    inventory, root = _fixture(tmp_path)
    loci = load_inventory(inventory)
    observations = discover_evidence(loci, load_contract(), [("fixture", root)])
    out = tmp_path / "out"
    manifest = write_outputs(out, loci, observations, load_contract())
    assert manifest["status"] == "PASS"
    assert manifest["bgc_count"] == 2
    for item in manifest["outputs"]:
        assert Path(item["path"]).is_file()
    stored = json.loads((out / "modeb_availability_manifest.json").read_text())
    assert stored["contract_id"] == "modeb_evidence_streams_v1"
    with (out / "modeb_bgc_availability.tsv").open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 2


def test_cli_parser_exposes_modeb_availability():
    pytest.importorskip("openpyxl")
    from mamey.cli import build_parser

    args = build_parser().parse_args([
        "modeb-availability",
        "--inventory", "inventory.tsv",
        "--source-root", "package=package_dir",
        "--out", "availability",
    ])
    assert args.command == "modeb-availability"
    assert args.inventory == "inventory.tsv"
