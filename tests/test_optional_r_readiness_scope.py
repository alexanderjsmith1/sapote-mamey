from pathlib import Path
import importlib.util
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("scoped_r",ROOT/"mamey/optional_r.py")
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

def test_empty_profile_cannot_claim_ready_without_execution(monkeypatch):
    monkeypatch.setattr(r.subprocess,"run",lambda *a,**k:pytest.fail("empty profile must not run R"))
    state,message,path=r.r_package_status((),executable="nonexistent selected R")
    assert state=="UNVERIFIED" and "not measured" in message

def test_string_profile_is_rejected_before_subprocess(monkeypatch):
    monkeypatch.setattr(r.subprocess,"run",lambda *a,**k:pytest.fail("invalid profile must not run R"))
    with pytest.raises(ValueError,match="sequence"):
        r.r_package_status("ggplot2",executable="R")

def test_namespace_success_is_qualified(monkeypatch):
    calls=[]
    def run(command,**kw):calls.append(command);return SimpleNamespace(returncode=0,stdout="SAPOTE_R_READY:ggplot2\n",stderr="")
    monkeypatch.setattr(r.subprocess,"run",run)
    state,message,path=r.r_package_status(("ggplot2",),executable="R with spaces")
    assert state=="READY" and "rendering unverified" in message
    assert calls[0][0]=="R with spaces"

def test_missing_namespace_remains_unavailable(monkeypatch):
    monkeypatch.setattr(r.subprocess,"run",lambda *a,**k:SimpleNamespace(returncode=10,stdout="SAPOTE_R_MISSING:ggplot2",stderr=""))
    assert r.r_package_status(("ggplot2",),executable="R")[0]=="UNAVAILABLE"


def test_zero_exit_without_namespace_confirmation_is_unverified(monkeypatch):
    monkeypatch.setattr(r.subprocess,"run",lambda *a,**k:SimpleNamespace(returncode=0,stdout="",stderr=""))
    state,message,path=r.r_package_status(("ggplot2",),executable="wrong zero-exit program")
    assert state=="UNVERIFIED" and "verify the selected Rscript" in message
