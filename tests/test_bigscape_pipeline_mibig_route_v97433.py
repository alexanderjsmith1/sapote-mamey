"""MIBiG anchoring dispatches through the guarded -m launcher."""
from __future__ import annotations
import importlib.util
import sqlite3
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def load():
    name = "bigscape_mibig_route_under_test"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools/bigscape_pipeline.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def argv(tmp_path, *extra):
    return ["--inputs", "synthetic.zip", "--pfam", "synthetic.hmm",
            "--workdir", str(tmp_path / "run"), "--skip-prep", *extra]

def test_mibig_route_uses_guarded_launcher_and_exact_db(tmp_path, monkeypatch):
    module = load()
    monkeypatch.setenv("BIGSCAPE_ENV_BIN", str(tmp_path / "env/bin"))
    calls = []
    db = tmp_path / "run/out/bigscape.db"
    def fake_run(cmd, **kw):
        calls.append((list(map(str, cmd)), kw))
        if any(str(x).endswith("bigscape_launch.sh") for x in cmd):
            db.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(db) as c:
                c.execute("create table run (id integer primary key)")
                c.execute("insert into run values (17)")
    monkeypatch.setattr(module, "run", fake_run)
    module.main(argv(tmp_path, "--mibig-dir", "references", "--mibig-name", "review_local"))
    launch = [x for x in calls if any(t.endswith("bigscape_launch.sh") for t in x[0])]
    assert len(launch) == 1
    cmd, kwargs = launch[0]
    assert "--mibig-dir" in cmd and "--mibig-name" in cmd
    assert cmd[cmd.index("--mibig-name") + 1] == "review_local"
    assert "--include-singletons" in cmd
    assert "-r" not in cmd
    assert kwargs["env"]["PFAM_HMM"] == "synthetic.hmm"
    downstream = [x[0] for x in calls if any(t.endswith("bigscape_known_novel.py") for t in x[0])]
    assert downstream[0][downstream[0].index("--db") + 1] == str(db)
    assert downstream[0][downstream[0].index("--run-id") + 1] == "17"

def test_missing_name_refuses_before_mutation(tmp_path, monkeypatch):
    module = load()
    monkeypatch.setenv("BIGSCAPE_ENV_BIN", str(tmp_path / "env/bin"))
    with pytest.raises(module.PipelineRunError) as e:
        module.main(argv(tmp_path, "--mibig-dir", "references"))
    assert e.value.code == "MIBIG_NAME_REQUIRED"
    assert not (tmp_path / "run").exists()

def test_chunked_mibig_is_held_even_with_run_id(tmp_path, monkeypatch):
    module = load()
    monkeypatch.setenv("BIGSCAPE_ENV_BIN", str(tmp_path / "env/bin"))
    with pytest.raises(module.PipelineRunError) as e:
        module.main(argv(tmp_path, "--mibig-dir", "references", "--mibig-name", "review_local",
                         "--chunk-mibig", "3", "--run-id", "8"))
    assert e.value.code == "CHUNK_MIBIG_UNPROVEN"
    assert not (tmp_path / "run").exists()
