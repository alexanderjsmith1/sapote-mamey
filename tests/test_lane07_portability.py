"""Bounded portability regressions; fixtures never install packages or run biology."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def mini_bundle(tmp_path):
    root = tmp_path / "bundle with spaces"
    (root / "mamey").mkdir(parents=True)
    shutil.copyfile(ROOT / "mamey_run.py", root / "mamey_run.py")
    (root / "BUILD_STAMP.txt").write_text("version=9.7.452\nbuild=fixture\n")
    (root / "mamey" / "__init__.py").write_text('__version__="1.9.176"\nBUNDLE_VERSION="9.7.452"\n')
    (root / "mamey" / "cli.py").write_text('def main():\n    print("CURRENT")\n    return 0\n')
    return root


def run_bundle(root, flag="-B"):
    env = dict(os.environ)
    env.pop("PYTHONPYCACHEPREFIX", None)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    args = [sys.executable]
    if flag:
        args.append(flag)
    else:
        env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([*args, "mamey_run.py"], cwd=root, env=env,
                          capture_output=True, text=True, timeout=15)


@pytest.mark.parametrize("flag", ["-B", None])
def test_disabled_bytecode_leaves_clean_tree_unchanged(tmp_path, flag):
    root = mini_bundle(tmp_path)
    before = snapshot(root)
    result = run_bundle(root, flag)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "CURRENT"
    assert snapshot(root) == before
    assert not (root / "mamey" / "__pycache__").exists()


def test_disabled_bytecode_refuses_untrusted_cache_without_purge(tmp_path):
    root = mini_bundle(tmp_path)
    cache = root / "mamey" / "__pycache__"
    cache.mkdir()
    (cache / "foreign.pyc").write_bytes(b"preserve untrusted evidence")
    before = snapshot(root)
    result = run_bundle(root)
    assert result.returncode == 2
    assert "BYTECODE_WRITES_DISABLED" in result.stderr
    assert "CURRENT" not in result.stdout
    assert snapshot(root) == before


def test_disabled_bytecode_preserves_source_drift_marker(tmp_path):
    root = mini_bundle(tmp_path)
    cache = root / "mamey" / "__pycache__"
    cache.mkdir()
    (cache / ".sapote_cut").write_text("version=9.7.452\nbuild=fixture\nsource=old\n")
    (cache / "foreign.pyc").write_bytes(b"do not purge")
    before = snapshot(root)
    result = run_bundle(root)
    assert result.returncode == 2
    assert "SOURCE_DRIFT_DETECTED" in result.stderr
    assert snapshot(root) == before


def bootstrap_fixture(tmp_path):
    root = tmp_path / "selected source"
    root.mkdir()
    shutil.copyfile(ROOT / "bootstrap.sh", root / "bootstrap.sh")
    (root / "pyproject.toml").write_text('[project]\nrequires-python=">=3.12"\n')
    caller = tmp_path / "unrelated checkout"
    caller.mkdir()
    (caller / "offline wheels").mkdir()
    shim = tmp_path / "python shim"
    shim.write_text("#!" + sys.executable + "\n" +
        "import json,os,sys\n" +
        "with open(os.environ['CALL_LOG'],'a') as out: out.write(json.dumps({'args':sys.argv[1:],'cwd':os.getcwd()})+'\\n')\n" +
        "if sys.argv[1:]==['--version']: print('Python 3.12.14')\n" +
        "if sys.argv[1:2]==['-c'] and os.environ.get('FAKE_OLD')=='1': sys.exit(2)\n")
    shim.chmod(0o755)
    log = tmp_path / "calls.jsonl"
    env = dict(os.environ, PYTHON=str(shim), CALL_LOG=str(log))
    return root, caller, log, env


def test_bootstrap_anchors_editable_target_and_relative_wheels(tmp_path):
    root, caller, log, env = bootstrap_fixture(tmp_path)
    result = subprocess.run(["bash", str(root / "bootstrap.sh"), "--wheels", "offline wheels"],
                            cwd=caller, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    installs = [r for r in calls if r["args"][:4] == ["-m", "pip", "--isolated", "install"]]
    assert len(installs) == 2
    assert all(Path(r["cwd"]) == root for r in installs)
    assert all(str(caller / "offline wheels") in r["args"] for r in installs)
    assert all("--no-index" in r["args"] for r in installs)


def test_bootstrap_old_python_refuses_before_pip(tmp_path):
    root, caller, log, env = bootstrap_fixture(tmp_path)
    env["FAKE_OLD"] = "1"
    result = subprocess.run(["bash", str(root / "bootstrap.sh")], cwd=caller, env=env,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 2
    assert "Python 3.12+ required" in result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert not any(r["args"][:2] == ["-m", "pip"] for r in calls)


def load_audit():
    spec = importlib.util.spec_from_file_location("audit_lane07", ROOT / "tools/audit_documents_wheelhouse.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("requirement", ["pypdf @ https://example.invalid/a.whl", "https://example.invalid/a.whl", "pypdf; python_version < '4'", "pypdf @ file:///outside/a.whl", "../local.whl", "--extra-index-url https://example.invalid"])
def test_offline_profile_rejects_non_named_version_requirements(tmp_path, requirement):
    module = load_audit()
    profile = tmp_path / "profile.txt"
    profile.write_text(requirement + "\n")
    with pytest.raises(ValueError):
        module.read_profile(profile)


def test_offline_joint_conflict_fails_even_when_rows_pass(tmp_path):
    module = load_audit()
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    calls = []
    def fake_run(command, **kwargs):
        assert kwargs["env"]["PIP_CONFIG_FILE"] == os.devnull
        calls.append(command)
        joint = "pypdf>=5" in command and "pillow>=10" in command
        return SimpleNamespace(returncode=int(joint), stdout="joint conflict" if joint else "would install", stderr="")
    report = module.audit_requirements(python=Path(sys.executable), wheelhouse=wheels,
        requirements=["pypdf>=5", "pillow>=10"], runner=fake_run)
    assert report["status"] == "FAIL"
    assert report["joint_resolution"]["status"] == "FAIL"
    assert report["failed_resolution"] == []
    assert all("--ignore-installed" in c for c in calls)
    assert all("--isolated" in c for c in calls)


def test_offline_empty_pool_cannot_pass_from_installed_package(tmp_path):
    module = load_audit()
    wheels = tmp_path / "empty wheels"
    wheels.mkdir()
    report = module.audit_requirements(python=Path(sys.executable), wheelhouse=wheels,
        requirements=["PyYAML>=6,<7"])
    assert report["status"] == "FAIL"
    assert report["failed_resolution"] == ["pyyaml"]


def test_placement_requires_executable_file(tmp_path, monkeypatch):
    source = ast.parse((ROOT / "mamey/cli.py").read_text())
    node = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "_placement_and_r_companion_status")
    monkeypatch.setitem(sys.modules, "mamey.workspace_root", SimpleNamespace(workspace_root=lambda: tmp_path))
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "cli.py", "exec"), namespace)
    directory = tmp_path / "bin"
    directory.mkdir()
    (directory / "blastdbcmd").mkdir()
    (directory / "mafft").write_text("nonexecutable")
    env = {"SAPOTE_WORKSPACE_ROOT": str(tmp_path), "BLAST_BIN":str(directory), "MAFFT_BIN":str(directory), "PATH":str(directory)}
    found, missing = namespace[node.name](env)
    assert "blastdbcmd" in missing and "mafft" in missing
    (directory / "mafft").chmod(0o755)
    found, missing = namespace[node.name](env)
    assert "mafft" in found and "blastdbcmd" in missing


@pytest.mark.parametrize("version, expected", [((3,9), "fail"), ((3,11), "fail"), ((3,12), "ok"), ((3,14), "ok")])
def test_doctor_python_gate_matches_package_minimum(version, expected):
    source = ast.parse((ROOT / "mamey/cli.py").read_text())
    node = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "doctor_command")
    index = next(i for i,n in enumerate(node.body) if isinstance(n, ast.Assign) and any(isinstance(t,ast.Tuple) and any(isinstance(e,ast.Name) and e.id == "major" for e in t.elts) for t in n.targets))
    block = ast.Module(body=node.body[index:index+2], type_ignores=[])
    ns = {"sys":SimpleNamespace(version_info=version),"ok":[],"warn":[],"fail":[]}
    exec(compile(block, "cli.py", "exec"), ns)
    assert bool(ns[expected])
    assert not ns["warn"]


def test_audit_api_rejects_remote_requirement_before_spawning(tmp_path):
    module = load_audit()
    def forbidden(*args, **kwargs):
        pytest.fail("unsafe requirement reached subprocess")
    with pytest.raises(ValueError, match="PROFILE_NAMED_VERSION_REQUIREMENT_ONLY"):
        module.audit_requirements(python=Path(sys.executable), wheelhouse=tmp_path,
            requirements=["pypdf @ https://example.invalid/pypdf.whl"], runner=forbidden)


def test_disabled_bytecode_bound_cache_can_be_read_without_rewriting(tmp_path):
    root = mini_bundle(tmp_path)
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env.pop("PYTHONPYCACHEPREFIX", None)
    first = subprocess.run([sys.executable, "mamey_run.py"], cwd=root, env=env,
                           capture_output=True, text=True, timeout=15)
    assert first.returncode == 0, first.stderr
    before = snapshot(root)
    result = run_bundle(root)
    assert result.returncode == 0, result.stderr
    assert snapshot(root) == before


def test_disabled_bytecode_foreign_cut_refused_without_mutation(tmp_path):
    root = mini_bundle(tmp_path)
    cache = root / "mamey" / "__pycache__"
    cache.mkdir()
    (cache / ".sapote_cut").write_text("version=9.7.451\nbuild=foreign\nsource=old\n")
    (cache / "foreign.pyc").write_bytes(b"preserve foreign evidence")
    before = snapshot(root)
    result = run_bundle(root)
    assert result.returncode == 2
    assert "FOREIGN_BYTECODE_REFUSED" in result.stderr
    assert snapshot(root) == before
