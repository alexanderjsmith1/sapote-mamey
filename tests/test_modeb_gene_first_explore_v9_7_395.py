import csv
import hashlib
import json
from pathlib import Path

import pytest

from mamey.mode_b.gene_first_explore import (
    CHANNELS,
    GeneFirstHold,
    run_gene_first_exploration,
)


STRAIN = "SYNTH-001"
NODE = "NODE_7_length_120000_cov_42.5"
REGION = "region002"
ALIAS = "BGC007"
TOKEN = f"{STRAIN}__{NODE}__{REGION}__{ALIAS}"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    package.mkdir()
    manifest = {
        "strain_id": STRAIN,
        "bgcs": [{
            "bgc_id": ALIAS,
            "contig": NODE,
            "region_number": 2,
            "antismash_region": REGION,
            "products": ["NRPS"],
            "edge_status": "Interior",
        }],
        "source_scans": {
            "mibig_per_gene": {"per_gene_mibig": {
                ALIAS: [{"query_gene": "gene_core", "mibig_accession": "BGC0000001"}]
            }},
            "clusterblast_genes": {"per_gene_best_hit": {
                ALIAS: [{"query_gene": "gene_core", "subject_gene": "ref_1"}]
            }},
            "rggmci": {"ranked_pairs": [{
                "bgc_a": ALIAS, "bgc_b": "BGC008", "rggmci_confidence": "LOW_SHARED_REFERENCE_SIGNAL"
            }]},
        },
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    fields = [
        "bgc_id", "locus_tag", "contig", "cds_start", "cds_end", "strand",
        "aa_length", "product_qualifier", "gene_function_inference", "sec_met_domains",
    ]
    with (package / f"{STRAIN}_gene_by_gene_all_bgcs.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([
            {
                "bgc_id": ALIAS, "locus_tag": "gene_core", "contig": NODE,
                "cds_start": 100, "cds_end": 1299, "strand": "+", "aa_length": 400,
                "product_qualifier": "nonribosomal peptide synthetase",
                "gene_function_inference": "core biosynthetic", "sec_met_domains": "AMP-binding;PCP",
            },
            {
                "bgc_id": ALIAS, "locus_tag": "gene_unknown", "contig": NODE,
                "cds_start": 1400, "cds_end": 1999, "strand": "-", "aa_length": 200,
                "product_qualifier": "hypothetical protein",
                "gene_function_inference": "unknown", "sec_met_domains": "",
            },
        ])
    return package


def _run(package: Path, out: Path, **kwargs):
    return run_gene_first_exploration(
        package=package, strain=STRAIN, full_node=NODE, region=REGION,
        bgc_alias=ALIAS, out=out, **kwargs,
    )


def test_synthetic_offline_rehearsal_emits_exact_identity_and_separate_channels(tmp_path):
    package = _package(tmp_path)
    out_root = tmp_path / "out"
    out_root.mkdir()
    receipt = _run(package, out_root)
    out = out_root / TOKEN
    assert receipt["status"] == "ENGINEERING_EXPLORATION_ONLY"
    assert receipt["exact_identity"]["exact_identity"] == f"{STRAIN} / {NODE} / {REGION} / {ALIAS}"
    channels = list(csv.DictReader((out / f"{TOKEN}__evidence_channels.tsv").open(), delimiter="\t"))
    assert [row["channel"] for row in channels] == [channel for channel, _label in CHANNELS]
    status = {row["channel"]: row["status"] for row in channels}
    assert status["domain"] == "BOUND"
    assert status["mibig"] == "BOUND"
    assert status["clusterblast"] == "BOUND"
    assert status["rggmci"] == "BOUND"
    assert status["nr"] == "MISSING"
    genes = list(csv.DictReader((out / f"{TOKEN}__important_genes.tsv").open(), delimiter="\t"))
    assert genes[0]["locus_tag"] == "gene_core"
    assert genes[0]["exact_identity"] == f"{STRAIN} / {NODE} / {REGION} / {ALIAS}"
    assert receipt["highest_information_next_analysis"]["analysis_id"] == "FILL_NR_GAP"
    assert set(path.name for path in out.iterdir()) == {
        f"{TOKEN}__MODEB_GENE_FIRST_EXPLORATION.md", f"{TOKEN}__important_genes.tsv",
        f"{TOKEN}__evidence_channels.tsv", f"{TOKEN}__exploration_receipt.json",
    }


def test_shortened_node_refuses_before_output_creation(tmp_path):
    package = _package(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(GeneFirstHold, match="shortened NODE token"):
        run_gene_first_exploration(
            package=package, strain=STRAIN, full_node="NODE_7", region=REGION,
            bgc_alias=ALIAS, out=out,
        )
    assert list(out.iterdir()) == []


def test_conflicting_evidence_identity_refuses_before_output_creation(tmp_path):
    package = _package(tmp_path)
    index = tmp_path / "evidence.tsv"
    fields = [
        "channel", "strain", "full_node", "region", "bgc_alias", "gene",
        "evidence_state", "source_locator", "source_sha256", "note",
    ]
    with index.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerow({
            "channel": "nr", "strain": STRAIN,
            "full_node": "NODE_9_length_120000_cov_42.5", "region": REGION,
            "bgc_alias": ALIAS, "gene": "gene_core", "evidence_state": "BOUND",
            "source_locator": "evidence://nr/job-1", "source_sha256": _sha("nr"), "note": "synthetic",
        })
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(GeneFirstHold, match="evidence row 2 conflicts"):
        _run(package, out, evidence_index=index)
    assert list(out.iterdir()) == []


def test_historical_card_is_lead_only_and_never_channel_support(tmp_path):
    package = _package(tmp_path)
    index = tmp_path / "evidence.tsv"
    fields = [
        "channel", "strain", "full_node", "region", "bgc_alias", "gene",
        "evidence_state", "source_locator", "source_sha256", "note",
    ]
    with index.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerow({
            "channel": "historical_card", "strain": STRAIN, "full_node": NODE,
            "region": REGION, "bgc_alias": ALIAS, "gene": "gene_core",
            "evidence_state": "LEAD_ONLY", "source_locator": "legacy/card.md",
            "source_sha256": "", "note": "historical lead",
        })
    out_root = tmp_path / "out"
    out_root.mkdir()
    receipt = _run(package, out_root, evidence_index=index)
    out = out_root / TOKEN
    assert receipt["historical_lead_count"] == 1
    genes = list(csv.DictReader((out / f"{TOKEN}__important_genes.tsv").open(), delimiter="\t"))
    assert "historical_card" not in genes[0]["bound_gene_channels"]
    text = (out / f"{TOKEN}__MODEB_GENE_FIRST_EXPLORATION.md").read_text(encoding="utf-8")
    assert "Historical cards registered as leads only: 1" in text
