"""Maintenance owner contracts: complete rosters, explicit holds and stable output pairs."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inventory = load("_maintenance_inventory")
catalog = load("gen_command_catalog")


def write(root, name, text="maintained fixture\n"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def tree(tmp_path):
    for name in ["mamey/cli.py", "tools/gen_tools_inventory.py", "tools/_maintenance_inventory.py",
                 "tools/gen_command_catalog.py", "mamey/companion_tools.py", "mamey/data/companion_tools.json",
                 "tools/alpha.py", "docs/current.md", "docs/current_v1.md", "docs/unclassified_v1.md",
                 "docs/history/old.md", "docs/history/unknown.md", "wiki/Mirror.md"]:
        write(tmp_path, name)
    write(tmp_path, "CURRENT_DOCS_INDEX.md", "[current](docs/current.md) [old current](docs/current_v1.md) "
          "[history](docs/history/old.md) [mirror](wiki/Mirror.md) [web](https://example.invalid/docs/unclassified_v1.md)\n")
    write(tmp_path, "tools/generated_surface_ownership.py", "SURFACES = {}\n")
    write(tmp_path, "tools/sync_wiki_mirrors.py", "MIRRORS = {'wiki/Mirror.md': 'docs/current.md'}\n")
    policy = {"schema": "sapote-mamey.maintenance-policy.v1", "retained_history": [],
              "history_prefixes": ["docs/history/"], "engineering_prefixes": [], "optional_documents": [],
              "optional_commands": {}, "optional_hooks": [], "generated_surfaces": [
                  {"id": "maintenance", "outputs": list(inventory.OUTPUTS),
                   "owner_paths": ["tools/gen_tools_inventory.py", inventory.POLICY],
                   "regeneration_rule": "python tools/gen_tools_inventory.py --maintenance",
                   "check_rule": "python tools/gen_tools_inventory.py --maintenance --check",
                   "trigger": "roster or owner input changes", "scope": "complete"}]}
    write(tmp_path, inventory.POLICY, json.dumps(policy))
    return tmp_path


def build(root, **kwargs):
    return inventory.build_inventory(root, kwargs.get("commands", []), kwargs.get("tools", ["tools/alpha.py"]),
                                     kwargs.get("companions", []))


def records(payload, kind):
    return {row["id"].removeprefix(kind + ":"): row for row in payload["records"] if row["kind"] == kind}


def hashes(root):
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_lifecycle_keeps_history_and_does_not_retire_old_version_names(tree):
    docs = records(build(tree), "document")
    assert docs["docs/history/old.md"]["linked_from_current_index"] is True
    assert docs["docs/history/old.md"]["lifecycle"] == "RETAINED_HISTORY"
    assert docs["docs/history/unknown.md"]["lifecycle"] == "RETAINED_HISTORY"
    assert docs["docs/current_v1.md"]["lifecycle"] == "CURRENT_NAVIGATION_DECLARED"
    assert docs["docs/unclassified_v1.md"]["lifecycle"] == "UNCLASSIFIED_REVIEW_HOLD"
    assert docs["wiki/Mirror.md"]["lifecycle"] == "GENERATED_OR_MANAGED_SURFACE"


def test_complete_scoped_roster_has_owners_without_importing_discovered_tools(tree):
    write(tree, "tools/alpha.py", "raise RuntimeError('must never import a discovered source')\n")
    write(tree, "outside/ignored.md")
    write(tree, "docs/new.md")
    companion = SimpleNamespace(id="external", name="External", requirement="on-request")
    payload = build(tree, companions=[companion])
    docs = records(payload, "document")
    assert "docs/new.md" in docs and "outside/ignored.md" not in docs
    assert len(docs) == len(list(tree.glob("*.md"))) + len(list((tree / "docs").rglob("*.md"))) + len(list((tree / "wiki").rglob("*.md"))) + 1
    assert records(payload, "companion")["external"]["availability"] == "NOT_PROBED"
    assert records(payload, "companion")["external"]["requirement"] == "on-request"
    assert records(payload, "tool")["tools/alpha.py"]["lifecycle"] == "SOURCE_DISCOVERED_REVIEW_HOLD"
    assert all(row["owner_paths"] and row["regeneration_rule"] for row in payload["records"])


def test_pair_generation_is_a_fixed_point_and_check_detects_either_stale_member(tree):
    call = lambda check: inventory.maintain(tree, [], ["tools/alpha.py"], [], check=check,
        write_text=lambda path, text: path.write_text(text, encoding="utf-8"))
    before = hashes(tree)
    assert call(True)[1] == 1
    assert hashes(tree) == before
    assert call(False)[1] == 0
    first = hashes(tree)
    assert call(True)[1] == 0
    assert call(False)[1] == 0
    assert hashes(tree) == first
    for name in inventory.OUTPUTS:
        original = (tree / name).read_text(encoding="utf-8")
        write(tree, name, original + "stale sentinel\n")
        changed = hashes(tree)
        message, code = call(True)
        assert code == 1 and name in message
        assert hashes(tree) == changed
        write(tree, name, original)


def test_generated_outputs_are_not_hashed_into_their_own_input_graph(tree):
    payload = build(tree)
    write(tree, inventory.JSON_OUT, "arbitrary old output")
    write(tree, inventory.MD_OUT, "arbitrary old navigation")
    assert build(tree) == payload
    assert not set(inventory.OUTPUTS) & {row["path"] for row in payload["inputs"]}
    assert "source" not in records(payload, "document")[inventory.MD_OUT]
    write(tree, "docs/current.md", "changed maintained prose")
    assert build(tree) != payload


def test_metadata_modes_are_checked_read_only_and_repaired_by_generation(tree):
    if os.name != "posix":
        pytest.skip("POSIX metadata permission contract; Windows ACLs are outside this check")
    call = lambda check: inventory.maintain(tree, [], ["tools/alpha.py"], [], check=check,
        write_text=lambda path, text: path.write_text(text, encoding="utf-8"))
    assert call(False)[1] == 0
    for name in inventory.OUTPUTS:
        assert (tree / name).stat().st_mode & 0o777 == 0o644
        (tree / name).chmod(0o600)
    before = hashes(tree)
    assert call(True)[1] == 1
    assert hashes(tree) == before
    assert all((tree / name).stat().st_mode & 0o777 == 0o600 for name in inventory.OUTPUTS)
    assert call(False)[1] == 0
    assert all((tree / name).stat().st_mode & 0o777 == 0o644 for name in inventory.OUTPUTS)
    assert call(True)[1] == 0


@pytest.mark.parametrize("name", ["../escape.md", "/tmp/escape.md", "docs/../escape.md", "docs//escape.md", "docs\\escape.md"])
def test_unsafe_paths_refuse(name, tree):
    with pytest.raises(ValueError, match="unsafe maintenance path"):
        inventory.checked_path(tree, name, missing=True)


def test_symlinks_refuse_without_reading_the_target(tree):
    (tree / "docs/link.md").symlink_to(tree / "docs/current.md")
    with pytest.raises(ValueError, match="symlink"):
        build(tree)


def test_missing_owner_and_duplicate_tool_or_generated_claims_refuse_without_writes(tree):
    before = hashes(tree)
    with pytest.raises(ValueError, match="duplicate discovered"):
        build(tree, tools=["tools/alpha.py", "tools/alpha.py"])
    assert hashes(tree) == before
    policy = json.loads((tree / inventory.POLICY).read_text())
    policy["generated_surfaces"].append(dict(policy["generated_surfaces"][0], id="conflict"))
    write(tree, inventory.POLICY, json.dumps(policy))
    with pytest.raises(ValueError, match="conflicting generated owners"):
        build(tree)
    policy["generated_surfaces"] = [dict(policy["generated_surfaces"][0], owner_paths=["tools/missing.py"])]
    write(tree, inventory.POLICY, json.dumps(policy))
    with pytest.raises(ValueError, match="missing maintenance input"):
        build(tree)


def test_literal_owner_declarations_are_read_without_executing_the_owner(tree):
    write(tree, "tools/generated_surface_ownership.py", "raise RuntimeError('no execution')\nSURFACES = {}\n")
    assert build(tree)["counts"]["generated"] == 2
    write(tree, "tools/generated_surface_ownership.py", "SURFACES = make_surfaces()\n")
    with pytest.raises(ValueError):
        build(tree)


def test_catalog_has_no_optional_addon_rows():
    # v9.7.450 removed the only optional add-on (Lab Quest). The catalog lists parser commands only.
    assert catalog.ADDON_COMMANDS == {}
    records = catalog.command_records({"workflow": {"help": "status", "aliases": ["wf"]}})
    assert [r["name"] for r in records] == ["workflow"]
    assert all(r["requirement"] == "parser-declared" for r in records)


@pytest.mark.parametrize("extra", [["--connections"], ["--search", "audit"], ["--output", "ignored.json"],
                                   ["--format", "tsv"], ["--top", "2"], ["--root", "/tmp"]])
def test_maintenance_cli_refuses_mixed_modes_before_writing(extra):
    gen = load("gen_tools_inventory")
    with pytest.raises(SystemExit) as exc:
        gen.main(["--maintenance", *extra])
    assert exc.value.code == 2


def _source_bindings(root, names):
    return {name: {"sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
                   "bytes": (root / name).stat().st_size,
                   "mode": stat.S_IMODE((root / name).stat().st_mode)} for name in sorted(names)}


def _full_rosters(root):
    documents = {p.relative_to(root).as_posix() for p in root.glob("*.md")}
    for directory in ("docs", "wiki"):
        documents.update(p.relative_to(root).as_posix() for p in (root / directory).rglob("*.md"))
    tools = {p.relative_to(root).as_posix() for p in (root / "tools").rglob("*")
             if p.is_file() and p.suffix in {".py", ".sh"}
             and not any(part.startswith(".") or part == "__pycache__"
                         for part in p.relative_to(root / "tools").parts)}
    if (root / "bootstrap.sh").exists():
        tools.add("bootstrap.sh")
    return documents, tools


@pytest.fixture
def full_owner_source(tmp_path):
    """Complete actual owner scope, with code/config only and no research payloads."""
    source = tmp_path / "maintenance-owner-source"
    documents, tools = _full_rosters(ROOT)
    policy = json.loads((ROOT / inventory.POLICY).read_text(encoding="utf-8"))
    surfaces = inventory.literal_assignment(ROOT, "tools/generated_surface_ownership.py", "SURFACES")
    mirrors = inventory.literal_assignment(ROOT, "tools/sync_wiki_mirrors.py", "MIRRORS")
    names = documents | tools | {
        p.relative_to(ROOT).as_posix() for p in (ROOT / "mamey").rglob("*.py")
        if "__pycache__" not in p.parts
    }
    names.update({inventory.POLICY, "mamey/data/companion_tools.json",
                  "mamey/data/deliverables_registry.json", "pyproject.toml", "bootstrap_contract.yml"})
    for surface in (*surfaces.values(), *policy["generated_surfaces"]):
        names.update(surface["owner_paths"])
        names.update(surface["outputs"])
    for declaration in policy["optional_commands"].values():
        names.update(declaration["owner_paths"])
    names.update(policy["optional_hooks"])
    names.update(policy["optional_documents"])
    names.update(policy["retained_history"])
    names.update(mirrors)
    names.update(mirrors.values())
    # Paths are all declared source/configuration/metadata. No sequence, archive,
    # database, optional executable or candidate run/output directory is cloned.
    forbidden = {".zip", ".tar", ".gz", ".faa", ".fna", ".fa", ".fasta", ".gbk", ".hmm", ".dmnd"}
    for name in names:
        original = inventory.checked_path(ROOT, name)
        assert original.suffix not in forbidden, name
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
    before = _source_bindings(ROOT, names)
    assert _source_bindings(source, names) == before
    assert _full_rosters(source) == (documents, tools), "copy must not narrow actual scope"
    controls = tmp_path / "maintenance-owner-controls"
    controls.mkdir()
    (controls / "copy-provenance.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
    yield source, controls, documents, tools
    assert _source_bindings(ROOT, names) == before, "candidate inputs/generated surfaces must stay unchanged"


def _owner_process(source, controls, *arguments, describe=False):
    """Fresh process pins parser/registry/owner imports to this disposable source."""
    program = r'''
import json, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(root), str(root / "tools")]
import mamey, mamey.cli, mamey.companion_tools
import gen_tools_inventory as gen
import gen_command_catalog as catalog
import _maintenance_inventory as inventory
modules = (mamey, mamey.cli, mamey.companion_tools, gen, catalog, inventory)
assert all(Path(m.__file__).resolve().is_relative_to(root) for m in modules), "foreign owner import"
commands = catalog.command_records()
tools = [(Path("tools") / name).as_posix() if not name.startswith("../") else name.removeprefix("../")
         for name, _ in gen.collect()]
companions = mamey.companion_tools.load_registry()
if sys.argv[2] == "describe":
    payload = inventory.build_inventory(root, commands, tools, companions)
    sys.stdout.write(json.dumps({"payload": payload, "commands": commands, "tools": tools,
        "module_origins": {m.__name__: str(Path(m.__file__).relative_to(root)) for m in modules}}))
else:
    raise SystemExit(gen.main(sys.argv[3:]))
'''
    env = dict(os.environ, PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE="1",
               SAPOTE_ROOT=str(controls / "workspace"), SAPOTE_WORKSPACE_ROOT=str(controls / "workspace"),
               MPLCONFIGDIR=str(controls / "matplotlib"))
    command = [sys.executable, "-B", "-c", program, str(source), "describe" if describe else "owner", *arguments]
    result = subprocess.run(command, cwd=source, env=env, text=True, capture_output=True, timeout=60)
    attempt = len(list(controls.glob("owner-*.json")))
    log = controls / f"owner-{attempt}.log"
    log.write_text(result.stdout + result.stderr, encoding="utf-8")
    (controls / f"owner-{attempt}.json").write_text(json.dumps({
        "arguments": list(arguments), "describe": describe, "exit_code": result.returncode,
        "python_invocation": sys.executable,
        "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        "owner_sha256": hashlib.sha256((source / "tools/gen_tools_inventory.py").read_bytes()).hexdigest(),
    }, indent=2), encoding="utf-8")
    return result


def test_owner_generated_full_scope_inventory_is_current_and_complete(full_owner_source):
    source, controls, documents, tools = full_owner_source
    generated = _owner_process(source, controls, "--maintenance")
    assert generated.returncode == 0, generated.stdout + generated.stderr
    checked = _owner_process(source, controls, "--maintenance", "--check")
    assert checked.returncode == 0, checked.stdout + checked.stderr
    described = _owner_process(source, controls, describe=True)
    assert described.returncode == 0, described.stdout + described.stderr
    actual = json.loads(described.stdout)
    payload = json.loads((source / inventory.JSON_OUT).read_text(encoding="utf-8"))
    assert payload == actual["payload"]
    assert set(records(payload, "command")) == {row["name"] for row in actual["commands"]}
    assert set(records(payload, "tool")) == set(actual["tools"]) == tools
    assert set(records(payload, "document")) == documents
    raw_registry = json.loads((source / "mamey/data/companion_tools.json").read_text(encoding="utf-8"))["tools"]
    declared_ids = {row["id"] for row in raw_registry}
    assert len(declared_ids) == len(raw_registry), "canonical registry identities must be unique"
    assert set(records(payload, "companion")) == declared_ids
    assert payload["counts"]["companion"] == len(declared_ids)
    assert payload["counts"]["optional-hook"] == 8
    assert payload["scope"]["availability"] == "NOT_PROBED"
    assert "UNCLASSIFIED_REVIEW_HOLD" in payload["document_lifecycles"]
    assert "SOURCE_CHECKSUMS_SHA256.txt" not in {row["path"] for row in payload["inputs"]}
    assert all(row["owner_paths"] and row["regeneration_rule"] for row in payload["records"])
    for row in payload["inputs"]:
        path = source / row["path"]
        assert row["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert row["bytes"] == path.stat().st_size
    pair = _source_bindings(source, inventory.OUTPUTS)
    assert _owner_process(source, controls, "--maintenance").returncode == 0
    assert _source_bindings(source, inventory.OUTPUTS) == pair
    for name in inventory.OUTPUTS:
        path = source / name
        path.write_bytes(path.read_bytes() + b"\ncorrupt generated member\n")
        before_check = _source_bindings(source, {p.relative_to(source).as_posix()
            for p in source.rglob("*") if p.is_file()})
        refused = _owner_process(source, controls, "--maintenance", "--check")
        assert refused.returncode == 1 and name in refused.stdout, refused.stdout + refused.stderr
        assert _source_bindings(source, before_check) == before_check, "check must never repair"
        assert _owner_process(source, controls, "--maintenance").returncode == 0
        assert _owner_process(source, controls, "--maintenance", "--check").returncode == 0
        assert _source_bindings(source, inventory.OUTPUTS) == pair
    maintained = source / "docs/CATALOG_MAINTENANCE.md"
    original = maintained.read_bytes()
    maintained.write_bytes(original + b"\nmaintained input drift\n")
    before_check = _source_bindings(source, {p.relative_to(source).as_posix()
        for p in source.rglob("*") if p.is_file()})
    refused = _owner_process(source, controls, "--maintenance", "--check")
    assert refused.returncode == 1, refused.stdout + refused.stderr
    assert _source_bindings(source, before_check) == before_check
    maintained.write_bytes(original)
    assert _owner_process(source, controls, "--maintenance").returncode == 0
    assert _owner_process(source, controls, "--maintenance", "--check").returncode == 0
    assert _source_bindings(source, inventory.OUTPUTS) == pair


def test_release_preparation_declares_both_maintenance_outputs():
    workflow = load("release_workflow")
    assert set(inventory.OUTPUTS) <= set(workflow.preparation_outputs(ROOT))
    shell = (ROOT / "tools/release_cut.sh").read_text()
    assert "python3 tools/gen_tools_inventory.py --maintenance >/dev/null" in shell
    assert "python3 tools/gen_tools_inventory.py --maintenance --check >/dev/null" in shell
