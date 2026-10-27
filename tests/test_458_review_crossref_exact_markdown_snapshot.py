from pathlib import Path
import hashlib
import importlib.util
import os
import pytest
ROOT=Path(os.environ.get('CROSSREF_REVIEW_BASE',Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('crossref_snapshot_review',ROOT/'tools/chapter_table_crossrefs.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
def manifest(path):return {'documents':[{'id':'fixture','scope':'chapter5','path':str(path)}]}

def edit_after_reads(monkeypatch,source,replacements):
    original=Path.open;remaining=list(replacements)
    def opening(path,*args,**kwargs):
        raw=original(path,*args,**kwargs)
        if path!=source or not remaining:return raw
        replacement=remaining.pop(0)
        class Captured:
            def __enter__(self):return raw.__enter__()
            def __exit__(self,*exc):
                answer=raw.__exit__(*exc)
                with original(source,'wb') as writer:writer.write(replacement)
                return answer
        return Captured()
    monkeypatch.setattr(Path,'open',opening)

def test_aba_change_cannot_return_mismatched_pin_and_events(tmp_path,monkeypatch):
    source=tmp_path/'chapter.md';old=b'Table 5.1. Old snapshot.\n';new=b'Table 5.2. Changed snapshot.\n';source.write_bytes(old)
    edit_after_reads(monkeypatch,source,[new,old])
    try:result=tool.audit_manifest(manifest(source))
    except ValueError as error:
        assert 'primary source changed during read' in str(error)
        return
    label=result['events'][0]['label'];binding=result['source_bindings'][0];used={'5.1':old,'5.2':new}[label]
    assert binding['sha256']==hashlib.sha256(used).hexdigest(),'EVENTS_AND_PIN_DESCRIBE_DIFFERENT_VERSIONS'
    assert binding['bytes']==len(used)

def test_existing_ordinary_change_refusal_is_preserved(tmp_path,monkeypatch):
    source=tmp_path/'chapter.md';source.write_text('Table 5.1. Old snapshot.\n')
    edit_after_reads(monkeypatch,source,[b'Table 5.2. Changed snapshot.\n'])
    with pytest.raises(ValueError,match='primary source changed during read'):tool.audit_manifest(manifest(source))

def test_raw_utf8_crlf_pin_and_visible_line_numbers(tmp_path):
    source=tmp_path/'chapter.md';raw='<!-- note -->\r\nTable 5.1. Café counts.\r\nSee Table 5.1.\r\n'.encode('utf-8');source.write_bytes(raw)
    result=tool.audit_manifest(manifest(source));binding=result['source_bindings'][0]
    assert binding['sha256']==hashlib.sha256(raw).hexdigest() and binding['bytes']==len(raw)
    assert [x['location'] for x in result['events']]==['line:2','line:3']
    assert result['status']=='ACCOUNTED'
