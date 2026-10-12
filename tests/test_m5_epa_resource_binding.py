"""Capture actual placement command construction, never execute external tools."""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from tools import phylo_place as place
from tools import phylo_autopilot as autopilot


@pytest.mark.parametrize('threads', [1, 3])
def test_alignment_split_and_mafft_share_explicit_budget(tmp_path, monkeypatch, threads):
    ref = tmp_path / 'ref.fa'; ref.write_text('>REF\nACGT\n')
    query = tmp_path / 'q.fa'; query.write_text('>Q\nAC\n')
    monkeypatch.setenv('OMP_NUM_THREADS', '48')
    calls = []
    def fake(cmd, **kwargs):
        calls.append((cmd, kwargs['env']))
        if cmd[0] == 'mafft':
            kwargs['stdout'].write('>REF\nACGT\n>Q\nAC--\n')
        else:
            (Path(cmd[cmd.index('--outdir') + 1]) / 'query.fasta').write_text('>Q\nAC--\n')
    monkeypatch.setattr(place.subprocess, 'check_call', fake)
    result = place._align_queries('mafft', 'epa', str(ref), str(query), str(tmp_path), False, threads=threads)
    assert Path(result).read_text() == '>Q\nAC--\n'
    assert calls[0][0][calls[0][0].index('--thread') + 1] == str(threads)
    assert calls[1][0][calls[1][0].index('--threads') + 1] == str(threads)
    for _, env in calls:
        for key in ('OMP_NUM_THREADS', 'OMP_THREAD_LIMIT', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
            assert env[key] == str(threads)


@pytest.mark.parametrize('threads', [1, 3])
def test_actual_place_handler_binds_epa_and_provenance(tmp_path, monkeypatch, threads):
    ref = tmp_path / 'refpkg'; ref.mkdir()
    (ref / '_provenance.json').write_text(json.dumps({'group': 'streptomyces', 'molecule': 'nucleotide'}))
    (ref / 'labelmap.tsv').write_text('safe\toriginal\nREF\tREF\n')
    (ref / 'ref.aln.fasta').write_text('>REF\nACGT\n')
    (ref / 'ref.tree').write_text('(REF:0.1);\n')
    query = tmp_path / 'query.fa'; query.write_text('>Q\n' + 'ACGT' * 350 + '\n')
    out = tmp_path / 'placement'; calls = []
    monkeypatch.setenv('OMP_NUM_THREADS', '48')
    epa = tmp_path / 'synthetic epa-ng'; epa.write_text('synthetic executable identity'); epa.chmod(0o755)
    monkeypatch.setattr(place, '_which', lambda name, *bins: str(epa) if name == 'epa-ng' else name)
    probes = []
    def probe(command, **kwargs):
        probes.append((command, kwargs['env']))
        assert command == [str(epa), '--version'] and kwargs['timeout'] == 10
        return SimpleNamespace(returncode=0, stdout=b'EPA-ng v0.3.8\n', stderr=b'')
    monkeypatch.setattr(place.subprocess, 'run', probe)
    def align(*args, **kwargs):
        assert kwargs['threads'] == threads
        aligned = out / 'query.aligned.fasta'; aligned.write_text('>Q\nACGT\n'); return str(aligned)
    monkeypatch.setattr(place, '_align_queries', align)
    monkeypatch.setattr(place.subprocess, 'call', lambda cmd, **kw: calls.append((cmd, kw['env'])) or 0)
    args = SimpleNamespace(refpkg=str(ref), query=str(query), outdir=str(out), fragmentary=False, threads=threads)
    assert place.cmd_place(args) == 0
    cmd, env = calls[0]
    assert cmd[cmd.index('--threads') + 1] == str(threads)
    assert env['OMP_NUM_THREADS'] == str(threads)
    assert probes[0][1]['OMP_THREAD_LIMIT'] == str(threads)
    receipt = json.loads((out / '_provenance.json').read_text())
    assert receipt['epa_ng_admission']['version'] == '0.3.8'
    assert receipt['threads'] == threads and receipt['resource_environment']['OMP_THREAD_LIMIT'] == str(threads)


def test_place_parser_exposes_one_core_default(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(place, 'cmd_place', lambda a: seen.append(a.threads) or 0)
    monkeypatch.setattr(sys, 'argv', ['phylo_place.py', 'place', '--refpkg', 'unused', '--query', 'unused'])
    assert place.main() == 0 and seen == [1]


def test_all_handler_keeps_budget_through_each_stage(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(place, 'cmd_build_ref', lambda a: seen.append(('build', a.threads)) or 0)
    monkeypatch.setattr(place, 'cmd_place', lambda a: seen.append(('place', a.threads)) or 0)
    monkeypatch.setattr(place, 'cmd_report', lambda a: seen.append(('report', a.threads)) or 0)
    a = SimpleNamespace(refpkg=None, outdir=str(tmp_path / 'new'), group='streptomyces', threads='3')
    assert place.cmd_all(a) == 0
    assert seen == [('build', 3), ('place', 3), ('report', 3)]


@pytest.mark.parametrize('threads', [None, '3'])
def test_actual_autopilot_handler_forwards_budget(tmp_path, monkeypatch, threads):
    query = tmp_path / 'q.fa'; query.write_text('>Q\n' + 'ACGT' * 350 + '\n')
    monkeypatch.setattr(autopilot, 'assign_genus', lambda *a, **k: {'Q': {'genus': 'Streptomyces', 'pident': 99, 'aln_len': '1400', 'title': 'synthetic'}})
    monkeypatch.setattr(autopilot, 'build_reference_fasta', lambda *a, **k: 3)
    calls = []
    monkeypatch.setattr(autopilot.subprocess, 'run', lambda cmd, **kw: calls.append(cmd) or SimpleNamespace(returncode=0))
    argv = ['run-16s', '--query', str(query), '--db', 'synthetic_db', '--group', 'streptomyces',
            '--outdir', str(tmp_path / 'new'), '--approved-by', 'synthetic test']
    if threads is not None:
        argv += ['--threads', threads]
    assert autopilot.main(argv) == 0
    assert calls[0][calls[0].index('--threads') + 1] == (threads or '1')


def test_invalid_budget_refuses_before_input_or_output(tmp_path):
    out = tmp_path / 'new'
    assert autopilot.main(['run-16s', '--query', 'missing', '--db', 'missing', '--group', 'streptomyces',
                           '--outdir', str(out), '--threads', '0', '--dry-run']) == 2
    assert not out.exists()
    with pytest.raises(argparse.ArgumentTypeError):
        place.cmd_place(SimpleNamespace(threads=0))
