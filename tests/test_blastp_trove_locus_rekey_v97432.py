"""Regression coverage for package-authoritative BLASTp trove locus re-keying."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from mamey.blastp_ingest import ingest_blastp_trove


ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package(
        tmp_path: Path, *, ambiguous: bool = False, cds_table: bool = True,
        gene_context: bool = True, blank_current_length: bool = False) -> Path:
    package = tmp_path / "package"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(
        json.dumps({"strain_id": "AS-TEST"}), encoding="utf-8"
    )
    records = [
        {"bgc_id": "BGC001", "cds": [{"locus_tag": "ctg101_1", "aa_length": 210}]},
        {"bgc_id": "BGC002", "cds": [{"locus_tag": "ctg109_3", "aa_length": 300}]},
        {"bgc_id": "BGC003", "cds": [{"locus_tag": "ctg201_1", "aa_length": 410}]},
    ]
    if ambiguous:
        records[2]["cds"].append({"locus_tag": "ctg109_3", "aa_length": 300})
    if gene_context:
        (package / "AS-TEST_gene_context.jsonl").write_text(
            "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
        )
    if cds_table:
        rows = [
            {"strain": "AS-TEST", "bgc_id": "BGC001", "locus_tag": "ctg101_1", "length_aa": "210"},
            {"strain": "AS-TEST", "bgc_id": "BGC002", "locus_tag": "ctg109_3",
             "length_aa": "" if blank_current_length else "300"},
            {"strain": "AS-TEST", "bgc_id": "BGC003", "locus_tag": "ctg201_1", "length_aa": "410"},
        ]
        if ambiguous:
            rows.append(
                {"strain": "AS-TEST", "bgc_id": "BGC003", "locus_tag": "ctg109_3", "length_aa": "300"}
            )
        with (package / "AS-TEST_cds_table.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["strain", "bgc_id", "locus_tag", "length_aa"])
            writer.writeheader()
            writer.writerows(rows)
    return package


def _trove(
        tmp_path: Path, rows: list[dict], *, source_bgc: str = "BGC001") -> tuple[Path, Path]:
    root = tmp_path / "trove"
    folder = root / "AS-TEST" / source_bgc
    folder.mkdir(parents=True)
    source = folder / f"{source_bgc}_top_hit_per_gene.csv"
    fields = sorted({key for row in rows for key in row})
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return root, source


def _row(locus: str = "ctg109_3", aa_length: str = "300", **overrides) -> dict:
    row = {
        "strain": "AS-TEST",
        "bgc_id": "BGC001",
        "gene": locus,
        "aa_length": aa_length,
        "subject_acc": "WP_TEST.1",
        "subject_organism": "Streptomyces testensis",
        "subject_def": "test protein",
        "pct_identity": "72.0",
        "query_coverage": "98.0",
        "evalue": "1e-40",
        "bitscore": "200",
    }
    row.update(overrides)
    return row


def _csv_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_strict_default_still_rejects_stale_alias(tmp_path):
    package = _package(tmp_path)
    trove, _ = _trove(tmp_path, [_row()])
    result = ingest_blastp_trove(package, trove, "nr", "AS-TEST")
    assert result["genes"] == 0 and result["rekey_by_locus"] is False
    assert _csv_rows(Path(result["quarantine"]))[0]["reason"] == "NONCURRENT_LOCUS"
    assert not (package / "blastp_online" / "BGC002_online_blastp.csv").exists()


def test_rekey_routes_rows_from_one_stale_folder_to_multiple_current_bgcs(tmp_path):
    package = _package(tmp_path)
    trove, source = _trove(tmp_path, [_row(), _row("ctg201_1", "410", subject_acc="WP_OTHER.1")])
    source_before = _sha(source)

    result = ingest_blastp_trove(
        package, trove, "nr", "AS-TEST", rekey_by_locus=True
    )

    assert result["genes"] == 2 and result["quarantined"] == 0
    assert result["bgcs_written"] == {"BGC002": 1, "BGC003": 1}
    assert result["rekey_resolution_counts"] == {"REKEYED_BY_CURRENT_CDS_TABLE": 2}
    assert _sha(source) == source_before
    assert not (package / "blastp_online" / "BGC001_online_blastp.csv").exists()
    for bgc, locus in (("BGC002", "ctg109_3"), ("BGC003", "ctg201_1")):
        row = _csv_rows(package / "blastp_online" / f"{bgc}_online_blastp.csv")[0]
        assert row["locus_tag"] == locus
        assert row["query_bgc"] == bgc
        assert row["source_query_bgc"] == "BGC001"
        assert row["locus_rekey_state"] == "REKEYED_BY_CURRENT_CDS_TABLE"

    receipt = json.loads(Path(result["receipt"]).read_text())
    assert receipt["schema"] == "mamey_blastp_locus_rekey_ingest_v2"
    assert receipt["locus_rekey"]["admitted_current_bgcs"] == {"BGC002": 1, "BGC003": 1}
    ledger = json.loads((package / "blastp_online" / "_ingest_ledger.json").read_text())
    assert ledger["nr"]["BGC002"]["source_sha256"] == [source_before]
    assert ledger["nr"]["BGC003"]["source_sha256"] == [source_before]


def test_rekey_uses_cds_table_without_gene_context_and_records_confirmed_alias(tmp_path):
    package = _package(tmp_path, gene_context=False)
    trove, _ = _trove(tmp_path, [_row(bgc_id="BGC002")], source_bgc="BGC002")
    result = ingest_blastp_trove(
        package, trove, "nr", "AS-TEST", rekey_by_locus=True
    )
    assert result["genes"] == 1
    overlay = _csv_rows(package / "blastp_online" / "BGC002_online_blastp.csv")[0]
    assert overlay["query_bgc"] == "BGC002"
    assert overlay["source_query_bgc"] == "BGC002"
    assert overlay["locus_rekey_state"] == "CURRENT_ALIAS_CONFIRMED_BY_CDS_TABLE"


@pytest.mark.parametrize(
    ("package_kwargs", "row", "reason", "resolved_bgc"),
    [
        ({}, _row("ctg999_1", "300"), "LOCUS_ABSENT_FROM_CURRENT_PACKAGE", ""),
        ({"ambiguous": True}, _row(), "LOCUS_AMBIGUOUS_IN_CURRENT_PACKAGE", "BGC002;BGC003"),
        ({"blank_current_length": True}, _row(),
         "CURRENT_AA_LENGTH_AMBIGUOUS_OR_UNAVAILABLE", "BGC002"),
        ({}, _row(aa_length="299"), "QUERY_CURRENT_AA_LENGTH_MISMATCH", "BGC002"),
        ({}, _row(aa_length=""), "ZERO_OR_BLANK_AA_LENGTH", "BGC002"),
    ],
)
def test_rekey_preserves_distinct_typed_holds(
        tmp_path, package_kwargs, row, reason, resolved_bgc):
    package = _package(tmp_path, **package_kwargs)
    trove, _ = _trove(tmp_path, [row])
    result = ingest_blastp_trove(
        package, trove, "nr", "AS-TEST", rekey_by_locus=True
    )
    assert result["genes"] == 0 and result["quarantined"] == 1
    quarantine = _csv_rows(Path(result["quarantine"]))[0]
    assert quarantine["reason"] == reason
    assert quarantine["source_bgc"] == "BGC001"
    assert quarantine["source_query_bgc"] == "BGC001"
    assert quarantine["resolved_bgc"] == resolved_bgc
    assert not (package / "blastp_online" / "BGC002_online_blastp.csv").exists()


def test_rekey_requires_one_package_cds_table_before_output_write(tmp_path):
    package = _package(tmp_path, cds_table=False)
    trove, _ = _trove(tmp_path, [_row()])
    with pytest.raises(ValueError, match="BLASTP_TROVE_REKEY_REQUIRES_ONE_CDS_TABLE"):
        ingest_blastp_trove(
            package, trove, "nr", "AS-TEST", rekey_by_locus=True
        )
    assert not (package / "blastp_online").exists()


def test_cli_exposes_explicit_rekey_mode(tmp_path):
    package = _package(tmp_path)
    trove, _ = _trove(tmp_path, [_row()])
    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "mamey_run.py"),
            "ingest-blastp-trove",
            "--trove", str(trove),
            "--package", str(package),
            "--channel", "nr",
            "--strain", "AS-TEST",
            "--rekey-by-locus",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert process.returncode == 0, process.stdout
    assert "rekey_by_locus=True" in process.stdout
    assert (package / "blastp_online" / "BGC002_online_blastp.csv").is_file()
