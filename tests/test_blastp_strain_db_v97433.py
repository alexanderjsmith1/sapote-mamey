"""Per-strain BLASTp export guards, including drifted BGC aliases."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from mamey.blastp_ingest import (
    BLASTP_HITS_COLUMNS, BLASTP_HITS_SCHEMA, validate_blastp_hits_store,
)
from mamey.blastp_strain_db import StrainBlastpHold, build, inspect, main


def _source(path: Path) -> Path:
    with sqlite3.connect(path) as connection:
        columns = ", ".join(
            f"{name} {kind}{' NOT NULL' if required else ''}"
            for name, kind, required in BLASTP_HITS_SCHEMA
        )
        connection.execute(f"CREATE TABLE hits ({columns})")
        keys = ", ".join(BLASTP_HITS_COLUMNS)
        marks = ", ".join("?" for _ in BLASTP_HITS_COLUMNS)
        for strain, gene, channel, source_alias, identity, aa in [
            ("STR-A", "ctg2_1", "ncbi_nr", "BGC001", 87.42, 320),
            ("STR-A", "ctg2_1", "ncbi_clustered_nr", "BGC001", 72.5, 320),
            ("STR-A", "ctg2_2", "ncbi_nr", "BGC001", 61.0, 210),
            ("STR-A", "old_assembly_1", "local_swissprot", "BGC099", 43.0, 200),
            ("STR-B", "ctg7_1", "ncbi_clustered_nr", "BGC002", 91.0, 400),
        ]:
            row = {name: None for name in BLASTP_HITS_COLUMNS}
            row.update(
                workspace="fixture", strain=strain, bgc_id=source_alias, gene=gene,
                aa_length=aa, provenance_suspect=0,
                hit_rank=1, subject_acc="ACC1", pct_identity=identity,
                channel=channel, source_file="fixture.tsv",
            )
            connection.execute(
                f"INSERT INTO hits ({keys}) VALUES ({marks})",
                [row[name] for name in BLASTP_HITS_COLUMNS],
            )
    return path


def _package(root: Path, strain: str, genes: list[tuple]) -> Path:
    package = root / strain / "package"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(
        json.dumps({"strain_id": strain}), encoding="utf-8"
    )
    with (package / f"{strain}_cds_table.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["strain", "contig", "region", "bgc_id",
                                "locus_tag", "length_aa"],
        )
        writer.writeheader()
        for gene, contig, region, alias, aa in genes:
            writer.writerow(dict(
                strain=strain, contig=contig, region=region,
                bgc_id=alias, locus_tag=gene, length_aa=aa,
            ))
    return package


def test_export_uses_current_locus_and_separate_channels_without_rewriting_source(tmp_path):
    source = _source(tmp_path / "cohort.sqlite")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    package = _package(tmp_path, "STR-A", [
        ("ctg2_1", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 320),
        ("ctg2_2", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 210),
        ("ctg2_3", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 90),
    ])
    result = build(source, package, tmp_path / "out")
    assert result["genes"] == 3
    assert result["raw_hits"] == 4
    assert result["locus_bound_hits"] == 3
    assert result["held_hit_rows"] == 1
    assert result["unbound_hit_rows"] == 1
    assert result["with_nr"] == 2
    assert result["with_clustered_nr"] == 1
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    output = Path(result["path"])
    with sqlite3.connect(output) as connection:
        validate_blastp_hits_store(connection)
        assert connection.execute(
            "SELECT contig,region,bgc_alias,has_nr,has_clustered_nr,best_nr "
            "FROM coverage WHERE gene='ctg2_1'"
        ).fetchone() == ("NODE_2_length_9000_cov_44.1", "region001", "BGC002", 1, 1, 87.42)
        assert connection.execute(
            "SELECT bgc_id FROM hits WHERE gene='ctg2_1' LIMIT 1"
        ).fetchone()[0] == "BGC001"
        assert connection.execute(
            "SELECT gene FROM clustered_gap"
        ).fetchall() == [("ctg2_2",)]
        assert connection.execute(
            "SELECT gene,has_nr,has_clustered_nr FROM coverage WHERE gene='ctg2_3'"
        ).fetchone() == ("ctg2_3", 0, 0)
        receipt = dict(connection.execute("SELECT key,value FROM source_receipt"))
        snapshot = output.parent / receipt["source_snapshot_file"]
        assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == receipt["source_snapshot_sha256"]
    assert inspect(output)["schema"] == "mamey_blastp_strain_db_v2"


def test_existing_output_is_preserved_until_explicit_replace(tmp_path):
    source = _source(tmp_path / "source.sqlite")
    package = _package(tmp_path, "STR-A", [
        ("ctg2_1", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 320),
    ])
    output = Path(build(source, package, tmp_path / "out")["path"])
    before = hashlib.sha256(output.read_bytes()).hexdigest()
    with pytest.raises(StrainBlastpHold, match="OUTPUT_EXISTS"):
        build(source, package, tmp_path / "out")
    assert hashlib.sha256(output.read_bytes()).hexdigest() == before
    assert build(source, package, tmp_path / "out", replace=True)["raw_hits"] == 4
    assert not list((tmp_path / "out").glob("*.tmp"))


def test_ambiguous_gene_identity_fails_before_output(tmp_path):
    source = _source(tmp_path / "source.sqlite")
    package = _package(tmp_path, "STR-A", [
        ("ctg2_1", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 320),
        ("ctg2_1", "NODE_7_length_8000_cov_33.0", "region002", "BGC004", 320),
    ])
    with pytest.raises(StrainBlastpHold, match="GENE_AMBIGUOUS"):
        build(source, package, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_length_and_missing_length_are_retained_but_not_locus_bound(tmp_path):
    source = _source(tmp_path / "source.sqlite")
    with sqlite3.connect(source) as connection:
        connection.execute("UPDATE hits SET aa_length=319 WHERE gene='ctg2_1' AND channel='ncbi_nr'")
        connection.execute("UPDATE hits SET aa_length=NULL WHERE gene='ctg2_2'")
    package = _package(tmp_path, "STR-A", [
        ("ctg2_1", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 320),
        ("ctg2_2", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 210),
    ])
    result = build(source, package, tmp_path / "out")
    assert result["raw_hits"] == 4
    assert result["locus_bound_hits"] == 1
    assert result["held_hit_rows"] == 3
    assert result["with_nr"] == 0
    assert result["with_clustered_nr"] == 1
    with sqlite3.connect(result["path"]) as connection:
        assert dict(connection.execute(
            "SELECT binding_state,COUNT(*) FROM held_hits GROUP BY binding_state"
        )) == {"NONCURRENT_LOCUS": 1, "QUERY_CURRENT_AA_LENGTH_MISMATCH": 1,
               "ZERO_OR_BLANK_AA_LENGTH": 1}


def test_committed_wal_rows_are_in_persisted_snapshot(tmp_path):
    source = _source(tmp_path / "source.sqlite")
    package = _package(tmp_path, "STR-A", [
        ("ctg2_1", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 320),
        ("ctg2_2", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 210),
    ])
    with sqlite3.connect(source) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("UPDATE hits SET subject_acc='WAL-COMMITTED' WHERE gene='ctg2_2'")
        writer.commit()
        assert (tmp_path / "source.sqlite-wal").exists()
        result = build(source, package, tmp_path / "out")
    with sqlite3.connect(result["path"]) as connection:
        assert connection.execute(
            "SELECT subject_acc FROM locus_bound_hits WHERE gene='ctg2_2'"
        ).fetchone()[0] == "WAL-COMMITTED"
        receipt = dict(connection.execute("SELECT key,value FROM source_receipt"))
    snapshot = tmp_path / "out" / receipt["source_snapshot_file"]
    assert snapshot.exists()
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == receipt["source_snapshot_sha256"]


def test_two_packages_build_two_independent_strain_files(tmp_path, capsys):
    source = _source(tmp_path / "source.sqlite")
    first = _package(tmp_path, "STR-A", [
        ("ctg2_1", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 320),
    ])
    second = _package(tmp_path, "STR-B", [
        ("ctg7_1", "NODE_7_length_8000_cov_33.0", "region003", "BGC005", 400),
    ])
    assert main(["build", "--source-db", str(source), "--package", str(first),
                 str(second), "--out", str(tmp_path / "out")]) == 0
    report = json.loads(capsys.readouterr().out)
    assert {row["strain"] for row in report} == {"STR-A", "STR-B"}
    assert len(list((tmp_path / "out").glob("source_snapshot_*.sqlite"))) == 1
    assert inspect(tmp_path / "out" / "STR-A_blastp.db")["strains_in_hits"] == ["STR-A"]
    assert inspect(tmp_path / "out" / "STR-B_blastp.db")["strains_in_hits"] == ["STR-B"]


def test_duplicate_package_batch_refuses_before_any_output(tmp_path, capsys):
    source = _source(tmp_path / "source.sqlite")
    package = _package(tmp_path, "STR-A", [
        ("ctg2_1", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 320),
    ])
    assert main(["build", "--source-db", str(source), "--package",
                 str(package), str(package), "--out", str(tmp_path / "out")]) == 2
    assert "DUPLICATE_STRAIN_PACKAGE" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_missing_source_strain_holds_whole_batch_before_strain_outputs(tmp_path, capsys):
    source = _source(tmp_path / "source.sqlite")
    first = _package(tmp_path, "STR-A", [
        ("ctg2_1", "NODE_2_length_9000_cov_44.1", "region001", "BGC002", 320),
    ])
    renamed = _package(tmp_path, "STR-B_v30", [
        ("ctg7_1", "NODE_7_length_8000_cov_33.0", "region003", "BGC005", 400),
    ])
    out = tmp_path / "out"
    assert main(["build", "--source-db", str(source), "--package",
                 str(first), str(renamed), "--out", str(out)]) == 2
    assert "SOURCE_STRAIN_ABSENT: STR-B_v30" in capsys.readouterr().err
    assert not list(out.glob("*_blastp.db"))
    assert len(list(out.glob("source_snapshot_*.sqlite"))) == 1


def test_reviewed_strain_map_is_explicit_and_recorded(tmp_path, capsys):
    source = _source(tmp_path / "source.sqlite")
    package = _package(tmp_path, "STR-B_v30", [
        ("ctg7_1", "NODE_7_length_8000_cov_33.0", "region003", "BGC005", 400),
    ])
    mapping = tmp_path / "map.tsv"
    mapping.write_text("package_strain\tsource_strain\nSTR-B_v30\tSTR-B\n")
    out = tmp_path / "out"
    assert main(["build", "--source-db", str(source), "--package", str(package),
                 "--out", str(out), "--strain-map", str(mapping)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report[0]["raw_hits"] == 1
    assert report[0]["locus_bound_hits"] == 1
    with sqlite3.connect(out / "STR-B_v30_blastp.db") as connection:
        assert dict(connection.execute("SELECT key,value FROM source_receipt"))[
            "source_strain"] == "STR-B"
        assert connection.execute("SELECT DISTINCT strain FROM hits").fetchall() == [("STR-B",)]


def test_empty_export_requires_explicit_option(tmp_path, capsys):
    source = _source(tmp_path / "source.sqlite")
    package = _package(tmp_path, "STR-C", [
        ("ctg9_1", "NODE_9_length_8000_cov_33.0", "region001", "BGC001", 100),
    ])
    out = tmp_path / "out"
    assert main(["build", "--source-db", str(source), "--package", str(package),
                 "--out", str(out)]) == 2
    assert "SOURCE_STRAIN_ABSENT" in capsys.readouterr().err
    assert main(["build", "--source-db", str(source), "--package", str(package),
                 "--out", str(out), "--allow-empty"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["raw_hits"] == 0
