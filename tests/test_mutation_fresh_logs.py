"""Admission only; no mutation workflow or prior-file deletion."""
import importlib.util
import os
from pathlib import Path
import sys
import pytest
SCRIPT = Path(__file__).resolve().parents[1] / 'tools/gate_mutation_probe.py'
spec = importlib.util.spec_from_file_location('isolated_fresh_mutation_logs', SCRIPT)
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)

@pytest.fixture
def case(tmp_path, monkeypatch):
    root = tmp_path / 'source'; (root / 'mamey').mkdir(parents=True)
    (root / 'mamey/validate.py').write_text('SOFTWARE_MARKER')
    table = tmp_path / 'selected.tsv'
    table.write_text('id\tkind\tsource\told\tnew\ttests\tconsequence\nSOFTWARE\tguard\topaque.py\told\tnew\t\tsoftware-only\n')
    parent = tmp_path / 'reports'; parent.mkdir(); output = parent / 'result.tsv'
    calls = []
    def stub(root, row, logs):
        calls.append(str(logs))
        return dict(row, classification='UNPAIRED', mutation_status='NOT_RUN', remediation='STUB_ONLY', exit_code='', log=str(logs / 'SOFTWARE.baseline.log'))
    monkeypatch.setattr(tool, 'run_one', stub)
    monkeypatch.setattr(tool, 'inventory', lambda root: [])
    monkeypatch.setattr(tool, 'inventory_results', lambda *args: [])
    def forbid(*args, **kwargs): pytest.fail('mutation/deletion workflow reached')
    monkeypatch.setattr(tool.subprocess, 'run', forbid)
    monkeypatch.setattr(tool.shutil, 'copytree', forbid)
    monkeypatch.setattr(Path, 'unlink', forbid)
    monkeypatch.setattr(sys, 'argv', ['gate_mutation_probe', '--source-root', str(root), '--mutation-table', str(table), '--output', str(output)])
    return root, table, output, parent / 'probe_logs', calls

@pytest.mark.parametrize('occupied', ['empty-directory', 'foreign-junit', 'junit-symlink', 'log-hardlink', 'directory-symlink', 'dangling-symlink', 'ordinary-file'])
def test_preexisting_logs_are_refused_without_touching_evidence(case, tmp_path, occupied, capsys):
    root, table, output, logs, calls = case
    output.write_text('PRIOR_SINGLE_LINK_REPORT')
    foreign = tmp_path / 'foreign-evidence'; foreign.write_text('FOREIGN_EVIDENCE_BYTES')
    if occupied in {'empty-directory', 'foreign-junit', 'junit-symlink', 'log-hardlink'}:
        logs.mkdir()
        if occupied == 'foreign-junit': (logs / 'SOFTWARE.baseline.xml').write_text('FOREIGN_PRIOR_JUNIT')
        elif occupied == 'junit-symlink': (logs / 'SOFTWARE.baseline.xml').symlink_to(foreign)
        elif occupied == 'log-hardlink': os.link(foreign, logs / 'SOFTWARE.baseline.log')
    elif occupied == 'directory-symlink':
        directory = tmp_path / 'foreign-log-directory'; directory.mkdir(); (directory / 'SOFTWARE.baseline.xml').write_text('FOREIGN_PRIOR_JUNIT')
        logs.symlink_to(directory, target_is_directory=True)
    elif occupied == 'dangling-symlink': logs.symlink_to(tmp_path / 'absent-logs', target_is_directory=True)
    else: logs.write_text('FOREIGN_FILE_AT_LOG_PATH')
    originals = [table, root / 'mamey/validate.py', output, foreign]
    if logs.is_dir(): originals += [p for p in logs.iterdir() if p.is_file()]
    elif logs.is_file(): originals.append(logs)
    before = {p: p.read_bytes() for p in originals}
    identity = logs.lstat()
    refused = None
    try: tool.main()
    except SystemExit as error: refused = error
    assert refused is not None and refused.code == 2
    assert 'MUTATION_LOGS_EXISTS' in capsys.readouterr().err
    assert not calls
    assert logs.lstat().st_ino == identity.st_ino
    assert all(p.read_bytes() == data for p, data in before.items())

@pytest.mark.parametrize('existing_report', [False, True], ids=['fresh-report', 'replace-unrelated-report'])
def test_fresh_logs_keep_existing_public_paths_and_report_behavior(case, existing_report):
    root, table, output, logs, calls = case
    if existing_report: output.write_text('PRIOR_SINGLE_LINK_REPORT')
    before = table.read_bytes()
    assert tool.main() == 0
    assert calls == [str(logs)] and logs.is_dir()
    assert str(logs / 'SOFTWARE.baseline.log') in output.read_text()
    assert table.read_bytes() == before


@pytest.mark.parametrize("kind", ["file", "symlink", "dangling"])
def test_direct_helper_refuses_existing_logs_without_workflow(tmp_path, monkeypatch, kind):
    root = tmp_path / "source"; root.mkdir(); logs = tmp_path / "logs"; logs.mkdir()
    retained = tmp_path / "retained"; retained.write_bytes(b"keep")
    leaf = logs / "SOFTWARE.baseline.xml"
    if kind == "file": leaf.write_bytes(b"foreign")
    elif kind == "symlink": leaf.symlink_to(retained)
    else: leaf.symlink_to(tmp_path / "missing")
    before = leaf.lstat().st_ino
    monkeypatch.setattr(tool.shutil, "copytree", lambda *a, **k: pytest.fail("copy forbidden"))
    result = tool.run_one(root, {"id":"SOFTWARE", "kind":"guard", "source":"opaque.py", "old":"old", "new":"new", "tests":"synthetic", "consequence":"fixture"}, logs)
    assert result["classification"] == "HOLD_EXISTING_LOGS"
    assert leaf.lstat().st_ino == before and retained.read_bytes() == b"keep"

def test_direct_helper_refuses_logs_inside_source(tmp_path, monkeypatch):
    root = tmp_path / "source"; root.mkdir(); logs = root / "logs"; logs.mkdir()
    monkeypatch.setattr(tool.shutil, "copytree", lambda *a, **k: pytest.fail("copy forbidden"))
    result = tool.run_one(root, {"id":"SOFTWARE", "kind":"guard", "source":"opaque.py", "old":"old", "new":"new", "tests":"synthetic", "consequence":"fixture"}, logs)
    assert result["classification"] == "HOLD_UNSAFE_LOGS"
