from pathlib import Path
from mamey import modeb_subsections as tool

def test_external_genus_source_is_the_file_read(tmp_path,monkeypatch):
    monkeypatch.setattr(tool,'_genus_of',lambda p:'SyntheticGenus')
    source=tmp_path/'external'/'SyntheticGenus.md';source.parent.mkdir();source.write_text('- **SYNTHETIC_TEST_CONTEXT**\n')
    text=tool.genus_literature(tmp_path,lit_dir=str(source.parent))
    assert f'Source: `{source.resolve()}`' in text
    assert 'SYNTHETIC_TEST_CONTEXT' in text
    assert 'Source: `mamey/data/literature/' not in text

def test_bundle_fallback_keeps_portable_source_label(tmp_path,monkeypatch):
    module=tmp_path/'fake_bundle'/'mamey'/'modeb_subsections.py'
    source=module.parent/'data/literature/SyntheticGenus.md';source.parent.mkdir(parents=True);source.write_text('- **SYNTHETIC_TEST_CONTEXT**\n')
    monkeypatch.setattr(tool,'__file__',str(module));monkeypatch.setattr(tool,'_genus_of',lambda p:'SyntheticGenus')
    text=tool.genus_literature(tmp_path,lit_dir=str(tmp_path/'missing'))
    assert 'Source: `mamey/data/literature/SyntheticGenus.md`' in text
    assert 'SYNTHETIC_TEST_CONTEXT' in text
