"""Tiny source-pinned catalog regressions: scan scope and exact output locators."""
import csv
import importlib.util
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_owner(filename, name):
    path = ROOT / "tools" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert Path(module.__file__).resolve() == path.resolve()
    return module


@pytest.fixture
def owners(monkeypatch):
    # Do not use an installed module or another checkout's cached catalog helper.
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    inventory = _load_owner("gen_tools_inventory.py", "catalog_scope_inventory_owner")
    monkeypatch.setitem(sys.modules, "gen_tools_inventory", inventory)
    atlas = _load_owner("file_atlas.py", "catalog_scope_atlas_owner")
    maintenance = _load_owner("_maintenance_inventory.py", "catalog_scope_maintenance_owner")
    return atlas, inventory, maintenance


def _write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def tree(tmp_path, monkeypatch, owners):
    root = tmp_path / "bundle"
    _write(root, "tools/alpha.py", '"""Fabricated catalog purpose."""\n')
    _write(root, "mamey/beta.py", '"""Fabricated engine purpose."""\n')
    monkeypatch.setattr(owners[0], "ROOT", root)
    return root


def test_ancestor_named_data_preserves_bundle_membership(tmp_path, monkeypatch, owners):
    root = tmp_path / "data" / "bundle"
    for name in ("tools/alpha.py", "mamey/beta.py", "tools/data/ignored.py", "mamey/_vendor/ignored.py"):
        _write(root, name, '"""Fabricated source."""\n')
    atlas = owners[0]
    monkeypatch.setattr(atlas, "ROOT", root)
    assert {p.relative_to(root).as_posix() for p in atlas._py_files()} == {"tools/alpha.py", "mamey/beta.py"}
    assert {row["path"] for row in atlas.build()} == {"tools/alpha.py", "mamey/beta.py"}


@pytest.mark.parametrize("directory", [".pytest_cache", ".scratch", "__pycache__"])
def test_cache_python_files_do_not_change_atlas_rows(tree, owners, directory):
    atlas = owners[0]
    before = atlas.build()
    _write(tree, f"tools/{directory}/volatile.py", '"""Volatile artifact naming alpha."""\n')
    _write(tree, f"mamey/{directory}/volatile.py", '"""Volatile artifact naming beta."""\n')
    assert atlas.build() == before


@pytest.mark.parametrize("directory", [".pytest_cache", ".scratch", "__pycache__"])
def test_cache_test_references_do_not_change_atlas_rows(tree, owners, directory):
    atlas = owners[0]
    before = atlas.build()
    _write(tree, f"tests/{directory}/test_volatile.py", "alpha beta\n")
    assert atlas.build() == before


@pytest.mark.parametrize("directory", [".pytest_cache", ".scratch", "__pycache__"])
def test_cache_shell_and_gate_references_do_not_change_atlas_rows(tree, owners, directory):
    atlas = owners[0]
    before = atlas.build()
    _write(tree, f"{directory}/volatile.sh", "python tools/alpha.py\n")
    _write(tree, f"{directory}/gate_registry.tsv", "beta\n")
    assert atlas.build() == before


def test_visible_nested_test_shell_and_gate_references_remain_counted(tree, owners):
    _write(tree, "tests/nested/test_visible.py", "alpha\n")
    _write(tree, "ops/run.sh", "python tools/alpha.py\n")
    _write(tree, "ops/gate_registry.tsv", "alpha\n")
    row = next(row for row in owners[0].build() if row["path"] == "tools/alpha.py")
    assert row["n_tests"] == 1
    assert row["test_refs"] == "test_visible.py"
    assert row["shell_refs"] == "gate_registry.tsv;run.sh"
    assert row["orphan"] is False


@pytest.mark.parametrize("locator, table_code, list_code", [
    ("nested/pipe|name.py", "`tools/nested/pipe\\|name.py`", "`tools/nested/pipe|name.py`"),
    ("nested/odd|`name.py", "`` tools/nested/odd\\|`name.py ``", "`` tools/nested/odd|`name.py ``"),
    ("nested/two``ticks|.sh", "``` tools/nested/two``ticks\\|.sh ```", "``` tools/nested/two``ticks|.sh ```"),
])
def test_catalog_locator_code_spans_preserve_exact_paths(owners, locator, table_code, list_code):
    inventory = owners[1]
    rows = [(locator, "Fabricated source purpose.")]
    assert f"| {table_code} | Fabricated source purpose. |" in inventory.render_md(rows).splitlines()
    assert f"- {list_code} — Fabricated source purpose." in inventory.render_manifest_block(rows).splitlines()


def test_atlas_markdown_quotes_locator_but_csv_preserves_raw_path(tree, owners):
    _write(tree, "tools/nested/odd|`name.py", '"""Fabricated locator purpose."""\n')
    csv_path = tree / "atlas.csv"
    md_path = tree / "atlas.md"
    assert owners[0].main(["--out", str(csv_path), "--md", str(md_path)]) == 0
    with csv_path.open(newline="", encoding="utf-8") as stream:
        paths = {row["path"] for row in csv.DictReader(stream)}
    assert paths == {"tools/alpha.py", "mamey/beta.py", "tools/nested/odd|`name.py"}
    code = "`` tools/nested/odd\\|`name.py ``"
    locator_rows = [line for line in md_path.read_text(encoding="utf-8").splitlines() if "odd" in line]
    assert locator_rows and all(line.startswith(f"| {code} |") for line in locator_rows)


@pytest.mark.parametrize("document, expected", [
    ("docs/Name #?.md", "Name%20%23%3F.md"),
    ("wiki/nested/Name #?.md", "../wiki/nested/Name%20%23%3F.md"),
    ("README.md", "../README.md"),
])
def test_maintenance_links_encode_path_characters_without_url_semantics(owners, document, expected):
    actual = owners[2]._link(document)
    assert actual == expected
    parsed = urlsplit(actual)
    assert parsed.query == parsed.fragment == ""
    assert unquote(parsed.path) == unquote(expected)
