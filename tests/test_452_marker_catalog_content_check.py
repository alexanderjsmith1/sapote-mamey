"""gen_marker_catalog --check verifies both generated files, not only the stored hash field.

An edited JSON table that keeps the stored sha256, or a missing or stale Markdown companion,
must fail the check. A fresh render of both files must still pass.
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location(
        "gen_marker_catalog_452", ROOT / "tools" / "gen_marker_catalog.py"
    )
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    monkeypatch.setattr(gen, "JSON_OUT", tmp_path / "MARKER_CATALOG.generated.json")
    monkeypatch.setattr(gen, "MD_OUT", tmp_path / "MARKER_CATALOG.generated.md")
    gen.write(gen.collect())
    monkeypatch.setattr(gen.sys, "argv", ["gen_marker_catalog.py", "--check"])
    return gen


def test_fresh_pair_passes(monkeypatch, tmp_path):
    gen = _load(monkeypatch, tmp_path)
    assert gen.main() == 0


def test_changed_table_with_unchanged_hash_fails(monkeypatch, tmp_path):
    gen = _load(monkeypatch, tmp_path)
    payload = json.loads(gen.JSON_OUT.read_text(encoding="utf-8"))
    table = next(iter(payload["tables"]))
    family = next(iter(payload["tables"][table]))
    payload["tables"][table][family] = ["edited_pattern"]
    gen.JSON_OUT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    assert json.loads(gen.JSON_OUT.read_text())["sha256"] == gen.collect()["sha256"]
    assert gen.main() == 1


def test_absent_markdown_fails(monkeypatch, tmp_path):
    gen = _load(monkeypatch, tmp_path)
    gen.MD_OUT.unlink()
    assert gen.main() == 1


def test_stale_markdown_fails(monkeypatch, tmp_path):
    gen = _load(monkeypatch, tmp_path)
    gen.MD_OUT.write_text(gen.MD_OUT.read_text(encoding="utf-8") + "\nhand edit\n", encoding="utf-8")
    assert gen.main() == 1
