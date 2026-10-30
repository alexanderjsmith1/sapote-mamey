"""Retain supplied software hit rows; never open an operator store or run BLAST."""
import csv
import importlib.util
from pathlib import Path
import sqlite3


SPEC = importlib.util.spec_from_file_location("swissprot_fixture_helpers_461",
    Path(__file__).with_name("test_blastp_store_importers.py"))
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)


def test_all_ten_source_ranks_survive_idempotent_import(tmp_path):
    db = fixture._make_store(tmp_path)
    source = fixture._swiss_csv(tmp_path)
    fixture._expand_hit_ranks(source)
    for _ in range(2):
        result = fixture._run(fixture.SWISSPROT, tmp_path, "--execute", "--source-workspace", "software-import")
        assert result.returncode == 0, result.stderr
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT hit_rank FROM hits ORDER BY hit_rank").fetchall() == [(rank,) for rank in range(1, 11)]


def test_seen_source_can_add_missing_ranks_without_replacing_prior_rows(tmp_path):
    db = fixture._make_store(tmp_path)
    source = fixture._swiss_csv(tmp_path)
    first = fixture._run(fixture.SWISSPROT, tmp_path, "--execute", "--source-workspace", "original-import")
    assert first.returncode == 0, first.stderr
    fixture._expand_hit_ranks(source)
    before = fixture._sha(db)
    dry = fixture._run(fixture.SWISSPROT, tmp_path)
    assert dry.returncode == 0, dry.stderr
    assert "rows to add: 9" in dry.stdout
    assert fixture._sha(db) == before
    retry = fixture._run(fixture.SWISSPROT, tmp_path, "--execute", "--source-workspace", "recovery-import")
    assert retry.returncode == 0, retry.stderr
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM hits").fetchone()[0] == 10
        assert connection.execute("SELECT workspace FROM hits WHERE hit_rank=1").fetchone()[0] == "original-import"


def test_same_rank_different_subjects_are_retained_and_exact_duplicates_collapse(tmp_path):
    db = fixture._make_store(tmp_path)
    source = fixture._swiss_csv(tmp_path)
    with source.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields, first = reader.fieldnames, next(reader)
    with source.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writerow({**first, "subject_acc": "SOFTWARE_OTHER_SUBJECT"})
        writer.writerow(first)
    result = fixture._run(fixture.SWISSPROT, tmp_path, "--execute", "--source-workspace", "software-import")
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM hits").fetchone()[0] == 2
