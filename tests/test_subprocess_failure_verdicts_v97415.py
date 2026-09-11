"""Failed external commands must not become negative scientific measurements."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(rel, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    spec = importlib.util.spec_from_file_location('failure_probe_' + Path(rel).stem, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def failed_binary(tmp_path):
    p = tmp_path / 'failed-tool'
    p.write_text('#!/bin/sh\necho "plausible 3.1.2"\necho "simulated failure" >&2\nexit 3\n')
    p.chmod(0o755)
    return str(p)


@pytest.mark.parametrize('rel,func', [
    ('deliverable_tools/clade_decontam.py', 'summed_bitscores_vs_ref'),
    ('deliverable_tools/clade_nt_core_bgc.py', '_blastn_dir'),
])
def test_failed_database_build_never_returns_empty_hits(tmp_path, monkeypatch, failed_binary, rel, func):
    mod = _load(rel, monkeypatch)
    if rel.endswith('clade_decontam.py'):
        with pytest.raises(RuntimeError, match=r'makeblastdb failed.*rc=3.*simulated failure'):
            getattr(mod, func)('query.fa', 'ref.fa', failed_binary, failed_binary, str(tmp_path))
    else:
        with pytest.raises(subprocess.CalledProcessError):
            getattr(mod, func)('query.fa', 'ref.fa', failed_binary, failed_binary, str(tmp_path))


@pytest.mark.parametrize('rel,func', [
    ('deliverable_tools/clade_decontam.py', 'summed_bitscores_vs_ref'),
    ('deliverable_tools/clade_nt_core_bgc.py', '_blastn_dir'),
])
def test_failed_blast_after_successful_db_never_returns_empty_hits(tmp_path, monkeypatch, failed_binary, rel, func):
    mod = _load(rel, monkeypatch)
    success = tmp_path / 'success-tool'
    success.write_text('#!/bin/sh\nexit 0\n'); success.chmod(0o755)
    with pytest.raises(subprocess.CalledProcessError):
        getattr(mod, func)('query.fa', 'ref.fa', failed_binary, str(success), str(tmp_path))


def test_mlsa_command_failure_stops_before_downstream_work(monkeypatch, failed_binary):
    mod = _load('tools/build_mlsa.py', monkeypatch)
    with pytest.raises(subprocess.CalledProcessError): mod._sh([failed_binary])


def test_refset_dedup_failure_is_not_a_successful_noop(monkeypatch, failed_binary):
    mod = _load('tools/phylo_refset.py', monkeypatch)
    monkeypatch.setattr(mod, '_bin', lambda _: failed_binary)
    with pytest.raises(SystemExit, match=r'makeblastdb failed.*exit 3'):
        mod.dedup([('Synthetica alpha strain A', 'ACGT'), ('Synthetica beta strain B', 'ACGA')])


def test_failed_version_probe_does_not_enter_methods(tmp_path, monkeypatch, failed_binary):
    mod = _load('tools/figure_methods.py', monkeypatch)
    monkeypatch.setattr(mod.shutil, 'which', lambda _: failed_binary)
    assert all(value == '' for value in mod.detect_versions([str(tmp_path)]).values())


@pytest.mark.parametrize('rc,stdout,stderr,status', [
    (3, 'GToTree 2.0.0', '', 'FAIL'), (0, '', 'GToTree 2.0.0', 'PASS'),
    (0, 'unrecognized banner', '', 'FAIL'),
])
def test_preflight_version_check_cannot_disappear(monkeypatch, rc, stdout, stderr, status):
    mod = _load('tools/phylo_preflight.py', monkeypatch)
    monkeypatch.setattr(mod, '_which', lambda _: '/fake/tool')
    def run(cmd, **kw):
        if cmd[0] == 'GToTree': return SimpleNamespace(returncode=rc, stdout=stdout, stderr=stderr)
        return SimpleNamespace(returncode=0, stdout='file probe', stderr='')
    monkeypatch.setattr(mod.subprocess, 'run', run)
    report = mod.Report();mod.check_env(report)
    rows = [row for row in report.items if row['check'] == 'E2']
    assert len(rows) == 1 and rows[0]['status'] == status


@pytest.mark.parametrize('rc,report,expected', [
    (3, None, 'GATE_ERROR'),
    (0, None, 'GATE_ERROR'),
    (0, dict(exit_code=1, status='FAIL', warning_instances=0), 'GATE_ERROR'),
    (1, dict(exit_code=1, status='FAIL', warning_instances=1), 'FAIL'),
    (0, dict(exit_code=0, status='PASS', warning_instances=0, coverage_verified=False), 'COVERAGE_UNVERIFIED'),
    (0, dict(exit_code=0, status='PASS', warning_instances=0, coverage_verified=True), 'OK'),
])
def test_round_ledger_uses_receipt_and_exit_not_ok_text(monkeypatch, rc, report, expected):
    mod = _load('tools/round_ledger.py', monkeypatch)
    def run(cmd, **kw):
        if report is not None:
            Path(cmd[cmd.index('--report-json') + 1]).write_text(json.dumps(report))
        return SimpleNamespace(returncode=rc, stdout='OK (0 warnings) missing traceback', stderr='')
    monkeypatch.setattr(mod.subprocess, 'run', run)
    assert mod.run_gate('card.md', 'package', 'synthetic-alias')[0] == expected


def test_failed_harvest_cannot_write_reference_or_success_receipt(tmp_path, monkeypatch, failed_binary):
    mod = _load('tools/harvest_16s.py', monkeypatch)
    source = tmp_path / 'source.fa';source.write_text('>TEST\nACGT\n')
    out = tmp_path / 'output'
    monkeypatch.setattr(sys, 'argv', ['harvest', '--genus', 'Synthetica', '--strains', 'TEST',
        '--authoritative', str(source), '--refseq-db', 'missing-db', '--blastdbcmd', failed_binary,
        '--out-dir', str(out)])
    assert mod.main() == 3
    assert not (out / 'Synthetica_reference.fasta').exists()
    receipt = (out / 'harvest_receipt.txt').read_text()
    assert 'reference_records=ERROR' in receipt
    assert 'reference_status=ERROR blastdbcmd exit 3' in receipt
    assert 'reference_records=0' not in receipt
