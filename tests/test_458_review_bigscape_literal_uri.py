"""SQLite reader URIs must preserve literal punctuation and stay read-only."""
import importlib.util
from pathlib import Path
import sqlite3

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ["bigscape_family_verdicts", "bigscape_family_figures", "bigscape_clinker_html"]


def load(name):
    spec = importlib.util.spec_from_file_location("literal_uri_" + name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def database(path):
    with sqlite3.connect(path) as connection:
        connection.executescript("CREATE TABLE family(id,cutoff,bin_label,run_id);"
                                 "CREATE TABLE bgc_record(id,gbk_id,product,category);"
                                 "CREATE TABLE bgc_record_family(family_id,record_id);"
                                 "CREATE TABLE gbk(id,path);")


@pytest.mark.parametrize("name", TOOLS)
@pytest.mark.parametrize("filename", ["db#selected.sqlite", "db?selected.sqlite", "db%23selected.sqlite"])
def test_reader_opens_exact_literal_file_read_only(name, filename, tmp_path):
    target = tmp_path / filename
    database(target)
    database(tmp_path / "db")
    connection = load(name)._open_db_ro(str(target))
    try:
        assert Path(connection.execute("PRAGMA database_list").fetchone()[2]) == target.resolve()
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("CREATE TABLE forbidden(value)")
    finally:
        connection.close()


@pytest.mark.parametrize("filename", ["db#selected.sqlite", "db?selected.sqlite", "db%23selected.sqlite"])
def test_cross_strain_reader_opens_exact_literal_file(filename, tmp_path, monkeypatch):
    target = tmp_path / filename
    database(target)
    database(tmp_path / "db")
    module = load("bigscape_cross_strain")
    real_connect = sqlite3.connect
    observed = []

    def trace(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        observed.append(Path(connection.execute("PRAGMA database_list").fetchone()[2]))
        return connection

    monkeypatch.setattr(module.sqlite3, "connect", trace)
    assert module.build_rows(str(target), "1") == []
    assert observed == [target.resolve()]
