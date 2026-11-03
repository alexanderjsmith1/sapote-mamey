"""Protect panel, tree and host inputs when writing a numbered roster."""
import importlib.util
import os
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'tools' / 'phylo_roster.py'
SPEC = importlib.util.spec_from_file_location('roster_source_preservation', SOURCE)
roster = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(roster)


@pytest.mark.parametrize('source_kind', ['panel', 'tree', 'strain_table'])
@pytest.mark.parametrize('alias_kind', ['direct', 'symlink', 'hardlink'])
def test_input_alias_refused_before_write(tmp_path, source_kind, alias_kind):
    panel, tree, hosts = (tmp_path / name for name in ('panel.tsv', 'tree.nwk', 'hosts.csv'))
    panel.write_text('candidate_id\trole\nA\tREFERENCE\nB\tREFERENCE\n')
    tree.write_text('(A:0.1,B:0.2);\n')
    hosts.write_text('label,host\nA,soil\n')
    source = {'panel': panel, 'tree': tree, 'strain_table': hosts}[source_kind]
    original = source.read_bytes()
    output = source if alias_kind == 'direct' else tmp_path / 'alias'
    if alias_kind == 'symlink':
        output.symlink_to(source)
    elif alias_kind == 'hardlink':
        os.link(source, output)
    args = ['--tree', str(tree)] if source_kind == 'tree' else ['--panel', str(panel)]
    if source_kind == 'strain_table':
        args += ['--strain-table', str(hosts)]
    with pytest.raises(SystemExit) as exc:
        roster.main([*args, '--remove', '1', '--out', str(output)])
    assert exc.value.code == 2
    assert source.read_bytes() == original


@pytest.mark.parametrize('content', ['', 'candidate_id\trole\n'])
def test_empty_panel_preserves_existing_output(tmp_path, content):
    panel, output = tmp_path / 'panel.tsv', tmp_path / 'output.tsv'
    panel.write_text(content)
    output.write_bytes(b'existing output\n')
    with pytest.raises(SystemExit) as exc:
        roster.main(['--panel', str(panel), '--remove', '1', '--out', str(output)])
    assert exc.value.code == 2
    assert output.read_bytes() == b'existing output\n'
