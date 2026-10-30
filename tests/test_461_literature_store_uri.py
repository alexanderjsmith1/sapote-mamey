"""Exact SQLite filename/read-only controls. Never generate a literature atlas."""
from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "tools/refresh_literature_atlas.py"
SPEC = importlib.util.spec_from_file_location("literature_store_uri_461", SOURCE)
atlas = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(atlas)


def make_store(path, marker):
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE metadata(key TEXT,value TEXT)")
        for name in ("current_locus", "owner_record", "locus_binding", "document"):
            connection.execute(f"CREATE TABLE {name}(software_marker TEXT)")
        connection.execute("INSERT INTO metadata VALUES ('marker',?)", (marker,))


@pytest.mark.parametrize("suffix", ["#literal", "?literal"])
def test_special_filename_opens_the_exact_supplied_store(tmp_path, suffix):
    decoy = tmp_path / "evidence.sqlite"
    supplied = tmp_path / ("evidence.sqlite" + suffix)
    make_store(decoy, "decoy")
    make_store(supplied, "supplied")
    with closing(atlas.open_store(supplied)) as connection:
        assert connection.execute("SELECT value FROM metadata WHERE key='marker'").fetchone()[0] == "supplied"


@pytest.mark.parametrize("suffix", ["#literal", "?literal"])
def test_special_filename_remains_read_only(tmp_path, suffix):
    decoy = tmp_path / "evidence.sqlite"
    supplied = tmp_path / ("evidence.sqlite" + suffix)
    make_store(decoy, "decoy")
    make_store(supplied, "supplied")
    with closing(atlas.open_store(supplied)) as connection:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("INSERT INTO metadata VALUES ('attempt','software fixture')")


def test_ordinary_store_remains_exact_and_read_only(tmp_path):
    supplied = tmp_path / "ordinary.sqlite"
    make_store(supplied, "supplied")
    with closing(atlas.open_store(supplied)) as connection:
        assert connection.execute("SELECT value FROM metadata WHERE key='marker'").fetchone()[0] == "supplied"
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("INSERT INTO metadata VALUES ('attempt','software fixture')")
