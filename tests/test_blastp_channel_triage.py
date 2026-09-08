from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from mamey.blastp_channel_triage import ContractError, build_triage


NODE = "NODE_000001_length_1000_cov_20.0"
NR_SHA = "a" * 64
CLUSTERED_SHA = "b" * 64
UNKNOWN_SHA = "c" * 64


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    identity = tmp_path / "identity.tsv"
    provenance = tmp_path / "provenance.tsv"
    hits = tmp_path / "hits.tsv"
    _write_tsv(
        identity,
        [{"strain": "TEST-001", "full_node": NODE, "region": "region001", "bgc_alias": "BGC001"}],
    )
    _write_tsv(
        provenance,
        [
            {
                "channel": "nr",
                "source_file_sha256": NR_SHA,
                "source_locator": "receipts/nr_top10.tsv",
                "source_bytes": "120",
                "source_label": "nr source receipt",
            },
            {
                "channel": "clustered_nr",
                "source_file_sha256": CLUSTERED_SHA,
                "source_locator": "receipts/clustered_nr_top10.tsv",
                "source_bytes": "121",
                "source_label": "clustered_nr source receipt",
            },
            {
                "channel": "clustered_nr",
                "source_file_sha256": NR_SHA,
                "source_locator": "receipts/shared_artifact.tsv",
                "source_bytes": "120",
                "source_label": "separately labelled shared artifact",
            },
        ],
    )
    rows: list[dict[str, str]] = []

    def add(gene: str, channel: str, subject: str, source_sha: str, rank: str = "1") -> None:
        rows.append(
            {
                "strain": "TEST-001",
                "bgc_id": "BGC001",
                "gene": gene,
                "hit_rank": rank,
                "subject_acc": subject,
                "channel": channel,
                "source_file_sha256": source_sha,
                "pct_identity": "90.1",
                "query_coverage": "99.0",
            }
        )

    add("gene_001", "nr", "ACC_NR", NR_SHA)
    add("gene_001", "clustered_nr", "ACC_CLUSTERED", CLUSTERED_SHA)
    add("gene_002", "nr", "ACC_SHARED", NR_SHA)
    add("gene_002", "clustered_nr", "ACC_SHARED", CLUSTERED_SHA)
    add("gene_003", "nr", "ACC_ONLY_NR", NR_SHA)
    add("gene_004", "clustered_nr", "ACC_ONLY_CLUSTERED", CLUSTERED_SHA)
    add("gene_005", "nr", "ACC_DUPLICATE_A", NR_SHA)
    add("gene_005", "nr", "ACC_DUPLICATE_B", NR_SHA)
    add("gene_005", "clustered_nr", "ACC_CLUSTERED", CLUSTERED_SHA)
    add("gene_006", "nr", "ACC_UNBOUND", UNKNOWN_SHA)
    add("gene_006", "clustered_nr", "ACC_CLUSTERED", CLUSTERED_SHA)
    add("gene_007", "nr", "ACC_SAME_ARTIFACT", NR_SHA)
    add("gene_007", "clustered_nr", "ACC_SAME_ARTIFACT", NR_SHA)
    add("gene_008", "nr", "ACC_RANK_TWO", NR_SHA, rank="2")
    _write_tsv(hits, rows)
    return hits, identity, provenance


def test_typed_triage_preserves_distinct_channels_and_provenance(tmp_path: Path) -> None:
    hits, identity, provenance = _inputs(tmp_path)
    rows, receipt = build_triage(hits, identity, provenance)
    by_gene = {row["locus_tag"]: row for row in rows}

    assert by_gene["gene_001"]["triage_state"] == "DISAGREE_DIFFERENT_SUBJECT_ACCESSION"
    assert by_gene["gene_001"]["nr_subject_acc"] == "ACC_NR"
    assert by_gene["gene_001"]["clustered_nr_subject_acc"] == "ACC_CLUSTERED"
    assert by_gene["gene_002"]["triage_state"] == "CONCORDANT_SUBJECT_ACCESSION"
    assert by_gene["gene_003"]["triage_state"] == "ONLY_NR"
    assert by_gene["gene_004"]["triage_state"] == "ONLY_CLUSTERED_NR"
    assert by_gene["gene_005"]["triage_state"] == "HOLD_AMBIGUOUS_RANK1"
    assert by_gene["gene_005"]["clustered_nr_subject_acc"] == "ACC_CLUSTERED"
    assert by_gene["gene_006"]["triage_state"] == "HOLD_MISSING_PROVENANCE"
    assert by_gene["gene_007"]["triage_state"] == "HOLD_SHARED_SOURCE_ARTIFACT"
    assert by_gene["gene_008"]["triage_state"] == "HOLD_MISSING_RANK1"
    assert receipt["contract"]["cross_channel_winner_selected"] is False
    assert receipt["rows"]["non_rank1_input_rows_not_compared"] == 1


def test_alias_only_or_missing_identity_fails_closed(tmp_path: Path) -> None:
    hits, identity, provenance = _inputs(tmp_path)
    rows = list(csv.DictReader(hits.open(encoding="utf-8"), delimiter="\t"))
    rows[0]["bgc_id"] = "BGC_UNMAPPED"
    _write_tsv(hits, rows)

    with pytest.raises(ContractError, match="refusing alias-only grouping"):
        build_triage(hits, identity, provenance)


def test_cli_writes_portable_receipt_and_refuses_overwrite(tmp_path: Path) -> None:
    hits, identity, provenance = _inputs(tmp_path)
    output = tmp_path / "triage_output"
    tool = Path(__file__).parents[1] / "tools" / "blastp_channel_triage.py"
    command = [
        sys.executable,
        str(tool),
        "--hits",
        str(hits),
        "--identity-map",
        str(identity),
        "--provenance",
        str(provenance),
        "--out",
        str(output),
    ]
    first = subprocess.run(command, text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr
    report = json.loads(first.stdout)
    assert report["triage_table"]["name"] == "blastp_channel_triage.tsv"
    assert str(tmp_path) not in first.stdout
    receipt = json.loads((output / "blastp_channel_triage_receipt.json").read_text(encoding="utf-8"))
    assert receipt["input_bindings"]["hits"]["name"] == "hits.tsv"
    assert receipt["contract"]["source_label_default_allowed"] is False
    second = subprocess.run(command, text=True, capture_output=True, check=False)
    assert second.returncode == 2
    assert "refusing to overwrite" in second.stderr
