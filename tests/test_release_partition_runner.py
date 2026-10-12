"""Real offline partition execution and adversarial evidence reuse fixtures."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.fixture
def runner_module(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "tools"))
    return importlib.import_module("_release_partition_runner")


def suite(tmp_path, *, red=False):
    source = tmp_path / "suite"
    source.mkdir()
    (source / "pytest.ini").write_text("[pytest]\ntestpaths = .\n")
    (source / "conftest.py").write_text('''
def pytest_addoption(parser):
    parser.addoption("--run-slow", action="store_true")
    parser.addoption("--run-network", action="store_true")
''')
    (source / "test_a.py").write_text('''
import pytest
@pytest.mark.parametrize("value", ["a::b", "c"])
def test_parameter(value): assert value
@pytest.mark.skip(reason="explicit fixture skip")
def test_skip(): pass
''')
    (source / "test_b.py").write_text('''
def test_subtests(subtests):
    for value in range(2):
        with subtests.test(value=value):
            assert value >= 0
''')
    (source / "test_optional.py").write_text('import pytest\npytest.skip("optional fixture", allow_module_level=True)\n')
    if red:
        (source / "test_a.py").write_text('''
import os
from pathlib import Path
def test_transient_fixture():
    assert Path(os.environ["FIXTURE_READY"]).exists(), "fixture not ready"
''')
    return source


def environment(**extra):
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", **extra)
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTHONOPTIMIZE", None)
    return env


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_runner(module, source, output, env, **kwargs):
    return module.PartitionRunner(source, output, str(Path(sys.executable).absolute()),
                                  files_per_partition=1, env=env, **kwargs)


@pytest.mark.parametrize("outside", [False, True])
def test_runner_package_lookup_follows_child_cwd(runner_module, tmp_path, outside):
    """Source packages stay local while the evidence recorder remains discoverable."""
    source = suite(tmp_path)
    (source / "runner_cwd_probe_only.py").write_text("VALUE = 1\n")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    env = runner_module.test_environment(source, environment())
    command = [sys.executable, "-S", "-c", (
        "import importlib.util,json; "
        "print(json.dumps({name: importlib.util.find_spec(name) is not None "
        "for name in ['runner_cwd_probe_only', '_release_pytest_evidence']}))")]
    result = subprocess.run(command, cwd=unrelated if outside else source,
                            env=env, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {
        "runner_cwd_probe_only": not outside,
        "_release_pytest_evidence": True,
    }


def test_real_stage_resume_relocation_and_tamper_refusals(runner_module, tmp_path):
    m = runner_module
    source = suite(tmp_path); output = tmp_path / "evidence"; env = environment()
    data = make_runner(m, source, output, env).run()
    assert data["status"] == "PASS"
    assert data["totals"] == {"main_counts": {"passed": 3, "skipped": 1}, "main_nodes": 4,
                              "collection_skips": 1, "subtest_counts": {"passed": 2}}
    receipt = output / "partition.json"
    identity = data["binding"]["environment_identity_sha256"]
    assert m.verify_partition_receipt(receipt, source, digest(receipt), identity) == data["totals"]
    assert len(data["partitions"]) == 2
    active_before = [stage["active"] for stage in data["partitions"]]
    resumed = make_runner(m, source, output, env).run(resume=True)
    assert [stage["active"] for stage in resumed["partitions"]] == active_before
    assert all(len(stage["attempts"]) == 1 for stage in resumed["partitions"])
    # Relative evidence references survive a move without pretending commands ran there.
    moved = tmp_path / "moved evidence"
    shutil.move(output, moved)
    receipt = moved / "partition.json"
    assert m.verify_partition_receipt(receipt, source, digest(receipt), identity) == data["totals"]
    original = receipt.read_bytes()
    modified = json.loads(original)
    modified["binding"]["flags"].append("-k")
    receipt.write_text(json.dumps(modified))
    with pytest.raises(ValueError, match="binding differs"):
        m.verify_partition_receipt(receipt, source, digest(receipt), identity)
    receipt.write_bytes(original)
    modified = json.loads(original); modified["partitions"].pop()
    receipt.write_text(json.dumps(modified))
    with pytest.raises(ValueError, match="plan is incomplete"):
        m.verify_partition_receipt(receipt, source, digest(receipt), identity)
    receipt.write_bytes(original)
    stage_ref = data["partitions"][0]["active"]
    attempt = json.loads((moved / stage_ref["path"]).read_text())
    log = moved / attempt["log"]["path"]
    log_original = log.read_bytes(); log.write_bytes(log_original + b"tampered\n")
    with pytest.raises(ValueError, match="log SHA-256"):
        m.verify_partition_receipt(receipt, source, digest(receipt), identity)
    log.write_bytes(log_original)
    with pytest.raises(ValueError, match="environment differs"):
        m.verify_partition_receipt(receipt, source, digest(receipt), "f" * 64)
    (source / "test_a.py").write_text("def test_replaced(): pass\n")
    with pytest.raises(ValueError, match="source or machinery changed"):
        make_runner(m, source, moved, env).run(resume=True)


def test_failed_attempt_requires_explicit_disposition_and_stays_recorded(runner_module, tmp_path):
    m = runner_module
    source = suite(tmp_path, red=True); output = tmp_path / "evidence"
    marker = tmp_path / "external fixture ready"
    env = environment(FIXTURE_READY=str(marker))
    with pytest.raises(ValueError, match="stage failed: partition-0001"):
        make_runner(m, source, output, env).run()
    first = json.loads((output / "partition.json").read_text())
    assert first["status"] == "FAILED"
    failed_ref = first["partitions"][0]["attempts"][0]["receipt"]
    failed_path = output / failed_ref["path"]
    failed_original = failed_path.read_bytes()
    marker.write_text("external synthetic setup now ready")
    with pytest.raises(ValueError, match="explicit retry reason"):
        make_runner(m, source, output, env).run(resume=True)
    result = make_runner(m, source, output, env).run(resume=True,
        retry={"partition-0001": "Synthetic external fixture setup completed; original assertion evidence retained"})
    assert result["status"] == "PASS"
    assert len(result["partitions"][0]["attempts"]) == 2
    assert result["partitions"][0]["attempts"][1]["retry_reason"].startswith("Synthetic external")
    assert failed_path.read_bytes() == failed_original
    failed = json.loads(failed_original)
    assert failed["status"] == "FAILED"
    capture = json.loads((output / failed["capture"]["path"]).read_text())
    assert capture["counts"] == {"failed": 1}


def test_collection_failure_is_terminal_and_has_durable_diagnostics(runner_module, tmp_path):
    m = runner_module
    source = suite(tmp_path); output = tmp_path / "evidence"
    (source / "test_a.py").write_text('raise RuntimeError("synthetic collection failure")\n')
    with pytest.raises(ValueError, match="stage failed: collection"):
        make_runner(m, source, output, environment()).run()
    data = json.loads((output / "partition.json").read_text())
    assert data["status"] == data["collection"]["status"] == "FAILED"
    assert data["partitions"] == []
    attempt = json.loads((output / data["collection"]["attempts"][0]["receipt"]["path"]).read_text())
    assert attempt["watch"]["exit_code"] != 0
    captured = json.loads((output / attempt["capture"]["path"]).read_text())
    assert captured["collection_errors"]


def test_occupied_evidence_root_is_preserved(runner_module, tmp_path):
    source = suite(tmp_path); output = tmp_path / "evidence"; output.mkdir()
    marker = output / "prior"; marker.write_text("preserve me")
    with pytest.raises(FileExistsError):
        make_runner(runner_module, source, output, environment()).run()
    assert marker.read_text() == "preserve me"


def test_forced_memory_stop_retains_missing_nodes_and_needs_a_retry_disposition(runner_module, tmp_path, monkeypatch):
    m = runner_module
    source = suite(tmp_path); output = tmp_path / "evidence"; env = environment()
    real_watch = m.support.run_watched
    def force_stop(command, **kwargs):
        if "--release-evidence" in command and "--collect-only" not in command:
            kwargs["sampler"] = lambda pid: 0 if pid == os.getpid() else kwargs["rss_limit"]
        return real_watch(command, **kwargs)
    monkeypatch.setattr(m.support, "run_watched", force_stop)
    with pytest.raises(ValueError, match="stage failed: partition-0001"):
        make_runner(m, source, output, env).run()
    data = json.loads((output / "partition.json").read_text())
    failed_ref = data["partitions"][0]["attempts"][0]["receipt"]
    failure = json.loads((output / failed_ref["path"]).read_text())
    assert failure["watch"]["stop_reason"] == "MEMORY_LIMIT"
    assert failure["missing_nodes"] == data["partitions"][0]["plan"]["expected_nodes"]
    monkeypatch.setattr(m.support, "run_watched", real_watch)
    with pytest.raises(ValueError, match="explicit retry reason"):
        make_runner(m, source, output, env).run(resume=True)
    result = make_runner(m, source, output, env).run(resume=True,
        retry={"partition-0001": "Forced sampler acceptance fixture removed; original memory stop retained"})
    assert result["status"] == "PASS"
    assert (output / failed_ref["path"]).is_file()


def test_interruption_is_saved_and_never_implicitly_retried(runner_module, tmp_path, monkeypatch):
    m = runner_module
    source = suite(tmp_path); output = tmp_path / "evidence"; env = environment()
    real_watch = m.support.run_watched
    def interrupt(command, **kwargs):
        if "--release-evidence" in command and "--collect-only" not in command:
            raise KeyboardInterrupt()
        return real_watch(command, **kwargs)
    monkeypatch.setattr(m.support, "run_watched", interrupt)
    with pytest.raises(KeyboardInterrupt):
        make_runner(m, source, output, env).run()
    data = json.loads((output / "partition.json").read_text())
    assert data["status"] == "FAILED"
    assert data["partitions"][0]["status"] == "INTERRUPTED"
    attempt = json.loads((output / data["partitions"][0]["attempts"][0]["receipt"]["path"]).read_text())
    assert attempt["status"] == "INTERRUPTED"
    assert attempt["reason"] == "KeyboardInterrupt"
    monkeypatch.setattr(m.support, "run_watched", real_watch)
    with pytest.raises(ValueError, match="explicit retry reason"):
        make_runner(m, source, output, env).run(resume=True)


def test_public_cli_runs_and_independently_verifies_the_profile(runner_module, tmp_path):
    import verify_external_validation_receipt as existing
    source = suite(tmp_path); output = tmp_path / "evidence"
    cli = Path(runner_module.__file__).with_name("release_validate.py")
    env = environment(PYTHONPATH=str(Path(existing.__file__).parent))
    def command(*args):
        return subprocess.run([str(Path(sys.executable).absolute()), str(cli), *args],
                              env=env, capture_output=True, text=True, timeout=60)
    result = command("partition", "--source", str(source), "--out", str(output), "--files-per-partition", "1")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "RELEASE PARTITIONS: PASS" in result.stdout
    receipt = output / "partition.json"
    verified = command("verify", "--source", str(source), "--receipt", str(receipt),
                       "--sha256", digest(receipt), "--out", str(tmp_path / "fresh verification environment"))
    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert "VERIFIED — 4 main nodes" in verified.stdout


def test_measured_red_baseline_cannot_be_reused_as_final_validation(runner_module, tmp_path):
    m = runner_module
    source = suite(tmp_path, red=True); output = tmp_path / "baseline evidence"
    env = environment(FIXTURE_READY=str(tmp_path / "absent synthetic fixture"))
    data = make_runner(m, source, output, env, baseline=True).run()
    assert data["status"] == "MEASURED"
    assert data["schema"] == "sapote-mamey.partitioned-pytest-baseline.v1"
    assert data["totals"]["main_counts"] == {"failed": 1, "passed": 1}
    assert data["partitions"][0]["status"] == "MEASURED"
    receipt = output / "partition.json"
    identity = data["binding"]["environment_identity_sha256"]
    assert m.verify_partition_receipt(receipt, source, digest(receipt), identity, baseline=True) == data["totals"]
    with pytest.raises(ValueError, match="not a PASS"):
        m.verify_partition_receipt(receipt, source, digest(receipt), identity)
    with pytest.raises(ValueError, match="resume schema mismatch"):
        make_runner(m, source, output, env).run(resume=True)
    before = [s["active"] for s in data["partitions"]]
    resumed = make_runner(m, source, output, env, baseline=True).run(resume=True)
    assert [s["active"] for s in resumed["partitions"]] == before


def test_baseline_setup_errors_still_block_measurement(runner_module, tmp_path):
    source = suite(tmp_path); output = tmp_path / "baseline evidence"
    (source / "test_a.py").write_text('''
import pytest
@pytest.fixture
def broken(): raise RuntimeError("setup not admitted")
def test_bad(broken): pass
''')
    with pytest.raises(ValueError, match="stage failed: partition-0001"):
        make_runner(runner_module, source, output, environment(), baseline=True).run()
    data = json.loads((output / "partition.json").read_text())
    assert data["status"] == "FAILED"
