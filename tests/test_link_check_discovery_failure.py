import importlib.util, os
from pathlib import Path
import pytest
HOOK_PATH=Path(__file__).resolve().parents[1]/"hooks/link_check.py"

def load(monkeypatch,tmp_path):
 monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT",str(tmp_path));monkeypatch.delenv("SAPOTE_DELIVERABLE_ROOT",raising=False)
 spec=importlib.util.spec_from_file_location("hook_selected",str(HOOK_PATH));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_unavailable_discovery_refuses_legacy_guess(tmp_path,monkeypatch,capsys):
 for n in ("strain_data","other"):
  d=tmp_path/n;d.mkdir();(d/"WHERE_THINGS_LIVE.md").write_text("# synthetic\n")
 m=load(monkeypatch,tmp_path);capsys.readouterr();original=os.listdir
 def denied(path):
  if Path(path)==tmp_path:raise PermissionError("injected denied")
  return original(path)
 monkeypatch.setattr(os,"listdir",denied);assert m.deliverable_hub_root(str(tmp_path)) is None
 assert "discovery unavailable" in capsys.readouterr().err

def test_ambiguity_without_injection_still_refuses(tmp_path,monkeypatch,capsys):
 for n in ("strain_data","other"):
  d=tmp_path/n;d.mkdir();(d/"WHERE_THINGS_LIVE.md").write_text("# synthetic\n")
 m=load(monkeypatch,tmp_path);assert m.deliverable_hub_root(str(tmp_path)) is None
 assert "ambiguous" in capsys.readouterr().err

def test_single_root_still_selected(tmp_path,monkeypatch):
 d=tmp_path/"home";d.mkdir();(d/"WHERE_THINGS_LIVE.md").write_text("# synthetic\n")
 m=load(monkeypatch,tmp_path);assert m.deliverable_hub_root(str(tmp_path))==str(d)


def test_visible_wrapper_preserves_initial_warning_without_rescanning(tmp_path,monkeypatch,capsys):
 import json
 m=load(monkeypatch,tmp_path);capsys.readouterr()
 monkeypatch.setattr(m,"DELIVERABLE_HUB_ROOT",None)
 monkeypatch.setattr(m,"_INITIAL_DISCOVERY_WARNING","link_check: discovery unavailable (synthetic)\n",raising=False)
 def forbidden(_):raise AssertionError("must not rescan")
 monkeypatch.setattr(m,"deliverable_hub_root",forbidden)
 assert m._run_visible()==0
 assert "discovery unavailable" in json.loads(capsys.readouterr().out)["systemMessage"]


def test_transient_import_failure_is_visible_in_hook_protocol(tmp_path):
 import json, subprocess, sys
 workspace=tmp_path/"workspace";workspace.mkdir()
 for name in ("strain_data","other"):
  d=workspace/name;d.mkdir();(d/"WHERE_THINGS_LIVE.md").write_text("# synthetic\n")
 injection=tmp_path/"injection";injection.mkdir()
 (injection/"sitecustomize.py").write_text('import os\n_original=os.listdir\n_denied=False\ndef denied(path):\n    global _denied\n    if str(path)==os.environ.get("SYNTHETIC_DENY_WORKSPACE") and not _denied:\n        _denied=True\n        raise PermissionError("synthetic denied")\n    return _original(path)\nos.listdir=denied\n')
 env=os.environ.copy();env.pop("SAPOTE_DELIVERABLE_ROOT",None);env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONPATH=str(injection),SAPOTE_WORKSPACE_ROOT=str(workspace),SYNTHETIC_DENY_WORKSPACE=str(workspace))
 q=subprocess.run([sys.executable,"-B",str(HOOK_PATH)],env=env,capture_output=True,text=True,timeout=30)
 assert q.returncode==0 and "discovery unavailable" in json.loads(q.stdout)["systemMessage"]
