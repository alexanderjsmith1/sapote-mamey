"""v9.7.441 (finding EB3DF1EF_441_bigscape_pipeline_does_not_put_its_own_env_bin_on_path; diff by 283f1f96):
every subprocess the BiG-SCAPE pipeline launches gets the interpreter's bin directory first on PATH,
so a bare `fasttree` beside the env's python resolves without activating the env."""
import importlib.util, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("bigscape_pipeline", ROOT / "tools" / "bigscape_pipeline.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def test_interpreter_bin_is_first_on_path(tmp_path):
    m = _load(); py = tmp_path / "envs/bigscape/bin/python"; py.parent.mkdir(parents=True); py.write_text("")
    env = m.interpreter_env({"PATH": "/usr/bin:/bin"}, executable=str(py))
    assert env["PATH"].split(os.pathsep)[0] == str(py.parent)
    assert env["PATH"].endswith("/usr/bin:/bin")


def test_idempotent_and_dedups(tmp_path):
    m = _load(); py = tmp_path / "bin/python"; py.parent.mkdir(); py.write_text("")
    once = m.interpreter_env({"PATH": f"/usr/bin:{py.parent}"}, executable=str(py))
    twice = m.interpreter_env(once, executable=str(py))
    assert once["PATH"] == twice["PATH"] == f"{py.parent}:/usr/bin"


def test_run_injects_env(monkeypatch, tmp_path):
    m = _load(); seen = {}
    monkeypatch.setattr(m.subprocess, "run", lambda cmd, **kw: seen.update(kw) or 0)
    m.run(["true"])
    assert seen["env"]["PATH"].split(os.pathsep)[0] == os.path.dirname(sys.executable)


def test_existing_env_kw_is_extended_not_replaced(monkeypatch):
    m = _load(); seen = {}
    monkeypatch.setattr(m.subprocess, "run", lambda cmd, **kw: seen.update(kw) or 0)
    m.run(["true"], env={"PFAM_HMM": "/x/Pfam-A.hmm", "PATH": "/usr/bin"})
    assert seen["env"]["PFAM_HMM"] == "/x/Pfam-A.hmm" and seen["env"]["PATH"].startswith(os.path.dirname(sys.executable))
