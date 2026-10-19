"""Execute the selected test call sites only in tiny synthetic source trees."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tests" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_intake_exit_status_child_never_writes_source_cache(tmp_path, monkeypatch):
    module = load("test_443_intake_harness_exit_status_reports_failed_inputs")
    source = tmp_path / "source"
    source.mkdir()
    sentinel = source / "sentinel.py"
    sentinel.write_text("VALUE=1\n")
    harness = source / "intake_harness.py"
    harness.write_text('import sentinel\nprint("RUN_FAILED 1 BATCH_INCOMPLETE")\nraise SystemExit(1)\n')
    fixture = tmp_path / "public_fixture.zip"
    with zipfile.ZipFile(fixture, "w") as archive:
        archive.writestr("region.gbk", "synthetic public-safe record")
    module.ROOT = source
    module.HARNESS = harness
    module.FIXTURE = fixture
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    run = tmp_path / "run"
    run.mkdir()
    module.test_real_batch_with_a_broken_input_exits_one(run)
    assert not list(source.rglob("*.pyc"))
    assert not list(source.rglob("__pycache__"))


@pytest.mark.parametrize("bare", [False, True])
def test_isolated_reference_child_preserves_synthetic_source(tmp_path, monkeypatch, bare):
    module = load("test_447_full_reference_isolation")
    source = tmp_path / "source"
    (source / "tools").mkdir(parents=True)
    (source / "mamey").mkdir()
    (source / "mamey/__init__.py").write_text("")
    (source / "mamey/bank_transaction.py").write_text(
        "hold_reader=release_reader_locks=reader=lock=prepare=coherent=lambda:None\n"
        "BankError=RuntimeError\nSTORES=[]\n")
    (source / "tools/_bankio.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "before=list(sys.path)\n"
        "try:\n sys.path.insert(0,str(Path(__file__).resolve().parents[1]))\n from mamey.bank_transaction import *\n"
        "finally: sys.path[:]=before\n")
    module.ROOT = source
    run = tmp_path / "run"
    run.mkdir()
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    module.test_bankio_import_preserves_path_and_resolves_shared_api(run, bare)
    assert not list(source.rglob("*.pyc"))
    assert not list(source.rglob("__pycache__"))


@pytest.mark.parametrize("flag", ["-I", "-E"])
def test_guard_rejects_env_ignoring_python_without_explicit_B(tmp_path, flag):
    module = load("test_hermetic_env_guard_v97404")
    sample = tmp_path / "test_unsafe.py"
    sample.write_text("import subprocess,sys\nsubprocess.run([sys.executable," + repr(flag) + ",'\x2dc','pass'])\n")
    assert module._violations(sample) == ["test_unsafe.py:2"]
    sample.write_text("import subprocess,sys\nsubprocess.run([sys.executable,'-B'," + repr(flag) + ",'\x2dc','pass'])\n")
    assert module._violations(sample) == []


def test_guard_rejects_env_comprehension_dropping_bytecode_flag(tmp_path):
    module = load("test_hermetic_env_guard_v97404")
    sample = tmp_path / "test_unsafe.py"
    sample.write_text('import subprocess,os,sys\ndef t():\n env={k:v for k,v in os.environ.items() if k!="PYTHONDONTWRITEBYTECODE"}\n subprocess.run([sys.executable,"x.py"],env=env)\n')
    assert module._violations(sample) == ["test_unsafe.py:4"]


def test_guard_allows_explicit_B_with_filtered_environment(tmp_path):
    module = load("test_hermetic_env_guard_v97404")
    sample = tmp_path / "test_safe.py"
    sample.write_text('import subprocess,os,sys\ndef t():\n env={k:v for k,v in os.environ.items() if k!="PYTHONDONTWRITEBYTECODE"}\n subprocess.run([sys.executable,"-B","x.py"],env=env)\n')
    assert module._violations(sample) == []


@pytest.mark.parametrize("executable", ["bash", "/bin/bash", "C:\\shells\\bash.exe", "/usr/bin/env"])
def test_non_python_B_cannot_bypass_child_environment_guard(tmp_path, executable):
    module = load("test_hermetic_env_guard_v97404")
    sample = tmp_path / "test_shell.py"
    sample.write_text("import subprocess\nsubprocess.run([" + repr(executable) + ",'\x2dB','script.sh'],env={'PATH':'/bin'})\n")
    assert module._violations(sample) == ["test_shell.py:2"]
    sample.write_text("import subprocess\nsubprocess.run([" + repr(executable) + ",'\x2dB','script.sh'],env={'PYTHONDONTWRITEBYTECODE':'1'})\n")
    assert module._violations(sample) == []


@pytest.mark.parametrize("executable", ["python", "python3", "python3.12", "/opt/venv with spaces/bin/python3.12", "C:\\env\\Scripts\\python.exe", "python3.13.exe"])
def test_literal_python_options_match_sys_executable_controls(tmp_path, executable):
    module = load("test_hermetic_env_guard_v97404")
    sample = tmp_path / "test_python.py"
    sample.write_text("import subprocess\nsubprocess.run([" + repr(executable) + ",'\x2dI','-B','-c','pass'],env={})\n")
    assert module._violations(sample) == []
    sample.write_text("import subprocess\nsubprocess.run([" + repr(executable) + ",'\x2dI','-c','pass'],env={'PYTHONDONTWRITEBYTECODE':'1'})\n")
    assert module._violations(sample) == ["test_python.py:2"]


def test_unrecognized_I_retains_only_prior_environment_check(tmp_path):
    module = load("test_hermetic_env_guard_v97404")
    sample = tmp_path / "test_other.py"
    sample.write_text("import subprocess\nsubprocess.run(['custom-program','-I'],env={'PYTHONDONTWRITEBYTECODE':'1'})\n")
    assert module._violations(sample) == []


def test_python_B_after_script_is_not_an_interpreter_option(tmp_path):
    module = load("test_hermetic_env_guard_v97404")
    sample = tmp_path / "test_late.py"
    sample.write_text("import subprocess,sys\nsubprocess.run([sys.executable,'script.py','-B'],env={})\n")
    assert module._violations(sample) == ["test_late.py:2"]
