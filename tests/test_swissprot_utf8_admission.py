"""Encoding/provenance admission using a new synthetic store; never run BLAST."""
import csv
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import sqlite3
import pytest
from mamey.blastp_ingest import BLASTP_HITS_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("swissprot_candidate", ROOT / "tools/ingest_swissprot_local.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
FIELDS = ["strain", "gene", "bgc_id", "hit_rank", "subject_acc", "subject_def"]


def setup(tmp_path):
    db = tmp_path / "software.sqlite"
    columns = ",".join(name + " " + kind + (" NOT NULL" if required else "") for name, kind, required in BLASTP_HITS_SCHEMA)
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE hits (" + columns + ")")
    directory = tmp_path / "Local Blastp RESULTS (SwissProt)"
    directory.mkdir()
    return db, directory


def source(path, corrupt=None, gene="software_gene"):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerow(dict(strain="SOFTWARE", gene="first_valid_gene", bgc_id="software_identity", hit_rank=1, subject_acc="FIRST", subject_def="first valid row"))
    row = dict(strain="SOFTWARE", gene=gene, bgc_id="software_identity", hit_rank=2, subject_acc="SECOND", subject_def="comma-bearing, Unicode café description")
    if corrupt:
        row[corrupt] = "software___BAD_BYTE__value"
    writer.writerow(row)
    data = text.getvalue().encode("utf-8").replace(b"__BAD_BYTE__", b"\xff")
    path.write_bytes(data)
    return data


def invoke(tmp_path, db, execute):
    args = ["--root", str(tmp_path), "--db", str(db)]
    if execute:
        args += ["--execute", "--source-workspace", "software-import"]
    return tool.main(args)


@pytest.mark.parametrize("execute", [False, True])
@pytest.mark.parametrize("field", ["strain", "gene", "subject_acc", "subject_def"])
def test_invalid_bytes_skip_whole_file_without_identity_replacement(tmp_path, capsys, execute, field):
    db, directory = setup(tmp_path)
    path = directory / "bad_blastp_top10_local.csv"
    original = source(path, corrupt=field)
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    assert invoke(tmp_path, db, execute) == 0
    captured = capsys.readouterr()
    with sqlite3.connect(db) as connection:
        rows = connection.execute("SELECT gene,subject_acc,subject_def FROM hits").fetchall()
    assert rows == []
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    assert path.read_bytes() == original
    assert "unreadable: 1" in captured.out and "rows to add: 0" in captured.out
    assert path.name in captured.err and "utf-8" in captured.err
    assert "no-hit" not in (captured.out + captured.err).lower()


@pytest.mark.parametrize("gene", ["software_café", "software_\ufffd"])
def test_valid_unicode_and_literal_replacement_character_preserved(tmp_path, capsys, gene):
    db, directory = setup(tmp_path)
    path = directory / "valid_blastp_top10_local.csv"
    original = source(path, gene=gene)
    assert invoke(tmp_path, db, True) == 0
    assert "unreadable: 0" in capsys.readouterr().out
    with sqlite3.connect(db) as connection:
        rows = connection.execute("SELECT gene,subject_def,workspace,channel,source_file FROM hits ORDER BY hit_rank").fetchall()
    assert rows[1][0] == gene
    assert rows[1][1] == "comma-bearing, Unicode café description"
    assert rows[1][2:4] == ("software-import", "local_swissprot")
    assert rows[1][4] == os.path.relpath(path, tmp_path)
    assert path.read_bytes() == original


def test_other_readable_files_remain_explicit_partial_batch(tmp_path, capsys):
    db, directory = setup(tmp_path)
    bad = directory / "bad_blastp_top10_local.csv"
    good = directory / "good_blastp_top10_local.csv"
    originals = {bad: source(bad, corrupt="gene"), good: source(good, gene="good_gene")}
    assert invoke(tmp_path, db, True) == 0
    captured = capsys.readouterr()
    assert "unreadable: 1" in captured.out and "inserted 2" in captured.out
    assert bad.name in captured.err
    with sqlite3.connect(db) as connection:
        sources = connection.execute("SELECT DISTINCT source_file FROM hits").fetchall()
    assert sources == [(os.path.relpath(good, tmp_path),)]
    assert all(path.read_bytes() == data for path, data in originals.items())
