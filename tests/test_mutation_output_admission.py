"""Report-path preservation only; all workflow functions and subprocesses forbidden/stubbed."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/gate_mutation_probe.py'
spec = importlib.util.spec_from_file_location('isolated_mutation_output', SCRIPT)
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)

@pytest.fixture
def case(tmp_path, monkeypatch):
    root = tmp_path / 'source'; (root / 'mamey').mkdir(parents=True)
    (root / 'mamey/validate.py').write_text('SOFTWARE_SOURCE_MARKER\n')
    other = root / 'opaque.py'; other.write_text('SOFTWARE_OTHER_SOURCE_BYTES\n')
    table = tmp_path / 'selected.tsv'
    table.write_text('id\tkind\tsource\told\tnew\ttests\tconsequence\nSOFTWARE\tguard\topaque.py\told\tnew\t\tsoftware-only\n')
    output = tmp_path / 'reports/result.tsv'
    calls = []
    def no_process(*args, **kwargs): pytest.fail('mutation subprocess reached')
    monkeypatch.setattr(tool.subprocess, 'run', no_process)
    def result(root, row, logs):
        calls.append('stub-run-one')
        return dict(row, classification='UNPAIRED', mutation_status='NOT_RUN', remediation='STUB_ONLY', exit_code='', log='')
    monkeypatch.setattr(tool, 'run_one', result)
    monkeypatch.setattr(tool, 'inventory', lambda root: [])
    monkeypatch.setattr(tool, 'inventory_results', lambda *args: [])
    def invoke(destination):
        monkeypatch.setattr(sys, 'argv', ['gate_mutation_probe', '--source-root', str(root), '--mutation-table', str(table), '--output', str(destination)])
        return tool.main()
    return root, table, output, other, calls, invoke

@pytest.mark.parametrize('alias', ['direct-table', 'symlink-table', 'hardlink-table', 'hardlink-source', 'symlink-source', 'inside-source', 'parent-symlink-source', 'logs-symlink-source'])
def test_selected_sources_survive_output_aliases(case, tmp_path, alias, capsys):
    root, table, output, other, calls, invoke = case
    if alias == 'direct-table': output = table
    elif alias == 'inside-source': output = root / 'result.tsv'
    elif alias == 'parent-symlink-source':
        parent = tmp_path / 'alias-parent'; parent.symlink_to(root, target_is_directory=True); output = parent / 'result.tsv'
    else:
        output.parent.mkdir()
        if alias == 'symlink-table': output.symlink_to(table)
        elif alias == 'hardlink-table': os.link(table, output)
        elif alias == 'hardlink-source': os.link(other, output)
        elif alias == 'symlink-source': output.symlink_to(other)
        elif alias == 'logs-symlink-source': (output.parent / 'probe_logs').symlink_to(root, target_is_directory=True)
    before = {p: p.read_bytes() for p in [table, *root.rglob('*.py')]}
    refused = None
    try:
        invoke(output)
    except SystemExit as error:
        refused = error
    if os.environ.get('MUTATION_RESULTS'):
        with open(os.environ['MUTATION_RESULTS'], 'a') as receipt:
            receipt.write(json.dumps({'case': alias, 'refusal_code': refused.code if refused else None, 'stub_workflow_calls': len(calls), 'input_bytes_preserved': {str(p.relative_to(tmp_path)): p.read_bytes() == value for p, value in before.items()}, 'new_source_report_exists': (root / 'result.tsv').exists()}) + '\n')
    assert refused is not None and refused.code == 2
    assert 'MUTATION_OUTPUT_' in capsys.readouterr().err
    assert not calls
    assert all(p.read_bytes() == value for p, value in before.items())
    assert not (root / 'result.tsv').exists()
    if alias not in {'direct-table', 'logs-symlink-source'}:
        assert not (output.parent / 'probe_logs').exists()

@pytest.mark.parametrize('prior', [False, True], ids=['fresh', 'existing-single-link'])
def test_unrelated_report_behavior_remains(case, prior):
    root, table, output, other, calls, invoke = case
    output.parent.mkdir()
    if prior: output.write_text('prior unrelated report')
    before = {p: p.read_bytes() for p in [table, *root.rglob('*.py')]}
    assert invoke(output) == 0
    assert calls == ['stub-run-one']
    assert 'UNPAIRED' in output.read_text() and (output.parent / 'probe_logs').is_dir()
    assert all(p.read_bytes() == value for p, value in before.items())


def test_unrelated_multilink_output_is_explicitly_refused(case, tmp_path):
    root, table, output, other, calls, invoke = case
    output.parent.mkdir(); outside = tmp_path / 'unrelated.txt'; outside.write_text('unrelated bytes')
    os.link(outside, output)
    with pytest.raises(SystemExit) as caught: invoke(output)
    assert caught.value.code == 2 and outside.read_text() == 'unrelated bytes' and not calls


@pytest.mark.parametrize("dangling", [False, True])
def test_unrelated_symlink_output_is_refused(case, tmp_path, dangling):
    root, table, output, other, calls, invoke = case
    output.parent.mkdir(); outside = tmp_path / 'unrelated.txt'
    if not dangling: outside.write_text('retained external evidence')
    output.symlink_to(outside)
    with pytest.raises(SystemExit) as caught: invoke(output)
    assert caught.value.code == 2 and output.is_symlink() and not calls
    assert outside.read_text() == 'retained external evidence' if not dangling else not outside.exists()
    assert not (output.parent / 'probe_logs').exists()
