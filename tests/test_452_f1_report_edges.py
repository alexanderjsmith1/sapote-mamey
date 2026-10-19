"""Generic mixed report publication, rollback and output ownership controls."""
from pathlib import Path

import pytest
from mamey import output_transaction as tool


def fresh_pair(tmp_path):
    first, second, report = (tmp_path / name for name in ('first.txt', 'second.txt', 'report.md'))
    return first, second, report, {first: b'first', second: b'second'}


def test_absent_report_fsync_fault_rolls_back_whole_roster(tmp_path, monkeypatch):
    first, second, report, payloads = fresh_pair(tmp_path)
    original = tool.os.fsync
    calls = []
    primary = OSError('synthetic final fresh report fsync fault')
    def fsync(fd):
        calls.append(fd)
        if len(calls) == 3:
            assert first.exists() and second.exists() and report.exists()
            raise primary
        return original(fd)
    monkeypatch.setattr(tool.os, 'fsync', fsync)
    with pytest.raises(OSError) as caught:
        tool.publish_payloads(payloads, replacement=(report, b'report'))
    assert caught.value is primary and len(calls) == 3
    assert not first.exists() and not second.exists() and not report.exists()
    assert {r['path']: r['status'] for r in primary.rollback_cleanup_diagnostics} == {
        str(first): 'REMOVED', str(second): 'REMOVED', str(report): 'REMOVED'}
    assert not list(tmp_path.glob('.mamey-report-*'))


def test_late_absent_report_claim_preserves_claimant_and_rolls_back_pair(tmp_path, monkeypatch):
    first, second, report, payloads = fresh_pair(tmp_path)
    original = Path.open
    seen = []
    def open_path(path, mode='r', *args, **kwargs):
        if path == report and mode == 'xb':
            seen.append((first.exists(), second.exists()))
            with original(report, 'wb') as handle:
                handle.write(b'independent claimant')
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', open_path)
    with pytest.raises(FileExistsError):
        tool.publish_payloads(payloads, replacement=(report, b'report'))
    assert seen == [(True, True)]
    assert report.read_bytes() == b'independent claimant'
    assert not first.exists() and not second.exists()
    assert not list(tmp_path.glob('.mamey-report-*'))


def test_existing_report_stage_fsync_fault_preserves_old_report(tmp_path, monkeypatch):
    first, second, report, payloads = fresh_pair(tmp_path)
    report.write_bytes(b'old report')
    primary = OSError('synthetic report stage fsync fault')
    seen = []
    def fsync(fd):
        seen.extend(tmp_path.glob('.mamey-report-*'))
        assert not first.exists() and not second.exists()
        raise primary
    monkeypatch.setattr(tool.os, 'fsync', fsync)
    with pytest.raises(OSError) as caught:
        tool.publish_payloads(payloads, replacement=(report, b'report'))
    assert caught.value is primary and len(seen) == 1
    assert report.read_bytes() == b'old report'
    assert not first.exists() and not second.exists() and not seen[0].exists()
    rows = primary.rollback_cleanup_diagnostics
    assert len(rows) == 1
    assert (rows[0]['path'], rows[0]['action'], rows[0]['status']) == (str(seen[0]), 'unlink', 'REMOVED')


@pytest.mark.parametrize('condition', ['denied', 'changed_owner'])
def test_mixed_failure_keeps_primary_and_reports_stage_cleanup(tmp_path, monkeypatch, condition):
    first, second, report, payloads = fresh_pair(tmp_path)
    report.write_bytes(b'old report')
    primary = OSError('synthetic second catalog creation fault')
    original_open, original_unlink = Path.open, Path.unlink
    stages = []
    def open_path(path, mode='r', *args, **kwargs):
        if path == second and mode == 'xb':
            stages.extend(tmp_path.glob('.mamey-report-*'))
            assert first.exists() and len(stages) == 1
            if condition == 'changed_owner':
                stages[0].rename(tmp_path / 'displaced-owned-stage')
                stages[0].write_bytes(b'independent stage claimant')
            raise primary
        return original_open(path, mode, *args, **kwargs)
    def unlink(path, *args, **kwargs):
        if path in stages and condition == 'denied':
            raise PermissionError('synthetic stage cleanup denial')
        return original_unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', open_path)
    monkeypatch.setattr(Path, 'unlink', unlink)
    with pytest.raises(OSError) as caught:
        tool.publish_payloads(payloads, replacement=(report, b'report'))
    assert caught.value is primary and report.read_bytes() == b'old report'
    assert not first.exists() and not second.exists()
    stage_row = next(r for r in primary.rollback_cleanup_diagnostics if r['path'] == str(stages[0]))
    expected = 'CLEANUP_FAILED' if condition == 'denied' else 'OWNERSHIP_CHANGED'
    assert stage_row['status'] == expected
    assert any(expected in note for note in primary.__notes__)
    expected_bytes = b'report' if condition == 'denied' else b'independent stage claimant'
    assert stages[0].read_bytes() == expected_bytes


def test_existing_report_change_before_commit_preserves_new_owner(tmp_path, monkeypatch):
    first, second, report, payloads = fresh_pair(tmp_path)
    report.write_bytes(b'old report')
    claimant = tmp_path / 'claimant.txt'
    claimant.write_bytes(b'independent report claimant')
    original = tool.os.fsync
    calls = []
    def fsync(fd):
        calls.append(fd)
        result = original(fd)
        if len(calls) == 3:
            tool.os.replace(claimant, report)
        return result
    monkeypatch.setattr(tool.os, 'fsync', fsync)
    with pytest.raises(ValueError, match='changed before commit'):
        tool.publish_payloads(payloads, replacement=(report, b'report'))
    assert len(calls) == 3 and report.read_bytes() == b'independent report claimant'
    assert not first.exists() and not second.exists()
    assert not list(tmp_path.glob('.mamey-report-*'))


@pytest.mark.parametrize('exists', [False, True])
def test_report_only_bytes_contract_with_empty_fresh_roster(tmp_path, exists):
    report = tmp_path / 'report.md'
    if exists:
        report.write_bytes(b'old report')
    tool.publish_payloads({}, replacement=(report, b'synthetic replacement\n'))
    assert report.read_bytes() == b'synthetic replacement\n'
    assert not list(tmp_path.glob('.mamey-report-*'))


@pytest.mark.parametrize('report_slot', [False, True])
def test_casefold_component_ancestry_refuses_without_parent_creation(tmp_path, report_slot):
    ancestor, descendant = tmp_path / 'Slot', tmp_path / 'slot' / 'leaf.txt'
    with pytest.raises(ValueError, match='output paths collide'):
        if report_slot:
            tool.preflight_output_roster([descendant], replacement=ancestor)
        else:
            tool.preflight_output_roster([ancestor, descendant])
    assert not ancestor.exists() and not descendant.parent.exists()
