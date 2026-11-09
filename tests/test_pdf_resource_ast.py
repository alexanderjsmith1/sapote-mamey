"""Synthetic parser and receipt checks; no image rendering or network access."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
PANDOC = os.environ.get("PANDOC") or shutil.which("pandoc")
pytestmark = pytest.mark.skipif(not PANDOC, reason="Pandoc required")
PREFLIGHT = str(ROOT / "tools/sapote_md_preflight.py")
PERSIST = str(ROOT / "tools/persist_pdf_conversion_bindings.py")
PUBLISH = str(ROOT / "tools/publish_pdf_fallback_pair.py")
BUNDLE = str(ROOT)


def load(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preparer = load("pdf_ast_preparer", ROOT / "tools/prepare_pdf_resources.py")
persister = load("pdf_binding_persister", PERSIST)


def inputs(tmp_path, body):
    source = tmp_path / "source"
    work = tmp_path / "work"
    source.mkdir()
    work.mkdir()
    markdown = source / "input.md"
    markdown.write_text(body)
    return source, work, markdown, work / "resources.md"


def image_nodes(node):
    result = {"Image": [], "Link": []}
    def visit(value):
        if isinstance(value, dict):
            if value.get("t") in result:
                result[value["t"]].append(value["c"][-1])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(node)
    return result


def filtered_ast(markdown, work):
    env = dict(os.environ, SAPOTE_PDF_RESOURCE_MAP=str(work / "resources.resource_map.json"))
    result = subprocess.run([PANDOC, str(markdown), "-f", "markdown", "-t", "json",
                             "--lua-filter", str(ROOT / "tools/pdf_resource_filter.lua")],
                            env=env, capture_output=True, text=True)
    return result


def test_reference_forms_shared_link_and_receipt(tmp_path, monkeypatch):
    body = ("![Inline](panel.svg)\n\n![Full][art]\n\n![Folded][ART]\n\n"
            "![Collapsed][]\n\n![Shortcut]\n\n[art]: panel.svg \"Figure\"\n"
            "[Collapsed]: panel.svg\n[Shortcut]: panel.svg\n\n[art]\n\n"
            "`![Code](missing.svg)`\n")
    source, work, markdown, prepared = inputs(tmp_path, body)
    svg = source / "panel.svg"
    svg.write_text("<svg/>")
    calls = []
    def convert(url, write_to):
        calls.append(url)
        Path(write_to).write_bytes(b"%PDF synthetic converted bytes")
    monkeypatch.setitem(sys.modules, "cairosvg", types.SimpleNamespace(svg2pdf=convert))
    preparer.prepare(markdown, prepared, pandoc=PANDOC)
    assert prepared.read_text() == body
    assert calls == [str(svg.resolve())]
    safe = work / "safe.md"
    preflight = subprocess.run([sys.executable, PREFLIGHT, str(prepared), str(safe),
                               "--profile", "boss", "--appendix-md", str(work / "appendix.md"),
                               "--qa-json", str(work / "qa.json")], capture_output=True, text=True)
    assert preflight.returncode == 0, preflight.stderr
    result = filtered_ast(safe, work)
    assert result.returncode == 0, result.stderr
    nodes = image_nodes(json.loads(result.stdout))
    receipt = next(work.glob("*.pdf.conversion.json"))
    converted = Path(json.loads(receipt.read_text())["converted_pdf"])
    assert len(nodes["Image"]) == 5
    assert {entry[0] for entry in nodes["Image"]} == {str(converted)}
    assert [entry[0] for entry in nodes["Link"]] == ["panel.svg"]
    assert len(list(work.glob("*.conversion.json"))) == 1
    tex = subprocess.run([PANDOC, str(safe), "-f", "markdown", "-t", "latex",
                          "--lua-filter", str(ROOT / "tools/pdf_resource_filter.lua")],
                         env=dict(os.environ, SAPOTE_PDF_RESOURCE_MAP=str(work / "resources.resource_map.json")),
                         capture_output=True, text=True)
    assert tex.returncode == 0, tex.stderr
    assert tex.stdout.count("\\includegraphics") == 5 and "\\includesvg" not in tex.stdout
    draft = work / "mock_final.pdf"
    draft.write_bytes(b"%PDF synthetic downstream bytes")
    summary = persister.persist(work, draft, tmp_path / "binding.json")
    assert summary["conversion_count"] == 1
    assert summary["conversions"][0]["source_svg_sha256"] == hashlib.sha256(svg.read_bytes()).hexdigest()
    assert summary["conversions"][0]["intermediate_pdf_sha256"] == hashlib.sha256(converted.read_bytes()).hexdigest()
    output = tmp_path / "published/result.pdf"
    binding = tmp_path / "published/result.resource_bindings.json"
    published = subprocess.run([sys.executable, PUBLISH, str(work), str(draft), str(output), str(binding)],
                               env=dict(os.environ, PYTHONPATH=BUNDLE), capture_output=True, text=True)
    assert published.returncode == 0, published.stderr
    final_binding = json.loads(binding.read_text())
    assert final_binding["conversion_count"] == 1
    assert final_binding["output_pdf_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()


def test_angle_and_percent_space_paths_resolve_to_one_local_file(tmp_path):
    source, work, markdown, prepared = inputs(tmp_path, "![Angle](<a b.png>)\n\n![Percent](a%20b.png)\n")
    raster = source / "a b.png"
    raster.write_bytes(b"synthetic raster placeholder")
    preparer.prepare(markdown, prepared, pandoc=PANDOC)
    mapping = json.loads((work / "resources.resource_map.json").read_text())
    assert mapping["targets"] == {"a%20b.png": str(raster.resolve())}
    result = filtered_ast(prepared, work)
    assert result.returncode == 0, result.stderr
    assert [entry[0] for entry in image_nodes(json.loads(result.stdout))["Image"]] == [str(raster.resolve())] * 2


@pytest.mark.parametrize("target", ["https://example.invalid/a.svg", "//example.invalid/a.svg",
                                   "data:image/png;base64,AAAA", "file:///tmp/a.svg"])
def test_remote_and_nonlocal_targets_refused(tmp_path, target):
    _, work, markdown, prepared = inputs(tmp_path, f"![Reference][art]\n\n[art]: {target}\n")
    with pytest.raises(ValueError, match="PDF_REMOTE_RESOURCE_REFUSED"):
        preparer.prepare(markdown, prepared, pandoc=PANDOC)
    assert not prepared.exists() and not (work / "resources.resource_map.json").exists()


def test_missing_reference_target_refused(tmp_path):
    _, work, markdown, prepared = inputs(tmp_path, "![Reference][art]\n\n[art]: missing.svg\n")
    with pytest.raises(ValueError, match="PDF_IMAGE_UNAVAILABLE"):
        preparer.prepare(markdown, prepared, pandoc=PANDOC)
    assert not prepared.exists() and not (work / "resources.resource_map.json").exists()


@pytest.mark.parametrize("raw", ['<img src="missing.svg" />', r'\includegraphics{missing.svg}',
                                      '<div style="background-image: url(missing.png)"></div>'])
def test_raw_embeds_fail_closed(tmp_path, raw):
    _, work, markdown, prepared = inputs(tmp_path, raw + "\n")
    with pytest.raises(ValueError, match="PDF_RAW_IMAGE_RESOURCE_REFUSED"):
        preparer.prepare(markdown, prepared, pandoc=PANDOC)
    assert not prepared.exists() and not (work / "resources.resource_map.json").exists()


@pytest.mark.parametrize("later,expected", [
    ("![Later](missing.svg)", "PDF_IMAGE_UNMAPPED"),
    ('<img src="missing.svg" />', "PDF_RAW_IMAGE_RESOURCE_REFUSED"),
    (r'\includegraphics{missing.svg}', "PDF_RAW_IMAGE_RESOURCE_REFUSED"),
    ('<div style="background-image: url(missing.png)"></div>', "PDF_RAW_IMAGE_RESOURCE_REFUSED"),
])
def test_filter_refuses_resource_added_after_preparation(tmp_path, later, expected):
    _, work, markdown, prepared = inputs(tmp_path, "No image.\n")
    preparer.prepare(markdown, prepared, pandoc=PANDOC)
    prepared.write_text(later + "\n")
    result = filtered_ast(prepared, work)
    assert result.returncode != 0
    assert expected in result.stderr
