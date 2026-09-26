"""intake_harness must exit non-zero when any input it attempted failed.

Before v9.7.443 main() returned None, so a batch whose every input was RUN_FAILED exited 0 --
indistinguishable, to a shell, a scheduler or a calling agent, from a clean batch. The per-input
lines were printed, but nothing that reads an exit status could see them.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools" / "intake_harness.py"
FIXTURE = ROOT / "examples" / "test_data" / "smoke_antismash_small.zip"


def _harness():
    spec = importlib.util.spec_from_file_location("intake_harness_under_test", HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows(*statuses):
    return [{"strain": f"S{i}", "status": s} for i, s in enumerate(statuses)]


def test_all_ok_is_zero():
    status, text = _harness()._batch_exit_status(_rows("OK", "OK"))
    assert status == 0
    assert "RUN_FAILED 0" in text and "BATCH_INCOMPLETE" not in text


def test_any_run_failed_is_one_and_names_the_input():
    status, text = _harness()._batch_exit_status(_rows("OK", "RUN_FAILED"))
    assert status == 1
    assert "BATCH_INCOMPLETE" in text and "S1" in text and "--resume" in text


def test_every_input_failed_is_one():
    assert _harness()._batch_exit_status(_rows("RUN_FAILED", "RUN_FAILED"))[0] == 1


def test_needs_antismash_is_triage_not_failure():
    status, text = _harness()._batch_exit_status(_rows("OK", "NEEDS_ANTISMASH"))
    assert status == 0
    assert "NEEDS_ANTISMASH 1" in text


def test_empty_pass_is_zero():
    """A --resume pass that skips everything attempts nothing and has nothing to report."""
    assert _harness()._batch_exit_status([])[0] == 0


def test_real_batch_with_a_broken_input_exits_one(tmp_path):
    """End to end, on a copy of the shipped generic fixture whose GenBank records are corrupt.

    Both records are replaced: with only the region record corrupt the engine still ran OK from
    the full-contig record, so that is not a reliable failure."""
    broken = tmp_path / "inputs" / "broken_records.zip"
    broken.parent.mkdir()
    with zipfile.ZipFile(FIXTURE) as src, zipfile.ZipFile(broken, "w") as dst:
        for info in src.infolist():
            data = src.read(info)
            if info.filename.endswith(".gbk"):
                data = b"LOCUS       broken\nthis is not a GenBank record\n//\n"
            dst.writestr(info, data)
    out = tmp_path / "out"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"}
    result = subprocess.run(
        [sys.executable, str(HARNESS), "--inputs", str(broken.parent), "--outdir", str(out),
         "--registry", str(out / "reg.csv"), "--metrics", str(out / "met.csv")],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    assert "RUN_FAILED" in result.stdout, result.stdout + result.stderr
    assert result.returncode == 1, result.stdout + result.stderr
    assert "BATCH_INCOMPLETE" in result.stdout
