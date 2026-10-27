"""The BiG-SCAPE family readers open the database read-only and never create one.

bigscape_family_verdicts, bigscape_family_figures and bigscape_clinker_html used plain
sqlite3.connect(), so a mistyped --db path created an empty database and failed later.
"""
import ast
import importlib.util
import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
TOOLS = ("bigscape_family_verdicts", "bigscape_family_figures", "bigscape_clinker_html")


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_458ro", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("name", TOOLS)
def test_missing_db_is_refused_and_not_created(name, tmp_path):
    db = tmp_path / "typo.db"
    with pytest.raises(FileNotFoundError):
        _load(name)._open_db_ro(str(db))
    assert not db.exists()


@pytest.mark.parametrize("name", TOOLS)
def test_existing_db_opens_read_only(name, tmp_path):
    db = tmp_path / "bs.db"
    sqlite3.connect(db).close()
    con = _load(name)._open_db_ro(str(db))
    with pytest.raises(sqlite3.OperationalError):
        con.execute("create table t(x)")
    con.close()


@pytest.mark.parametrize("name", TOOLS)
def test_no_plain_connect_left(name):
    tree = ast.parse((ROOT / "tools" / f"{name}.py").read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "connect"
             and isinstance(node.func.value, ast.Name) and node.func.value.id == "sqlite3"]
    assert calls
    assert all(any(keyword.arg == "uri" and isinstance(keyword.value, ast.Constant)
                   and keyword.value.value is True for keyword in call.keywords)
               for call in calls)
