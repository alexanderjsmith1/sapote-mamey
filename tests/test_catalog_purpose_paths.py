"""Catalog descriptions quote source purpose; no clipped paths or invented capabilities."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(os.environ.get("CATALOG_TEST_SOURCE_ROOT", Path(__file__).resolve().parents[1]))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def modules():
    gen = load("gen_tools_inventory", ROOT / "tools/gen_tools_inventory.py")
    atlas = load("catalog_atlas_under_test", ROOT / "tools/file_atlas.py")
    return gen, atlas


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def collect(gen, root, monkeypatch):
    monkeypatch.setattr(gen, "ROOT", root)
    monkeypatch.setattr(gen, "TOOLS", root / "tools")
    return dict(gen.collect())


def test_multiline_opening_purpose_is_source_text_not_only_first_line(modules, tmp_path, monkeypatch):
    gen, atlas = modules
    source = ('"""example.py — Build source tables\n'
              'for tools/a_complete_renderer_with_a_long_name.py with exact source IDs.\n\n'
              'Examples:\n  python example.py --invented-example-flag\n"""\n'
              '# This later code comment is not the purpose.\nVALUE = 1\n')
    path = write(tmp_path / "tools/example.py", source)
    before = path.read_bytes()
    summary = collect(gen, tmp_path, monkeypatch)["example.py"]
    assert summary == "Build source tables for tools/a_complete_renderer_with_a_long_name.py with exact source IDs."
    assert atlas._parse(path)[1] == "example.py — " + summary
    assert "invented-example-flag" not in summary and "later code comment" not in summary
    assert path.read_bytes() == before


@pytest.mark.parametrize("description", [
    "Use tools/a_very_long_renderer_name_that_crosses_catalog_width.py for a selected plot.",
    "Only inspect the supplied data. " * 8 + "The declared producer is tools/protein_pcoa_render.py.",
])
def test_inventory_displays_complete_description_and_path(modules, description):
    gen, _ = modules
    rows = [("example.py", description)]
    assert description in gen.render_md(rows)
    assert description in gen.render_manifest_block(rows)


def test_atlas_csv_and_every_markdown_section_do_not_clip_summary(modules, tmp_path, monkeypatch):
    gen, atlas = modules
    description = "example.py — " + "source description " * 10 + "tools/ggtree_placement.R and tools/gap_directed_rescue.py."
    write(tmp_path / "tools/example.py", repr(description) + "\nVALUE = 1\n")
    monkeypatch.setattr(atlas, "ROOT", tmp_path)
    rows = atlas.build()
    assert len(rows) == 1 and rows[0]["summary"] == description
    output = tmp_path / "atlas.md"
    csv_path = tmp_path / "atlas.csv"
    assert atlas.main(["--md", str(output), "--out", str(csv_path)]) == 0
    assert output.read_text().count(description) == 4
    import csv
    with csv_path.open(newline="") as handle:
        assert list(csv.DictReader(handle))[0]["summary"] == description


@pytest.mark.parametrize("source,expected_inventory,expected_atlas", [
    ("# An unsupported capability appears only in a comment.\nVALUE = 1\n", "(no docstring)", ""),
    ('def helper():\n    """Function prose is not module purpose."""\n    return 1\n', "(no docstring)", ""),
    ('"""Purpose deliberately unknown."""\n# Claimed capability must not be inferred.\n', "Purpose deliberately unknown.", "Purpose deliberately unknown."),
    ('"""Read a file — do not infer biological production."""\n', "Read a file — do not infer biological production.", "Read a file — do not infer biological production."),
])
def test_unknowns_and_comments_do_not_create_purpose_claims(modules, tmp_path, monkeypatch, source, expected_inventory, expected_atlas):
    gen, atlas = modules
    path = write(tmp_path / "tools/example.py", source)
    assert collect(gen, tmp_path, monkeypatch)["example.py"] == expected_inventory
    assert atlas._parse(path)[1] == expected_atlas


@pytest.mark.parametrize("source,expected", [
    ("#!/bin/sh\n# example.sh — Assemble declared\n# input tables for tools/a_complete_renderer.py.\n\n# Another section.\necho ok\n", "Assemble declared input tables for tools/a_complete_renderer.py."),
    ("#!/bin/sh\necho ok\n# This implementation comment is not a header description.\n", "(no header comment)"),
    ("#!/bin/sh\n# Purpose deliberately unknown.\necho ok\n", "Purpose deliberately unknown."),
])
def test_shell_display_uses_only_initial_source_header(modules, tmp_path, monkeypatch, source, expected):
    gen, _ = modules
    write(tmp_path / "tools/example.sh", source)
    assert collect(gen, tmp_path, monkeypatch)["example.sh"] == expected


def test_connection_evidence_keeps_firstline_raw_docstring_and_source_hash(modules, tmp_path, monkeypatch):
    gen, _ = modules
    source = ('"""example.py — Inspect source tables.\n'
              'Deprecated is only text in the next physical line.\n\n'
              'Full docstring is available to search.\n"""\nVALUE = 1\n')
    path = write(tmp_path / "tools/example.py", source)
    raw_doc = ast.get_docstring(ast.parse(source))
    assert gen._module_docstring_py(path) == raw_doc
    assert gen._first_doc_line_py(path) == "Inspect source tables."
    row = gen.audit_connections(tmp_path)["tools"][0]
    assert row["summary"] == "Inspect source tables."
    assert row["sha256"] == hashlib.sha256(source.encode()).hexdigest()
    assert row["bytes"] == len(source.encode())
    # Display changes must not renew the first-line lifecycle heuristic.
    assert row["lifecycle"] == "ACTIVE_OR_UNSPECIFIED"


def test_markdown_pipe_escape_remains_and_atlas_csv_keeps_source_text(modules, tmp_path, monkeypatch):
    gen, atlas = modules
    source = '"""example.py — Read alpha | beta source fields.\nNo inferred verdict.\n"""\n'
    path = write(tmp_path / "tools/example.py", source)
    description = collect(gen, tmp_path, monkeypatch)["example.py"]
    assert description == "Read alpha \\| beta source fields. No inferred verdict."
    assert "alpha \\| beta" in gen.render_md([("example.py", description)])
    monkeypatch.setattr(atlas, "ROOT", tmp_path)
    assert atlas.build()[0]["summary"] == "example.py — Read alpha | beta source fields. No inferred verdict."
    output = tmp_path / "atlas.md"
    assert atlas.main(["--md", str(output)]) == 0
    assert "alpha \\| beta" in output.read_text()


def test_existing_long_tool_docstrings_survive_display(modules):
    gen, _ = modules
    # Generic text mirrors the verified source purpose; no shared-source reads needed.
    desc = "M5_452 P5: caption, METHODS and GENOMES_USED for a protein PCoA page, written by tools/protein_pcoa_render.py --page from the page's own receipts and tables."
    assert desc in gen.render_manifest_block([("protein_pcoa_page_docs.py", desc)])


@pytest.mark.parametrize("filename,target", [
    ("build_placement_ggtree_inputs.py", "tools/ggtree_placement.R"),
    ("gap_rescue_locus_map.py", "tools/gap_directed_rescue.py"),
    ("protein_pcoa_page_docs.py", "tools/protein_pcoa_render.py"),
])
def test_reported_real_source_path_is_complete_in_actual_renderers(modules, tmp_path, monkeypatch, filename, target):
    gen, atlas = modules
    real_root = Path(os.environ.get("CATALOG_TEST_REAL_SOURCE_ROOT", ROOT))
    path = real_root / "tools" / filename
    original = path.read_bytes()
    monkeypatch.setattr(gen, "ROOT", tmp_path)
    monkeypatch.setattr(gen, "TOOLS", path.parent)
    monkeypatch.setattr(gen, "tool_files", lambda: [path])
    descriptions = gen.collect()
    assert target in gen.render_manifest_block(descriptions)
    assert target in gen.render_md(descriptions)
    summary = atlas._parse(path)[1]
    row = dict(path="tools/" + filename, loc=len(original.splitlines()), summary=summary,
               n_defs=0, n_classes=0, fan_out=0, imports_internal="", fan_in=0, imported_by="",
               cli_verbs="", n_tests=0, test_refs="", shell_refs="", orphan=True)
    monkeypatch.setattr(atlas, "build", lambda: [row])
    output = tmp_path / "actual_source_atlas.md"
    assert atlas.main(["--md", str(output)]) == 0
    assert output.read_text().count(target) == 4
    assert path.read_bytes() == original


def test_filename_only_header_is_unknown_instead_of_using_comments(modules, tmp_path, monkeypatch):
    gen, _ = modules
    write(tmp_path / "tools/example.py", '"""example.py —\n"""\n# This claim is not source purpose.\n')
    assert collect(gen, tmp_path, monkeypatch)["example.py"] == "(no purpose description)"


def test_pipe_escape_and_firstline_reader_compatibility(modules, tmp_path):
    gen, _ = modules
    path = write(tmp_path / "example.py", '"""example.py — summary with a pipe | inside.\n"""\n')
    assert gen._first_doc_line_py(path) == "summary with a pipe \\| inside."


def test_connection_search_and_emit_owners_are_unchanged_when_preimage_available(modules):
    # Optional local review input: integrated source tests do not require lane-only paths.
    preimage = os.environ.get("CATALOG_TEST_PREIMAGE_ROOT")
    if not preimage:
        pytest.skip("preimage comparison is a lane review check; generic regressions need no preimage")
    gen, atlas = modules
    old_gen = ast.parse((Path(preimage) / "tools/gen_tools_inventory.py").read_text())
    new_gen = ast.parse(Path(gen.__file__).read_text())
    def functions(tree):
        return {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef)}
    old, new = functions(old_gen), functions(new_gen)
    for name in ("_module_docstring_py", "_first_doc_line_py", "_first_doc_line_sh", "_interface_and_lifecycle", "_scores", "audit_connections", "search_capabilities"):
        assert new[name] == old[name], name
    def emissions(tree):
        return sorted(ast.dump(node, include_attributes=False) for node in ast.walk(tree)
                      if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"emit", "print"})
    assert emissions(new_gen) == emissions(old_gen)
    old_atlas = ast.parse((Path(preimage) / "tools/file_atlas.py").read_text())
    new_atlas = ast.parse(Path(atlas.__file__).read_text())
    # The orphan listing's summary argument changes, but no emission site is added.
    assert len(emissions(old_atlas)) == len(emissions(new_atlas))
