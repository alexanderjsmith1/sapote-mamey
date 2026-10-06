"""Synthetic subprocess monitor tests; no scientific input or engine runs."""
import ast
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]


def monitor(monitored):
    """Load only the monitor function; scientific pipeline imports are unnecessary."""
    tree=ast.parse((ROOT/'tools/intake_harness.py').read_text())
    definition=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_monitored')
    class Sample:
        def __init__(self,pid):pass
        def memory_info(self):return SimpleNamespace(rss=1_000_000)
        def children(self,recursive=True):return []
    scope={'subprocess':subprocess,'tempfile':tempfile,'math':math,'time':time,
           '_HAVE_PSUTIL':monitored,'psutil':SimpleNamespace(Process=Sample,Error=RuntimeError)}
    exec(compile(ast.Module(body=[definition],type_ignores=[]),str(ROOT/'tools/intake_harness.py'),'exec'),scope)
    return scope['run_monitored']


@pytest.mark.parametrize('monitored',[True,False])
def test_flood_and_early_summary_return_in_full_without_pipe_deadlock(monitored):
    child='import sys;sys.stdout.write("SUMMARY_START\\n"+"X"*(8*1024*1024));sys.stdout.flush();sys.stderr.write("END\\n");sys.exit(7)'
    rc,wall,peak,text=monitor(monitored)([sys.executable,'-c',child],timeout=5)
    assert rc==7 and 0<=wall<5 and peak>=0
    assert text=='SUMMARY_START\n'+'X'*(8*1024*1024)+'END\n'


@pytest.mark.parametrize('monitored',[True,False])
def test_rapid_quiet_child_preserves_exit_status(monitored):
    rc,wall,peak,text=monitor(monitored)([sys.executable,'-c','raise SystemExit(3)'],timeout=5)
    assert (rc,text)==(3,'')


@pytest.mark.parametrize('monitored',[True,False])
def test_timeout_reaps_owned_child_and_retains_diagnostics(monitored,tmp_path):
    pidfile=tmp_path/'pid.txt'
    child='import os,sys,time;open(sys.argv[1],"w").write(str(os.getpid()));print("before timeout",flush=True);time.sleep(30)'
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        monitor(monitored)([sys.executable,'-c',child,str(pidfile)],timeout=.3)
    assert 'before timeout' in caught.value.output
    import os
    with pytest.raises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)


@pytest.mark.parametrize('timeout',[0,-1,float('inf'),float('nan')])
def test_invalid_timeout_refused_before_start(timeout):
    with pytest.raises(ValueError):monitor(True)(['must_not_start'],timeout=timeout)


def test_interruption_reaps_owned_child(monkeypatch,tmp_path):
    pidfile=tmp_path/'pid.txt'
    original=time.sleep
    def interrupt(seconds):
        # Interrupt only after the child has emitted its observable diagnostic.
        # A fixed startup sleep races process scheduling under a shared CPU.
        deadline=time.monotonic()+5
        while not pidfile.exists():
            assert time.monotonic()<deadline, 'synthetic child did not become ready'
            original(.01)
        raise KeyboardInterrupt()
    monkeypatch.setattr(time,'sleep',interrupt)
    child='import os,sys,time;from pathlib import Path;print("before interrupt",flush=True);p=Path(sys.argv[1]);staged=p.with_suffix(".ready");staged.write_text(str(os.getpid()));os.replace(staged,p);time.sleep(30)'
    with pytest.raises(KeyboardInterrupt) as caught:
        monitor(True)([sys.executable,'-c',child,str(pidfile)])
    assert 'before interrupt' in caught.value.output
    import os
    with pytest.raises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)



def test_text_output_preserves_original_universal_newline_behavior():
    child='import os;os.write(1,b"first\\r\\nsecond\\rthird\\n")'
    assert monitor(True)([sys.executable,'-c',child],timeout=5)[3]=='first\nsecond\nthird\n'


def test_explicit_encoding_is_preserved():
    child='import os;os.write(1,b"caf\\xe9\\n")'
    assert monitor(False)([sys.executable,'-c',child],timeout=5,encoding='latin-1')[3]=='café\n'
