"""Synthetic source-only sink recognition; scanned source is never executed."""
import importlib.util
import os
from pathlib import Path
import sys
import pytest
TARGET=Path(__file__).resolve().parents[1]/'tools/check_no_bundle_write_defaults.py'
spec=importlib.util.spec_from_file_location('mkdir_gate',TARGET);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
PREFIX='import os\nfrom pathlib import Path\nROOT=Path(os.getcwd())\n'


def run(tmp_path,monkeypatch,capsys,text,ceiling=0):
    root=tmp_path/'synthetic_tree';(root/'tools').mkdir(parents=True)
    source=root/'tools/probe.py';source.write_text(text)
    monkeypatch.setattr(sys,'argv',[str(TARGET),str(root),'--max',str(ceiling)])
    status=mod.main();streams=capsys.readouterr()
    assert source.read_text()==text
    return status,streams.out+streams.err


@pytest.mark.parametrize('statement',['ROOT.mkdir()','ROOT.mkdir(parents=True)','ROOT.mkdir(mode=0o755,parents=True,exist_ok=True)','ROOT.mkdir(0o755)','Path(ROOT / "child").mkdir()','Path(ROOT / "child").mkdir(parents=True)'])
def test_bound_receiver_flagged_without_treating_mode_as_path(tmp_path,monkeypatch,capsys,statement):
    status,output=run(tmp_path,monkeypatch,capsys,PREFIX+statement+'\n')
    assert status==1
    assert '1 unguarded' in output
    assert 'mkdir() receiver' in output


@pytest.mark.parametrize('source',[PREFIX+'ALIAS=ROOT / "child"\nALIAS.mkdir()\n','import os\nfrom pathlib import Path\ndef work():\n    root=Path(os.getcwd())\n    directory=root / "child"\n    directory.mkdir(exist_ok=True)\n'])
def test_same_scope_path_aliases_follow_existing_root_flow(tmp_path,monkeypatch,capsys,source):
    assert run(tmp_path,monkeypatch,capsys,source)[0]==1


@pytest.mark.parametrize('statement',['os.mkdir(ROOT)','os.mkdir(ROOT,mode=0o755)','os.makedirs(ROOT,exist_ok=True)','mkdir(ROOT)'])
def test_positional_directory_functions_retain_single_site(tmp_path,monkeypatch,capsys,statement):
    status,output=run(tmp_path,monkeypatch,capsys,PREFIX+statement+'\n',ceiling=1)
    assert status==0
    assert '1 unguarded site(s)' in output


@pytest.mark.parametrize('source',['from pathlib import Path\nROOT=Path(__file__).parent\nROOT.mkdir(exist_ok=True)\n','from pathlib import Path\nROOT=Path("explicit-location")\nROOT.mkdir()\n',PREFIX+'def work():\n    assert_output_outside_bundle(ROOT,__file__)\n    ROOT.mkdir(parents=True)\n',PREFIX+'def guard(path):\n    assert_output_outside_bundle(path,__file__)\ndef work():\n    guard(ROOT)\n    ROOT.mkdir()\n'])
def test_existing_safe_roots_and_guard_policy_preserved(tmp_path,monkeypatch,capsys,source):
    assert run(tmp_path,monkeypatch,capsys,source)[0]==0


def test_allowlist_still_waives_named_function(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(mod,'ALLOWLIST',{'tools/probe.py:<module>':'synthetic owner waiver'})
    assert run(tmp_path,monkeypatch,capsys,PREFIX+'ROOT.mkdir()\n')[0]==0


def test_receiver_site_obeys_existing_ceiling(tmp_path,monkeypatch,capsys):
    status,output=run(tmp_path,monkeypatch,capsys,PREFIX+'ROOT.mkdir(mode=0o755)\n',ceiling=1)
    assert status==0 and '1 unguarded site(s)' in output


def test_scanned_code_not_executed(tmp_path,monkeypatch,capsys):
    assert run(tmp_path,monkeypatch,capsys,'raise AssertionError("SCANNED_SOURCE_EXECUTED")\n'+PREFIX+'ROOT.mkdir()\n')[0]==1


def test_unreadable_subdirectory_refuses_partial_scan(tmp_path, monkeypatch, capsys):
    root = tmp_path / "tree"; good = root / "tools"; good.mkdir(parents=True)
    (good / "good.py").write_text("value = 1\n")
    hidden = good / "blocked"; hidden.mkdir()
    (hidden / "source.py").write_text("value = 2\n")
    original = mod._os.scandir
    def denied(path):
        if Path(path) == hidden: raise PermissionError(13, "synthetic denied", str(path))
        return original(path)
    monkeypatch.setattr(mod._os, "scandir", denied)
    monkeypatch.setattr(sys, "argv", [str(TARGET), str(root)])
    assert mod.main() == 2
    streams = capsys.readouterr()
    assert "COULD NOT SCAN" in streams.err and str(hidden) in streams.err
    assert "check OK" not in streams.out

def test_absent_optional_directories_still_allowed(tmp_path, monkeypatch, capsys):
    root = tmp_path / "tree"; good = root / "tools"; good.mkdir(parents=True)
    (good / "good.py").write_text("value = 1\n")
    monkeypatch.setattr(sys, "argv", [str(TARGET), str(root)])
    assert mod.main() == 0
    assert "1 file(s)" in capsys.readouterr().out


def test_read_error_returns_typed_failure(tmp_path, monkeypatch, capsys):
    root=tmp_path/"tree"; tools=root/"tools"; tools.mkdir(parents=True); source=tools/"selected.py"; source.write_text("x = 1")
    original=Path.read_text
    def denied(path,*args,**kwargs):
        if path == source: raise PermissionError("synthetic read denied")
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,"read_text",denied); monkeypatch.setattr(sys,"argv",[str(TARGET),str(root)])
    assert mod.main() == 2
    streams=capsys.readouterr(); assert "COULD NOT READ" in streams.err and "selected.py" in streams.err and "PASS" not in streams.out


@pytest.mark.parametrize("root_link", [False, True], ids=["nested", "scope-root"])
def test_unscanned_directory_symlink_refuses(tmp_path, monkeypatch, capsys, root_link):
    root=tmp_path/"tree";root.mkdir();outside=tmp_path/"outside";outside.mkdir();(outside/"missed.py").write_text("x = 1")
    if root_link:
        (root/"tools").symlink_to(outside,target_is_directory=True)
    else:
        tools=root/"tools";tools.mkdir();(tools/"clean.py").write_text("x = 1");(tools/"linked").symlink_to(outside,target_is_directory=True)
    monkeypatch.setattr(sys,"argv",[str(TARGET),str(root)])
    result=mod.main();streams=capsys.readouterr()
    if root_link:
        assert result == 0 and "check OK" in streams.out
    else:
        assert result == 2 and "COULD NOT SCAN" in streams.err and "symlink" in streams.err.lower() and "check OK" not in streams.out


@pytest.mark.parametrize("failure",["is_dir","is_symlink"])
def test_entry_classification_failure_refuses_partial_scan(tmp_path,monkeypatch,capsys,failure):
    root=tmp_path/"tree";(root/"tools"/"hidden").mkdir(parents=True)
    (root/"tools"/"clean.py").write_text("value=1\n")
    (root/"tools"/"hidden"/"unsafe.py").write_text(PREFIX+"ROOT.mkdir()\n")
    original=os.scandir
    class EntryProxy:
        def __init__(self,entry):self.entry=entry
        def __getattr__(self,name):return getattr(self.entry,name)
        def is_dir(self,*args,**kwargs):
            if self.entry.name=="hidden" and failure=="is_dir":raise OSError("synthetic classification failure")
            return self.entry.is_dir(*args,**kwargs)
        def is_symlink(self):
            if self.entry.name=="hidden" and failure=="is_symlink":raise OSError("synthetic classification failure")
            return self.entry.is_symlink()
    class IterProxy:
        def __init__(self,path):self.iterator=original(path)
        def __enter__(self):self.iterator.__enter__();return self
        def __exit__(self,*args):return self.iterator.__exit__(*args)
        def __iter__(self):return self
        def __next__(self):return EntryProxy(next(self.iterator))
    monkeypatch.setattr(os,"scandir",lambda path:IterProxy(path));monkeypatch.setattr(sys,"argv",[str(TARGET),str(root)])
    status=mod.main();streams=capsys.readouterr()
    assert status==2 and "COULD NOT SCAN" in streams.err and "hidden" in streams.err
    assert "check OK" not in streams.out
