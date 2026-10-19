"""Bounded liveness/identity controls, plus real self-owned already-stopped child."""
import errno, importlib.util, json, os, signal, subprocess, sys, time
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location("cleanup_support",Path(__file__).resolve().parents[1]/"tools/_release_validation.py")
rv=importlib.util.module_from_spec(spec);spec.loader.exec_module(rv)

class Process:
    pid=12345
    def __init__(self): self.live=True
    def poll(self): return None if self.live else -15
    def wait(self,timeout=None):
        if self.live: raise subprocess.TimeoutExpired("fixture",timeout)
        return -15

def fast_clock(monkeypatch):
    ticks=iter(range(100000))
    monkeypatch.setattr(rv.time,"monotonic",lambda:next(ticks))
    monkeypatch.setattr(rv.time,"sleep",lambda _:None)

def test_group_signal_precedes_individual_pid_stop(monkeypatch):
    process=Process();tree=rv._OwnedProcessTree(process.pid);calls=[]
    monkeypatch.setattr(rv,"_process_snapshot",lambda:{12345:(1,12345,20,"birth")} if process.live else {})
    def pid_stop(pid,sig): calls.append("pid");process.live=False
    def group_stop(pid,sig):
        calls.append("group")
        if not process.live:raise PermissionError(errno.EPERM,"already stopped group")
        process.live=False
    monkeypatch.setattr(rv.os,"kill",pid_stop);monkeypatch.setattr(rv.os,"killpg",group_stop)
    assert tree.stop(process) is None
    assert calls==["group"] and process.poll() is not None

def test_live_denied_group_remains_nonpass(monkeypatch):
    fast_clock(monkeypatch);process=Process();tree=rv._OwnedProcessTree(process.pid)
    monkeypatch.setattr(rv,"_process_snapshot",lambda:{12345:(1,12345,20,"birth")})
    def denied(*args):raise PermissionError(errno.EPERM,"live fixture denied")
    monkeypatch.setattr(rv.os,"kill",denied);monkeypatch.setattr(rv.os,"killpg",denied)
    assert tree.stop(process) is not None
    assert process.poll() is None
    assert any(e["status"]=="SIGNAL_FAILED" for e in tree.cleanup_events)
    assert tree.last_owned

def test_reused_root_group_is_not_signaled(monkeypatch):
    fast_clock(monkeypatch);process=Process();process.live=False
    tree=rv._OwnedProcessTree(process.pid);tree.known[12345]=(12345,"old birth")
    monkeypatch.setattr(rv,"_process_snapshot",lambda:{12345:(1,12345,20,"new birth")})
    calls=[];monkeypatch.setattr(rv.os,"kill",lambda *a:calls.append(a));monkeypatch.setattr(rv.os,"killpg",lambda *a:calls.append(a))
    assert tree.stop(process) is not None
    assert not calls and tree.scope_uncertain

def test_zombies_are_not_live_owned_members(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(rv.subprocess,"run",lambda *a,**kw:SimpleNamespace(stdout="12 1 12 0 Z Fri Oct 9 18:00:00 2026\n13 1 13 10 S Fri Oct 9 18:00:01 2026\n"))
    rows=rv._process_snapshot()
    assert 12 not in rows and rows[13]==(1,13,10240,"Fri Oct 9 18:00:01 2026")

def test_monitor_failure_retains_nonpass_even_when_fallback_stops_root(monkeypatch):
    fast_clock(monkeypatch);process=Process();tree=rv._OwnedProcessTree(process.pid)
    def failed():raise rv.ValidationRefused("fixture unavailable snapshot")
    monkeypatch.setattr(rv,"_process_snapshot",failed)
    monkeypatch.setattr(rv.os,"killpg",lambda *a:setattr(process,"live",False))
    assert tree.stop(process) is not None and process.poll() is not None

def test_interrupted_cleanup_refusal_preserves_original_and_sidecar(tmp_path,monkeypatch):
    process=Process()
    monkeypatch.setattr(rv.subprocess,"Popen",lambda *a,**kw:process)
    class Tree:
        known={};last_owned={12345:()};scope_uncertain=False;cleanup_events=[{"status":"SIGNAL_FAILED"}]
        def __init__(self,pid):pass
        def refresh(self):raise rv.WatchedTermination(signal.SIGTERM)
        def stop(self,p):return "PROCESS_CLEANUP_SIGNAL_FAILED"
    monkeypatch.setattr(rv,"_OwnedProcessTree",Tree)
    with pytest.raises(rv.ValidationRefused) as err:
        rv.run_watched(["fixture"],cwd=tmp_path,log=tmp_path/"child.log",env=dict(os.environ),sampler=lambda _:0,min_disk=0)
    assert isinstance(err.value.__cause__,rv.WatchedTermination)
    reports=list(tmp_path.glob("child.log.cleanup-*.json"));assert len(reports)==1
    report=json.loads(reports[0].read_text())
    assert report["status"]=="CLEANUP_UNCONFIRMED" and report["root_returncode"] is None
    assert "SIGTERM" in report["original_interruption"] and report["remaining_observed_pids"]==[12345]

def test_real_already_stopped_unreaped_root_is_verified(tmp_path):
    heartbeat=tmp_path/"heartbeat"
    child="from pathlib import Path;import time\np=Path("+repr(str(heartbeat))+")\nuntil=time.monotonic()+3\nwhile time.monotonic()<until:\n p.write_text(str(time.monotonic()));time.sleep(0.02)"
    process=subprocess.Popen([sys.executable,"-B","-c",child],start_new_session=True)
    try:
        deadline=time.monotonic()+2
        while not heartbeat.exists() and time.monotonic()<deadline:time.sleep(.01)
        assert heartbeat.exists();tree=rv._OwnedProcessTree(process.pid);tree.refresh()
        os.kill(process.pid,signal.SIGTERM);time.sleep(.1) # deliberately do not poll/reap before stop
        first=heartbeat.read_text()
        assert tree.stop(process) is None
        assert process.poll() is not None
        time.sleep(.1);assert heartbeat.read_text()==first
    finally:
        if process.poll() is None:process.kill()
        process.wait(timeout=4)


def test_group_error_after_verified_exit_is_retained_as_benign(monkeypatch):
    process=Process();tree=rv._OwnedProcessTree(process.pid)
    monkeypatch.setattr(rv,"_process_snapshot",lambda:{12345:(1,12345,20,"birth")} if process.live else {})
    def stopped_between_snapshot_and_signal(*args):
        process.live=False
        raise PermissionError(errno.EPERM,"fixture stopped between observation and signal")
    monkeypatch.setattr(rv.os,"killpg",stopped_between_snapshot_and_signal)
    monkeypatch.setattr(rv.os,"kill",lambda *a:pytest.fail("unexpected PID signal after verified exit"))
    assert tree.stop(process) is None
    assert any(e["status"]=="ERROR_AFTER_VERIFIED_EXIT" and e["errno"]==errno.EPERM for e in tree.cleanup_events)


def test_real_term_ignoring_session_requires_kill_and_stops_heartbeat(tmp_path):
    heartbeat=tmp_path/"heartbeat"
    code="from pathlib import Path;import signal,time\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\np=Path("+repr(str(heartbeat))+")\nuntil=time.monotonic()+8\nwhile time.monotonic()<until:\n p.write_text(str(time.monotonic()));time.sleep(0.02)"
    result=rv.run_watched([sys.executable,"-B","-c",code],cwd=tmp_path,log=tmp_path/"ignore-term.log",env=dict(os.environ),min_disk=0,timeout=.3,poll_interval=.04)
    assert result["stop_reason"]=="TIME_LIMIT" and result["exit_code"]==-signal.SIGKILL
    assert result["cleanup_error"] is None and heartbeat.exists()
    assert any(e.get("signal")=="SIGKILL" and e["status"]=="SENT" for e in result["cleanup_events"])
    first=heartbeat.read_text();time.sleep(.15);assert heartbeat.read_text()==first
