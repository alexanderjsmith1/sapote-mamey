"""Default tools inventory requires its maintained capabilities member before writing."""
import importlib.util
import pathlib
import sys
import types

import pytest


@pytest.fixture
def inventory(tmp_path, monkeypatch):
    source = pathlib.Path(__file__).resolve().parents[1] / "tools/gen_tools_inventory.py"
    spec = importlib.util.spec_from_file_location("inventory_pair_under_test", source)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    root = tmp_path / "bundle with spaces"
    tools = root / "tools"
    tools.mkdir(parents=True)
    (tools / "alpha.py").write_text('"""Synthetic inventory alpha."""\nVALUE = 1\n', encoding="utf-8")
    monkeypatch.setattr(gen, "ROOT", root)
    monkeypatch.setattr(gen, "TOOLS", tools)
    monkeypatch.setattr(gen, "MD_OUT", root / "docs/TOOLS_INVENTORY.generated.md")
    monkeypatch.setattr(gen, "MANIFEST", root / "docs/BUNDLE_CAPABILITIES.md")
    return gen


def snapshot(root):
    return {str(p.relative_to(root)): ("directory" if p.is_dir() else p.read_bytes())
            for p in root.rglob("*")}


def seed_pair(gen):
    gen.MD_OUT.parent.mkdir()
    gen.MD_OUT.write_text(gen.render_md(gen.collect()), encoding="utf-8")
    gen.MANIFEST.write_text(
        "Maintained prelude.\n`tools/` (1 scripts, fixture)\n\n"
        + gen.render_manifest_block(gen.collect()) + "\n\nMaintained afterword.\n",
        encoding="utf-8",
    )


def test_check_missing_manifest_is_nonzero_and_readonly(inventory, capsys):
    gen = inventory
    gen.MD_OUT.parent.mkdir()
    gen.MD_OUT.write_text(gen.render_md(gen.collect()), encoding="utf-8")
    before = snapshot(gen.ROOT)
    code = gen.main(["--check"])
    assert snapshot(gen.ROOT) == before
    assert code == 1
    assert "BUNDLE_CAPABILITIES.md" in capsys.readouterr().out


def test_check_both_missing_reports_both(inventory, capsys):
    gen = inventory
    before = snapshot(gen.ROOT)
    code = gen.main(["--check"])
    output = capsys.readouterr().out
    assert snapshot(gen.ROOT) == before
    assert code == 1
    assert "TOOLS_INVENTORY.generated.md" in output
    assert "BUNDLE_CAPABILITIES.md" in output


def test_write_missing_manifest_preserves_inventory(inventory, capsys):
    gen = inventory
    gen.MD_OUT.parent.mkdir()
    gen.MD_OUT.write_text("Previously reviewed inventory.\n", encoding="utf-8")
    before = snapshot(gen.ROOT)
    code = gen.main([])
    assert snapshot(gen.ROOT) == before
    assert code == 1
    assert "BUNDLE_CAPABILITIES.md" in capsys.readouterr().out


def test_write_missing_manifest_preserves_absent_output_directory(inventory):
    gen = inventory
    before = snapshot(gen.ROOT)
    code = gen.main([])
    assert snapshot(gen.ROOT) == before
    assert not gen.MD_OUT.parent.exists()
    assert code == 1


def test_valid_pair_roundtrip_preserves_maintained_prose(inventory):
    gen = inventory
    seed_pair(gen)
    gen.MD_OUT.write_text("Old inventory.\n", encoding="utf-8")
    text = gen.MANIFEST.read_text(encoding="utf-8").replace("(1 scripts", "(999 scripts")
    gen.MANIFEST.write_text(text, encoding="utf-8")
    assert gen.main([]) == 0
    assert gen.main(["--check"]) == 0
    after = gen.MANIFEST.read_text(encoding="utf-8")
    assert after.startswith("Maintained prelude.\n`tools/` (1 scripts, fixture)\n")
    assert after.endswith("\n\nMaintained afterword.\n")
    before = snapshot(gen.ROOT)
    assert gen.main(["--check"]) == 0
    assert snapshot(gen.ROOT) == before


def test_marker_free_existing_prose_is_retained_and_appended(inventory):
    gen = inventory
    gen.MANIFEST.parent.mkdir()
    prose = "Maintained capabilities without a generated block.\n"
    gen.MANIFEST.write_text(prose, encoding="utf-8")
    assert gen.main([]) == 0
    assert gen.main(["--check"]) == 0
    text = gen.MANIFEST.read_text(encoding="utf-8")
    assert text.startswith(prose)
    assert text.count(gen.START) == text.count(gen.END) == 1
    assert gen.render_manifest_block(gen.collect()) in text


@pytest.mark.parametrize("args", [["--connections"], ["--search", "synthetic"]])
def test_independent_read_modes_do_not_require_the_pair(inventory, args):
    gen = inventory
    before = snapshot(gen.ROOT)
    assert gen.main(args) == 0
    assert snapshot(gen.ROOT) == before
    assert not gen.MANIFEST.exists()


def test_maintenance_dispatch_does_not_enter_default_pair_preflight(inventory, monkeypatch, capsys):
    gen = inventory
    calls = []
    maintenance = types.ModuleType("_maintenance_inventory")
    def maintain(root, commands, paths, registry, **kwargs):
        calls.append((root, commands, paths, registry, kwargs["check"]))
        return "maintenance dispatch control\n", 0
    maintenance.maintain = maintain
    catalog = types.ModuleType("gen_command_catalog")
    def command_records():
        return ["command fixture"]
    catalog.command_records = command_records
    companion = types.ModuleType("mamey.companion_tools")
    def load_registry():
        return ["registry fixture"]
    companion.load_registry = load_registry
    monkeypatch.setitem(sys.modules, "_maintenance_inventory", maintenance)
    monkeypatch.setitem(sys.modules, "gen_command_catalog", catalog)
    monkeypatch.setitem(sys.modules, "mamey.companion_tools", companion)
    before = snapshot(gen.ROOT)
    assert gen.main(["--maintenance", "--check"]) == 0
    assert snapshot(gen.ROOT) == before
    assert calls == [(gen.ROOT, ["command fixture"], ["tools/alpha.py"], ["registry fixture"], True)]
    assert capsys.readouterr().out == "maintenance dispatch control\n"


@pytest.mark.parametrize("surface", ["inventory", "block", "count"])
def test_stale_pair_is_readonly_until_normal_regeneration(inventory, surface):
    gen = inventory
    seed_pair(gen)
    if surface == "inventory":
        gen.MD_OUT.write_text("Stale inventory.\n", encoding="utf-8")
    else:
        text = gen.MANIFEST.read_text(encoding="utf-8")
        text = text.replace("Synthetic inventory alpha.", "Stale description.") if surface == "block" else text.replace("(1 scripts", "(99 scripts")
        gen.MANIFEST.write_text(text, encoding="utf-8")
    before = snapshot(gen.ROOT)
    assert gen.main(["--check"]) == 1
    assert snapshot(gen.ROOT) == before
    assert gen.main([]) == 0
    assert gen.main(["--check"]) == 0


@pytest.mark.parametrize("args", [["--check"], []], ids=["check", "write"])
def test_unreadable_manifest_preserves_all_outputs(inventory, monkeypatch, args, capsys):
    gen = inventory
    seed_pair(gen)
    before = snapshot(gen.ROOT)
    original = pathlib.Path.read_text
    def refuse_manifest(path, *a, **kw):
        if path == gen.MANIFEST:
            raise PermissionError("synthetic capabilities permission failure")
        return original(path, *a, **kw)
    monkeypatch.setattr(pathlib.Path, "read_text", refuse_manifest)
    code = gen.main(args)
    assert snapshot(gen.ROOT) == before
    assert code == 1
    assert "BUNDLE_CAPABILITIES.md" in capsys.readouterr().out


@pytest.mark.parametrize("args", [["--check"], []], ids=["check", "write"])
def test_invalid_utf8_manifest_preserves_all_outputs(inventory, args, capsys):
    gen = inventory
    seed_pair(gen)
    gen.MANIFEST.write_bytes(b"\xffInvalid UTF-8 capabilities\n")
    before = snapshot(gen.ROOT)
    code = gen.main(args)
    assert snapshot(gen.ROOT) == before
    assert code == 1
    assert "BUNDLE_CAPABILITIES.md" in capsys.readouterr().out
