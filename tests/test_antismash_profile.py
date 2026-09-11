import inspect, json, subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
GUARD = ROOT / "tools" / "check_antismash_profile.py"

def _mk(tmp, strain, profile):
    d = tmp / strain / "package"; d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"strain": strain, "antismash_profile": profile}))

def _run(tmp):
    return subprocess.run([sys.executable, str(GUARD), str(tmp)], capture_output=True, text=True).returncode

def test_guard_flags_mixed(tmp_path):
    _mk(tmp_path, "A", "strict"); _mk(tmp_path, "B", "relaxed"); assert _run(tmp_path) == 1

def test_guard_flags_unknown(tmp_path):
    _mk(tmp_path, "A", "strict"); _mk(tmp_path, "B", "unknown"); assert _run(tmp_path) == 1

def test_guard_passes_uniform_known(tmp_path):
    _mk(tmp_path, "A", "relaxed"); _mk(tmp_path, "B", "relaxed"); assert _run(tmp_path) == 0

def test_run_cli_threads_profile():
    import mamey.cli as cli
    assert "antismash_profile" in inspect.signature(cli.run_one_strain).parameters
