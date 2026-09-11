"""Fail-closed regression tests for the external BLASTp SQLite importers.

All fixtures are synthetic.  The tests never discover or open an operator store.
"""
from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from mamey.blastp_ingest import (
    BLASTP_HITS_COLUMNS,
    BlastpStoreSchemaError,
    BlastpStoreWriteError,
    insert_blastp_hits,
    open_blastp_hits_store,
)


ROOT = Path(__file__).resolve().parents[1]
ROLLUP = ROOT / "tools" / "ingest_blastp_rollups.py"
SWISSPROT = ROOT / "tools" / "ingest_swissprot_local.py"
IDENTITY = "SYNTH-001 / NODE_1_length_1000_cov_1.000000 / region001 / BGC001"

HITS_SCHEMA = """
CREATE TABLE hits (
    workspace TEXT NOT NULL,
    strain TEXT NOT NULL,
    bgc_id TEXT NOT NULL,
    gene TEXT NOT NULL,
    aa_length INTEGER,
    role TEXT,
    domains TEXT,
    hit_rank INTEGER,
    subject_acc TEXT,
    subject_organism TEXT,
    subject_def TEXT,
    subject_db TEXT,
    pct_identity REAL,
    align_length INTEGER,
    query_coverage REAL,
    evalue REAL,
    bitscore REAL,
    pct_positives REAL,
    channel TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_mtime TEXT,
    provenance_suspect INTEGER DEFAULT 0
)
"""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_store(root: Path, schema: str = HITS_SCHEMA) -> Path:
    db = root / "BLASTp Database" / "blastp.sqlite"
    db.parent.mkdir(parents=True)
    with sqlite3.connect(db) as con:
        con.executescript(schema)
    return db


def _write_csv(path: Path, *, channel: str, subject_db: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "strain", "bgc_id", "gene", "aa_length", "role", "domains", "hit_rank",
        "subject_acc", "subject_organism", "subject_def", "subject_db", "pct_identity",
        "align_length", "query_coverage", "evalue", "bitscore", "pct_positives", "channel",
    ]
    row = {
        "strain": "SYNTH-001",
        "bgc_id": IDENTITY,
        "gene": "ctg1_1",
        "aa_length": "101",
        "role": "synthetic_test_role",
        "domains": "synthetic_test_domain",
        "hit_rank": "1",
        "subject_acc": "SYNTH_ACC_1",
        "subject_organism": "Synthetic organism",
        "subject_def": "synthetic fixture protein",
        "subject_db": subject_db,
        "pct_identity": "51.0",
        "align_length": "100",
        "query_coverage": "99.0",
        "evalue": "1e-20",
        "bitscore": "150.0",
        "pct_positives": "66.0",
        "channel": channel,
    }
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)


def _rollup_csv(root: Path, channel: str = "ncbi_nr") -> Path:
    path = root / "strain_data" / "SYNTH-001" / "blastp_nr_fixture" / "SYNTH-001_nr_top10_fixture.csv"
    _write_csv(path, channel=channel, subject_db="nr")
    return path


def _swiss_csv(root: Path) -> Path:
    path = (
        root / "Local Blastp RESULTS (SwissProt)" / "SYNTH-001" / "BGC001"
        / "BGC001_blastp_top10_local.csv"
    )
    _write_csv(path, channel="ignored_by_fixed_channel_importer", subject_db="swissprot")
    return path


def _run(tool: Path, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["SAPOTE_ROOT"] = str(root)
    env.pop("SAPOTE_WORKSPACE_ROOT", None)
    return subprocess.run(
        [sys.executable, str(tool), *args],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_contract_owns_exact_twenty_two_columns():
    assert len(BLASTP_HITS_COLUMNS) == 22
    assert BLASTP_HITS_COLUMNS[:4] == ("workspace", "strain", "bgc_id", "gene")
    assert BLASTP_HITS_COLUMNS[-4:] == (
        "channel", "source_file", "source_mtime", "provenance_suspect"
    )


@pytest.mark.parametrize("tool", [ROLLUP, SWISSPROT])
def test_missing_store_refuses_without_creating_a_database(tmp_path, tool):
    expected = tmp_path / "BLASTp Database" / "blastp.sqlite"
    result = _run(tool, tmp_path)
    assert result.returncode != 0
    assert "BLASTP_STORE_MISSING" in result.stderr
    assert not expected.exists()


@pytest.mark.parametrize("schema", [
    "CREATE TABLE hits (workspace TEXT)",
    HITS_SCHEMA.replace("workspace TEXT NOT NULL,\n    strain TEXT NOT NULL,", "strain TEXT NOT NULL,\n    workspace TEXT NOT NULL,"),
])
def test_missing_or_reordered_schema_is_a_typed_hold_without_mutation(tmp_path, schema):
    db = _make_store(tmp_path, schema)
    before = _sha(db)
    with pytest.raises(BlastpStoreSchemaError, match="BLASTP_STORE_SCHEMA_HOLD"):
        open_blastp_hits_store(db, writable=False)
    assert _sha(db) == before


def test_rollup_dry_run_is_read_only_and_reports_candidates(tmp_path):
    db = _make_store(tmp_path)
    _rollup_csv(tmp_path)
    before = _sha(db)
    result = _run(ROLLUP, tmp_path)
    assert result.returncode == 0, result.stderr
    assert "NEW (strain,channel,gene) rows to add: 1" in result.stdout
    assert "DRY-RUN" in result.stdout
    assert _sha(db) == before
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM hits").fetchone()[0] == 0


@pytest.mark.parametrize("tool,csv_builder", [(ROLLUP, _rollup_csv), (SWISSPROT, _swiss_csv)])
def test_execute_requires_explicit_source_workspace_before_any_write(tmp_path, tool, csv_builder):
    db = _make_store(tmp_path)
    csv_builder(tmp_path)
    before = _sha(db)
    result = _run(tool, tmp_path, "--execute")
    assert result.returncode != 0
    assert "--source-workspace is required with --execute" in result.stderr
    assert _sha(db) == before


def test_rollup_execute_is_named_column_atomic_and_idempotent(tmp_path):
    db = _make_store(tmp_path)
    _rollup_csv(tmp_path)
    first = _run(ROLLUP, tmp_path, "--execute", "--source-workspace", "synthetic-import")
    assert first.returncode == 0, first.stderr
    second = _run(ROLLUP, tmp_path, "--execute", "--source-workspace", "synthetic-import")
    assert second.returncode == 0, second.stderr
    with sqlite3.connect(db) as con:
        rows = con.execute(
            "SELECT workspace, strain, bgc_id, gene, channel, source_file FROM hits"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][:5] == (
        "synthetic-import", "SYNTH-001", IDENTITY, "ctg1_1", "ncbi_nr"
    )
    assert rows[0][5].endswith("SYNTH-001_nr_top10_fixture.csv")


def test_rollup_channel_conflict_refuses_the_entire_transaction(tmp_path):
    db = _make_store(tmp_path)
    _rollup_csv(tmp_path, channel="local_swissprot")
    before = _sha(db)
    result = _run(ROLLUP, tmp_path, "--execute", "--source-workspace", "synthetic-import")
    assert result.returncode != 0
    assert "BLASTP_ROLLUP_CHANNEL_HOLD" in result.stderr
    assert _sha(db) == before


def test_multirow_write_rolls_back_if_any_row_violates_the_store(tmp_path):
    schema = HITS_SCHEMA.replace(
        "gene TEXT NOT NULL,", "gene TEXT NOT NULL CHECK(gene != 'ctg1_bad'),"
    )
    db = _make_store(tmp_path, schema)
    template = (
        "synthetic-import", "SYNTH-001", IDENTITY, "ctg1_1", 101, "role", "domain", 1,
        "SYNTH_ACC_1", "Synthetic organism", "synthetic fixture protein", "nr", 51.0,
        100, 99.0, 1e-20, 150.0, 66.0, "ncbi_nr", "synthetic.csv", "2026-08-30", 0,
    )
    bad = list(template)
    bad[3] = "ctg1_bad"
    connection = open_blastp_hits_store(db, writable=True)
    try:
        with pytest.raises(BlastpStoreWriteError, match="BLASTP_STORE_WRITE_HOLD"):
            insert_blastp_hits(connection, [template, tuple(bad)])
    finally:
        connection.close()
    with sqlite3.connect(db) as check:
        assert check.execute("SELECT COUNT(*) FROM hits").fetchone()[0] == 0


def test_swissprot_execute_preserves_fixed_channel_and_source_workspace(tmp_path):
    db = _make_store(tmp_path)
    _swiss_csv(tmp_path)
    result = _run(SWISSPROT, tmp_path, "--execute", "--source-workspace", "synthetic-import")
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(db) as con:
        row = con.execute(
            "SELECT workspace, strain, bgc_id, gene, channel, subject_db FROM hits"
        ).fetchone()
    assert row == (
        "synthetic-import", "SYNTH-001", IDENTITY, "ctg1_1", "local_swissprot", "swissprot"
    )
