"""Synthetic documents only: automatic appendix publication must preserve evidence."""
import importlib.util
import os
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('appendix_preservation_review', ROOT/'tools/sapote_md_preflight.py')
mp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp)
WIDE = '| ' + ' | '.join(f'c{i}' for i in range(9)) + ' |\n|' + '---|'*9 + '\n| ' + ' | '.join(f'v{i}' for i in range(9)) + ' |\n'

def setup_case(tmp_path, source_name='input.md'):
    src = tmp_path/source_name
    src.write_text('# Original source\n\n'+WIDE, encoding='utf-8')
    boss = tmp_path/'boss.md'
    boss.write_text('PRIOR BOSS', encoding='utf-8')
    return src, boss, tmp_path/'boss.appendix.md', tmp_path/'qa.json'

def refuse(src, boss, qa):
    assert mp.main([str(src), str(boss), '--qa-json', str(qa)]) == 2
    assert boss.read_text() == 'PRIOR BOSS'
    assert not qa.exists()

def test_default_sidecar_cannot_replace_source(tmp_path):
    src, boss, side, qa = setup_case(tmp_path, 'boss.appendix.md')
    saved = src.read_bytes()
    refuse(src,boss,qa)
    assert src.read_bytes() == saved

@pytest.mark.parametrize('kind', ['file','symlink','dangling','hardlink'])
def test_existing_default_leaf_preserved(tmp_path, kind):
    src,boss,side,qa = setup_case(tmp_path)
    target = tmp_path/'evidence.md'
    target.write_text('EVIDENCE', encoding='utf-8')
    if kind == 'file': side.write_text('SAVED APPENDIX', encoding='utf-8')
    elif kind == 'symlink': side.symlink_to(target)
    elif kind == 'dangling': side.symlink_to(tmp_path/'absent.md')
    else: os.link(target,side)
    inode = side.lstat().st_ino
    refuse(src,boss,qa)
    assert side.lstat().st_ino == inode
    assert target.read_text() == 'EVIDENCE'
    if kind == 'file': assert side.read_text() == 'SAVED APPENDIX'
    if kind in ('symlink','dangling'): assert side.is_symlink()
    if kind == 'dangling': assert not (tmp_path/'absent.md').exists()

def test_qa_cannot_replace_automatic_appendix(tmp_path):
    src,boss,side,_ = setup_case(tmp_path)
    refuse(src,boss,side)
    assert not side.exists()

def test_late_default_collision_preserved(tmp_path, monkeypatch):
    src,boss,side,qa = setup_case(tmp_path)
    original = os.link
    def collide(source, destination, *args, **kwargs):
        if Path(destination) == side:
            side.write_text('LATE EVIDENCE', encoding='utf-8')
        return original(source,destination,*args,**kwargs)
    monkeypatch.setattr(os,'link',collide)
    refuse(src,boss,qa)
    assert side.read_text() == 'LATE EVIDENCE'
    assert not list(tmp_path.glob('.*.tmp'))

def test_late_qa_alias_cannot_replace_published_appendix(tmp_path, monkeypatch):
    src,boss,side,qa = setup_case(tmp_path)
    original = os.link
    def alias(source,destination,*args,**kwargs):
        result = original(source,destination,*args,**kwargs)
        if Path(destination) == side: qa.symlink_to(side)
        return result
    monkeypatch.setattr(os,'link',alias)
    assert mp.main([str(src),str(boss),'--qa-json',str(qa)]) == 2
    assert boss.read_text() == 'PRIOR BOSS'
    assert qa.is_symlink() and WIDE.rstrip() in side.read_text()

def test_unicode_default_retains_full_table(tmp_path):
    src,boss,side,qa = setup_case(tmp_path)
    text = src.read_text().replace('v3','café α')
    src.write_text(text,encoding='utf-8')
    assert mp.main([str(src),str(boss),'--qa-json',str(qa)]) == 0
    assert 'café α' in side.read_text(encoding='utf-8')
    assert '| c0 | c1' not in boss.read_text()
    assert src.read_text(encoding='utf-8') == text

def test_explicit_named_appendix_keeps_replacement_contract(tmp_path):
    src,boss,side,qa = setup_case(tmp_path)
    side.write_text('OLD EXPLICIT OUTPUT',encoding='utf-8')
    assert mp.main([str(src),str(boss),'--appendix-md',str(side)]) == 0
    assert WIDE.rstrip() in side.read_text()
