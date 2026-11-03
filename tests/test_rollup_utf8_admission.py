"""Strict text admission over synthetic nr/clustered-nr CSVs; never run BLAST."""
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
spec = importlib.util.spec_from_file_location("rollup_candidate", ROOT / "tools/ingest_blastp_rollups.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
ROUTES = {
    "nr": ("strain_data/SOFTWARE/blastp_nr_fixture/SOFTWARE_nr_top10_fixture.csv", "ncbi_nr", "nr"),
    "clustered": ("strain_data/SOFTWARE/blastp_clustered_nr_fixture/SOFTWARE_clustered_nr_top10_fixture.csv", "ncbi_clustered_nr", "nr_cluster_seq"),
    "runner": ("Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_SOFTWARE/results/SOFTWARE/SOFTWARE_blastp_top10_clustered.csv", "", ""),
}
FIELDS = ["strain", "gene", "bgc_id", "hit_rank", "subject_acc", "subject_def", "channel", "subject_db"]


def make_store(root):
    db = root / "software.sqlite"
    columns = ",".join(name + " " + kind + (" NOT NULL" if required else "") for name, kind, required in BLASTP_HITS_SCHEMA)
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE hits (" + columns + ")")
    return db


def source(root, route, corrupt=None):
    relative, channel, subject_db = ROUTES[route]
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=FIELDS)
    writer.writeheader()
    first = dict(strain="SOFTWARE", gene="first_gene", bgc_id="software_identity", hit_rank=1, subject_acc="FIRST", subject_def="first row", channel=channel, subject_db=subject_db)
    writer.writerow(first)
    second = {**first, "gene": "software_café_\ufffd", "hit_rank": 2, "subject_acc": "SECOND", "subject_def": "comma-bearing, Unicode café description"}
    if corrupt:
        second[corrupt] = "software___BAD_BYTE__value"
    writer.writerow(second)
    data = text.getvalue().encode("utf-8").replace(b"__BAD_BYTE__", b"\xff")
    path.write_bytes(data)
    return path, data


def invoke(root, db, execute):
    args = ["--root", str(root), "--db", str(db)]
    if execute:
        args += ["--execute", "--source-workspace", "software-import"]
    return tool.main(args)


@pytest.mark.parametrize("route", list(ROUTES))
@pytest.mark.parametrize("execute", [False, True])
@pytest.mark.parametrize("field", ["strain", "gene", "subject_acc"])
def test_invalid_utf8_skips_whole_named_source(tmp_path, capsys, route, execute, field):
    db = make_store(tmp_path)
    path, original = source(tmp_path, route, corrupt=field)
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    assert invoke(tmp_path, db, execute) == 0
    captured = capsys.readouterr()
    with sqlite3.connect(db) as connection:
        rows = connection.execute("SELECT gene,subject_acc FROM hits").fetchall()
    assert rows == []
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    assert path.read_bytes() == original
    assert "unreadable: 1" in captured.out and "rows to add: 0" in captured.out
    assert path.name in captured.err and "utf-8" in captured.err
    assert "no-hit" not in (captured.out + captured.err).lower()


@pytest.mark.parametrize("route", list(ROUTES))
def test_valid_unicode_and_channel_provenance_remain_exact(tmp_path, capsys, route):
    db = make_store(tmp_path)
    path, original = source(tmp_path, route)
    assert invoke(tmp_path, db, True) == 0
    assert capsys.readouterr().err == ""
    with sqlite3.connect(db) as connection:
        rows = connection.execute("SELECT gene,subject_def,workspace,channel,subject_db,source_file FROM hits ORDER BY hit_rank").fetchall()
    expected_channel = "ncbi_nr" if route == "nr" else "ncbi_clustered_nr"
    expected_db = "nr" if route == "nr" else "nr_cluster_seq"
    assert rows[1] == ("software_café_\ufffd", "comma-bearing, Unicode café description", "software-import", expected_channel, expected_db, os.path.relpath(path, tmp_path))
    assert path.read_bytes() == original


def test_mixed_batch_remains_explicit_partial_success(tmp_path, capsys):
    db = make_store(tmp_path)
    bad, bad_data = source(tmp_path, "clustered", corrupt="subject_acc")
    good, good_data = source(tmp_path, "nr")
    assert invoke(tmp_path, db, True) == 0
    captured = capsys.readouterr()
    assert "unreadable: 1" in captured.out and "inserted 2" in captured.out
    assert bad.name in captured.err
    with sqlite3.connect(db) as connection:
        sources = connection.execute("SELECT DISTINCT source_file,channel FROM hits").fetchall()
    assert sources == [(os.path.relpath(good, tmp_path), "ncbi_nr")]
    assert bad.read_bytes() == bad_data and good.read_bytes() == good_data
