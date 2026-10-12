"""Execute the real cut shell against tiny synthetic tools and source fixtures.

Real validation/manifest code runs. Gate stubs only record invocation or inject a
failure; the package stub writes an explicit fixture marker, never a release ZIP.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("partition_manifest_fixture", ROOT / "tests/test_release_partition_manifest.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def fake_cut(tmp_path, *, mode="partitioned", failure=None, tamper=False, red_final=False, skip_tests=False, context=False, import_hold=False):
    source = fixtures.source_fixture(tmp_path)
    tools = source / "tools"; tools.mkdir()
    output = tmp_path / "output"
    ready = tmp_path / "gate_ready"
    events = tmp_path / "gate_events.txt"
    # This fixture tests gate order. The separate convergence fixture tests that
    # the new subset profile carries --run-slow and --run-network.
    consumer = source / "tests/test_consumer.py"
    text = consumer.read_text()
    text = "\n".join(line for line in text.splitlines() if "assert request.config.getoption" not in line) + "\n"
    consumer.write_text(text)
    if red_final:
        (source / "tests/test_unrelated_failure.py").write_text('def test_bad(): assert False, "persistent final failure"\n')
    (source / "CHANGELOG.md").write_text("# v8.8.8 fixture\n\n- **Fixture** synthetic cut only.\n")
    (source / "README.md").write_text("fixture\n")
    # This is a tiny release-machinery fixture, not a partial production bundle.
    # Copy the owned machinery explicitly: unrelated research tools would need
    # their full mamey dependencies and belong in the real-source import audit.
    fixture_tools = [
        "release_cut.sh", "release_validate.py", "release_workflow.py",
        "gen_release_manifest.py", "_release_import_smoke.py",
        "_release_import_worker.py", "_release_partition_runner.py",
        "_release_partitions.py", "_release_pytest_evidence.py",
        "_release_validation.py", "_release_workflow.py",
    ]
    for name in fixture_tools:
        shutil.copy2(ROOT / "tools" / name, tools / name)
    (tools / "cut_preflight.sh").write_text('sapote_assert_no_review_root(){ return 0; }\nsapote_purge_cut_bytecode(){ return 0; }\n')
    logger = '''
import os,sys
from pathlib import Path
def record_gate():
    name=Path(__file__).name
    with Path(os.environ["GATE_LOG"]).open("a") as stream:
        stream.write(name+" "+" ".join(sys.argv[1:])+"\\n")
    if os.environ.get("FAIL_GATE")==name and not Path(os.environ["GATE_READY"]).exists():
        raise SystemExit("injected gate failure: "+name)
'''
    generic = ["render_bootstrap_contract.py", "gen_command_catalog.py", "generate_deliverables_menu.py",
               "gen_tools_inventory.py", "check_module_accretion.py", "check_release_manifest.py", "verify_release_identity.py"]
    for name in generic:
        (tools / name).write_text(logger + '\nif __name__ == "__main__":\n    record_gate(); print("PASS")\n')
    (tools / "sync_wiki_mirrors.py").write_text("MIRRORS = {}\n")
    (tools / "sync_version.py").write_text(logger + '''
def sync_build_stamp_patch(check=False): return None
if __name__ == "__main__":
    record_gate(); print("OK")
''')
    (tools / "rewrite_release_identity.py").write_text(logger + '''
if __name__ == "__main__":
    record_gate()
    if "--check" not in sys.argv:
        Path("BUILD_STAMP.txt").write_text("build="+sys.argv[2]+"\\n")
''')
    (tools / "repo_health.py").write_text(logger + '''
if __name__ == "__main__":
    record_gate()
    if "--strict" in sys.argv and os.environ.get("TAMPER_SOURCE")=="1":
        Path("README.md").write_text("source changed after final validation\\n")
    print("PASS: no blocking issues")
''')
    (tools / "tracked_file_policy.py").write_text('''
from pathlib import Path
import sys
import zipfile
def tracked_paths(root):
    return ["./"+path.relative_to(root).as_posix() for path in sorted(root.rglob("*"))
            if path.is_file() and path.name not in {"TIER_MANIFEST.txt","SOURCE_CHECKSUMS_SHA256.txt"}
            and "__pycache__" not in path.parts and ".pytest_cache" not in path.parts]
if __name__ == "__main__":
    print("# fixture manifest")
    print("\\n".join(tracked_paths(Path.cwd())))
''')
    (tools / "make_public_tier.sh").write_text('''#!/usr/bin/env bash
set -eu
printf 'PACKAGE\n' >> "$GATE_LOG"
python3 - "$2" "$3" <<'ZIP'
from pathlib import Path
import sys,zipfile
source=Path(sys.argv[1]);out=Path(sys.argv[2])
with zipfile.ZipFile(out/'fixture.zip','w') as archive:
    for path in sorted(source.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            archive.write(path,path.relative_to(source))
ZIP
printf 'parity gate: OK\n'
''')
    # Copy only the current helpers needed by this tiny source fixture.
    # No campaign path, extracted baseline or unbound installed package is used.
    for name in ['tools/_console.py','tools/verify_external_validation_receipt.py',
                 'tools/check_tier_parity.py','tools/tier_vocabulary.py','mamey/ziputil.py']:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,target)
    if import_hold:
        (tools/'held_import.py').write_text('raise SystemExit("planted import hold")\n')
    env = dict(os.environ, PYTHONPATH=str(tools), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               PYTHONDONTWRITEBYTECODE="1", GATE_LOG=str(events), GATE_READY=str(ready), RELEASE_DATE="20261009")
    env["PATH"] = str(Path(sys.executable).absolute().parent) + os.pathsep + env["PATH"]
    env.pop("PYTEST_ADDOPTS", None); env.pop("PYTHONOPTIMIZE", None)
    if mode is not None:
        env["RELEASE_PYTEST_MODE"] = mode
    else:
        env.pop("RELEASE_PYTEST_MODE", None)
    if failure:
        env["FAIL_GATE"] = failure
    if tamper:
        env["TAMPER_SOURCE"] = "1"
    command = ["bash", str(tools / "release_cut.sh"), "8.8.8", str(source), str(output), "a"]
    if skip_tests:
        command.append("--skip-tests")
    result = subprocess.run(command, cwd=tmp_path, env=env, text=True, capture_output=True, timeout=180)
    if context:
        return result, output, source, env, command, ready
    return result, output, events.read_text() if events.exists() else "", source


def test_partition_cut_preserves_all_post_test_gates_and_only_packages_after_final_binding(tmp_path):
    result, output, events, source = fake_cut(tmp_path)
    assert (source/"TIER_MANIFEST.txt").stat().st_mode & 0o777 == 0o644
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Release stage: baseline" in result.stdout
    assert "Release stage: final" in result.stdout
    assert "Release stage: prepackage" in result.stdout
    assert "Release stage: imports-precheck" in result.stdout
    assert "Release stage: imports-final" in result.stdout
    assert json.loads((output/'baseline/partition.json').read_text())['status'] == 'MEASURED'
    assert json.loads((output/'final/partition.json').read_text())['status'] == 'PASS' 
    with zipfile.ZipFile(output / "packages/code/fixture.zip") as archive:
        assert archive.read("CHANGELOG.md").startswith(b"# v8.8.8 fixture")
        assert (archive.getinfo("TIER_MANIFEST.txt").external_attr >> 16) & 0o777 == 0o644
    workflow = json.loads((output / "workflow.json").read_text())
    assert workflow['status'] == 'STAGES_COMPLETE'
    assert [stage['name'] for stage in workflow['stages']][-1] == 'artifact'
    artifact = json.loads((output/'artifact/artifact.json').read_text())
    assert artifact['status'] == 'EXTRACTED_SUITE_PASS' 
    assert artifact['import_safety']['status'] == 'PASS'
    assert events.index("repo_health.py --strict") < events.index("PACKAGE")
    for name in ["render_bootstrap_contract.py --check", "gen_command_catalog.py --check",
                 "generate_deliverables_menu.py --check", "gen_tools_inventory.py --check",
                 "gen_tools_inventory.py --maintenance --check",
                 "rewrite_release_identity.py", "verify_release_identity.py --strict-membership"]:
        assert name in events
    event_lines = events.splitlines()
    ordinary_inventory_gate = event_lines.index("gen_tools_inventory.py --check")
    maintenance_inventory_gate = event_lines.index("gen_tools_inventory.py --maintenance --check")
    assert ordinary_inventory_gate < maintenance_inventory_gate < event_lines.index("PACKAGE")
    assert (output / "final/partition.json").is_file()
    assert not list(output.glob("pytest_full_suite_*.log"))  # no invented monolithic log


def test_complete_import_hold_stops_before_baseline_tests_and_packaging(tmp_path):
    result, output, events, _ = fake_cut(tmp_path, import_hold=True)
    assert result.returncode != 0
    assert 'PACKAGE' not in events and not (output/'baseline').exists()
    workflow=json.loads((output/'workflow.json').read_text())
    stage=next(row for row in workflow['stages'] if row['name']=='imports-precheck')
    assert stage['status']=='FAILED'
    current=json.loads((output/'imports-precheck/current.json').read_text())
    assert current['status']=='HOLD'
    receipt=json.loads((output/'imports-precheck'/current['receipt']['path']).read_text())
    held=[row for order in receipt['orders'] for row in order['results'] if row['path']=='tools/held_import.py']
    assert held and all(row['exception_type']=='SystemExit' for row in held)


@pytest.mark.parametrize("options", [
    {"red_final": True}, {"failure": "repo_health.py"}, {"tamper": True},
])
def test_red_unbound_or_failed_gate_cannot_build_a_package(tmp_path, options):
    result, output, events, _ = fake_cut(tmp_path, **options)
    assert result.returncode != 0
    assert "PACKAGE" not in events
    assert not list(output.rglob("*.zip")) if output.exists() else True


def test_default_monolithic_cut_remains_available_and_keeps_its_real_log(tmp_path):
    result, output, events, _ = fake_cut(tmp_path, mode=None)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PACKAGE" in events
    assert (output / "code/fixture.zip").is_file()
    assert list(output.glob("pytest_full_suite_*.log"))
    assert not list(output.glob("partition_final_*"))


def test_partition_mode_cannot_be_combined_with_external_skip_tests(tmp_path):
    result, output, events, _ = fake_cut(tmp_path, skip_tests=True)
    assert result.returncode != 0
    assert "cannot use --skip-tests" in result.stderr
    assert events == ""
    assert not list(output.rglob("*.zip")) if output.exists() else True


def test_failed_real_cut_gate_resumes_without_repeating_source_suites(tmp_path):
    result, output, source, env, command, ready = fake_cut(tmp_path, failure='repo_health.py', context=True)
    assert result.returncode != 0
    before = json.loads((output/'workflow.json').read_text())
    final_bytes = (output/'final/partition.json').read_bytes()
    attempts = {row['name']: row for row in before['stages']}
    assert attempts['post-gates']['status'] == 'FAILED'
    assert attempts['baseline']['status'] == attempts['final']['status'] == 'PASS'
    failed = attempts['post-gates']['attempts'][0]['receipt']
    failed_bytes = (output/failed['path']).read_bytes()
    ready.write_text('Synthetic external gate prerequisite repaired; source unchanged\n')
    resumed_env = dict(env, RELEASE_WORKFLOW_RESUME='1',
        RELEASE_WORKFLOW_RETRY='post-gates=Fixture gate prerequisite repaired; preserve original failure')
    resumed = subprocess.run(command, cwd=tmp_path, env=resumed_env, text=True, capture_output=True, timeout=180)
    assert resumed.returncode == 0, resumed.stdout+resumed.stderr
    after = json.loads((output/'workflow.json').read_text())
    assert after['status'] == 'STAGES_COMPLETE'
    states = {row['name']:row for row in after['stages']}
    assert len(states['post-gates']['attempts']) == 2
    assert states['baseline']['active'] == attempts['baseline']['active']
    assert states['final']['active'] == attempts['final']['active']
    assert (output/'final/partition.json').read_bytes() == final_bytes
    assert (output/failed['path']).read_bytes() == failed_bytes
    # Every original source suite attempt remains singular.
    assert len(states['baseline']['attempts']) == len(states['final']['attempts']) == 1
    assert after['context']['seal_status'] == 'NOT_RUN'
    assert after['context']['import_safety'] == 'REQUIRED_COMPLETE_SOURCE_AND_ARTIFACT'


def test_occupied_seal_target_is_refused_before_any_work(tmp_path):
    target = tmp_path/'occupied.zip';target.write_text('owner evidence')
    source = ROOT
    env = dict(os.environ, PYTHONPATH=str(ROOT/'tools'),
               PYTHONDONTWRITEBYTECODE='1')
    output = tmp_path/'forbidden-output'
    result = subprocess.run([sys.executable, str(ROOT/'tools/release_workflow.py'), 'cut',
        '--source', str(source), '--out', str(output), '--version','9.7.450', '--date','20261010',
        '--seal-target',str(target)],env=env,text=True,capture_output=True,timeout=10)
    assert result.returncode != 0 and 'seal target is occupied' in result.stderr
    assert target.read_text() == 'owner evidence' and not output.exists()


def test_full_cut_root_can_be_independently_verified_without_stage_execution(tmp_path):
    import hashlib
    result, output, source, env, command, _ = fake_cut(tmp_path, context=True)
    assert result.returncode == 0, result.stdout+result.stderr
    root = output/'workflow.json';before = root.read_bytes()
    gate_log = Path(env['GATE_LOG']);events_before = gate_log.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    verification = tmp_path/'independent-verification'
    # The shell cut selects PATH python3. Verify that exact invocation locator;
    # sys.executable can be the distinct python alias in the same virtualenv.
    # Environment receipts intentionally bind aliases rather than conflating them.
    cut_python = shutil.which('python3', path=env['PATH'])
    assert cut_python == str(Path(sys.executable).absolute().parent / 'python3')
    checked = subprocess.run([sys.executable, str(source/'tools/release_workflow.py'), 'verify',
        '--source',str(source), '--out',str(output), '--sha256',digest,
        '--python',cut_python, '--admission',str(verification)],
        env=env,cwd=tmp_path,text=True,capture_output=True,timeout=30)
    assert checked.returncode == 0, checked.stdout+checked.stderr
    assert 'VERIFIED_STAGES' in checked.stdout
    assert root.read_bytes() == before and gate_log.read_bytes() == events_before
    receipt = json.loads((verification/'workflow-verification.json').read_text())
    assert receipt['context']['seal_status'] == 'NOT_RUN'
    assert receipt['context']['import_safety'] == 'REQUIRED_COMPLETE_SOURCE_AND_ARTIFACT'


def test_workflow_environment_normalizes_shell_transport_but_binds_meaningful_settings(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'tools'))
    from release_workflow import workflow_environment
    monkeypatch.setenv('SHLVL','7');monkeypatch.setenv('OLDPWD','/previous/shell/location')
    monkeypatch.setenv('_','/path/to/bash');monkeypatch.setenv('PWD','/stale/shell/location')
    first = workflow_environment(sys.executable, tmp_path)
    monkeypatch.setenv('PATH',first['PATH'])
    assert workflow_environment(sys.executable,tmp_path) == first
    assert first['PATH'].split(os.pathsep).count(str(Path(sys.executable).absolute().parent)) == 1
    monkeypatch.setenv('SHLVL','8');monkeypatch.setenv('_','/different/python')
    assert workflow_environment(sys.executable, tmp_path) == first
    assert first['PWD'] == str(tmp_path.resolve())
    monkeypatch.setenv('SAPOTE_WORKSPACE_ROOT', '/explicit/new/workspace')
    assert workflow_environment(sys.executable, tmp_path) != first
