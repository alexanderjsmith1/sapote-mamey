from mamey import judgment_store as tool

def test_retry_consolidates_legacy_duplicate_sections(tmp_path,monkeypatch):
    lay=tmp_path/'lay.md';ferm=tmp_path/'ferm.md'
    before='preamble\n\n## BGC001\n\nstale first\n\n## BGC002\n\nother locus retained\n\n## BGC001\n\nstale second\n'
    for path in [lay,ferm]:path.write_text(before)
    monkeypatch.setattr(tool,'_laypersons_path',lambda p:lay)
    monkeypatch.setattr(tool,'_fermentation_path',lambda p:ferm)
    monkeypatch.setattr(tool,'_mode_b_path',lambda p,b:tmp_path/'mode_b.md')
    monkeypatch.setattr(tool,'_update_register',lambda *a,**k:[])
    tool.record_mode_b(tmp_path,'BGC001','## §1\nsynthetic body\n',
                       layperson_paragraph='current lay note',fermentation_note='current fermentation note')
    for path in [lay,ferm]:
        text=path.read_text()
        assert text.count('## BGC001\n')==1
        assert 'stale first' not in text and 'stale second' not in text
        assert '## BGC002\n\nother locus retained' in text
        assert text.startswith('preamble\n') and text.index('## BGC001')<text.index('## BGC002')
