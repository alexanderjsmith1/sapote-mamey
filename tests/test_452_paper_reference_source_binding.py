"""Synthetic source-generation and OOXML-presence regression controls."""
import hashlib
import importlib.util
import sys
from pathlib import Path
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[1]

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

@pytest.fixture
def modules():
    return (load(ROOT / "tools/paper_reference_audit.py", "c4_fixed_parser"),
            load(ROOT / "tests/test_452_paper_reference_audit.py", "c4_fixed_fixtures"))

@pytest.mark.parametrize("replace_mode", ["inplace", "atomic"])
def test_consumed_hash_or_changed_source_refusal(modules, tmp_path, monkeypatch, replace_mode):
    parser, fixtures = modules
    source = fixtures.docx(tmp_path, ["Original consumed paragraph.", "References",
                                     "Alpha AB. 2020. Synthetic original."], "source.docx")
    replacement = fixtures.docx(tmp_path, ["Different replacement paragraph.", "References",
                                          "Beta CD. 2021. Synthetic replacement."], "replacement.docx")
    original_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    real_parse = parser.ET.fromstring
    changed = False
    def replace_after_xml_read(raw, *args, **kwargs):
        nonlocal changed
        if not changed:
            if replace_mode == "inplace":
                source.write_bytes(replacement.read_bytes())
            else:
                replacement.replace(source)
            changed = True
        return real_parse(raw, *args, **kwargs)
    monkeypatch.setattr(parser.ET, "fromstring", replace_after_xml_read)
    try:
        paragraphs, holds, binding = parser.read_docx(source, "main")
    except ValueError as exc:
        assert "SOURCE_CHANGED_DURING_READ" in str(exc)
    else:
        assert paragraphs[0]["text"] == "Original consumed paragraph."
        assert binding["sha256"] == original_sha, "Hash must describe consumed original bytes"
    assert changed

@pytest.mark.parametrize("tag,code", [
    ("altChunk", "UNSUPPORTED_ALTCHUNK"), ("fldSimple", "CACHED_FIELD_TEXT"),
    ("ins", "TRACKED_CHANGES_PRESENT"), ("del", "TRACKED_CHANGES_PRESENT"),
    ("moveFrom", "TRACKED_CHANGES_PRESENT"), ("moveTo", "TRACKED_CHANGES_PRESENT"),
])
def test_leaf_markup_keeps_absence_provisional(modules, tmp_path, tag, code):
    parser, fixtures = modules
    w = fixtures.W
    marker = f"<w:{tag}/>"
    extra = marker if tag == "altChunk" else ""
    in_paragraph = "" if tag == "altChunk" else marker
    content = (f'<w:document xmlns:w="{w}"><w:body>{extra}'
               f'<w:p>{in_paragraph}<w:r><w:t>(Missing, 2020).</w:t></w:r></w:p>'
               '<w:p><w:r><w:t>References</w:t></w:r></w:p>'
               '<w:p><w:r><w:t>Alpha AB. 2020. Synthetic reference.</w:t></w:r></w:p>'
               '</w:body></w:document>')
    source = fixtures.docx(tmp_path, [], extra_parts={"word/document.xml": content})
    report = parser.audit([("main", source)])
    assert code in {row["code"] for row in report["parsing_holds"]}
    assert report["status"] == "INCOMPLETE"
    assert report["missing_references"] and report["uncited_references"]
    assert not any(row["confirmed"] for row in report["missing_references"] + report["uncited_references"])

def test_binding_names_exact_consumed_xml_parts(modules, tmp_path):
    parser, fixtures = modules
    source = fixtures.docx(tmp_path, ["Original text.", "References", "Alpha AB. 2020. Synthetic reference."])
    with zipfile.ZipFile(source) as archive:
        expected = {"word/document.xml": hashlib.sha256(archive.read("word/document.xml")).hexdigest()}
    before = source.read_bytes()
    paragraphs, holds, binding = parser.read_docx(source, "main")
    assert binding.get("xml_parts_sha256") == expected
    assert binding["sha256"] == hashlib.sha256(before).hexdigest()
    assert source.read_bytes() == before

def test_symlink_selector_switch_keeps_opened_source_binding(modules, tmp_path, monkeypatch):
    parser, fixtures = modules
    original = fixtures.docx(tmp_path, ["Original selected text.", "References",
                                      "Alpha AB. 2020. Synthetic original."], "original.docx")
    replacement = fixtures.docx(tmp_path, ["Different text.", "References",
                                         "Beta CD. 2021. Synthetic replacement."], "replacement.docx")
    alias = tmp_path / "selected.docx"
    alias.symlink_to(original)
    original_bytes = original.read_bytes()
    original_sha = hashlib.sha256(original_bytes).hexdigest()
    real_parse = parser.ET.fromstring
    switched = False
    def switch_after_xml_read(raw, *args, **kwargs):
        nonlocal switched
        if not switched:
            alias.unlink()
            alias.symlink_to(replacement)
            switched = True
        return real_parse(raw, *args, **kwargs)
    monkeypatch.setattr(parser.ET, "fromstring", switch_after_xml_read)
    paragraphs, holds, binding = parser.read_docx(alias, "main")
    assert switched
    assert paragraphs[0]["text"] == "Original selected text."
    assert binding["sha256"] == original_sha
    assert binding["path"] == str(alias.absolute())
    assert original.read_bytes() == original_bytes

