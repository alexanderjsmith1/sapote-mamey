"""Real-workflow regression: account-wide markers are not evidence authority."""
from pathlib import Path
import argparse
import pytest
from mamey import blastp_gate as G
from mamey import cli

@pytest.mark.parametrize('marker', G._PROJECT_MARKERS)
def test_home_marker_does_not_select_account_root(tmp_path, monkeypatch, marker):
    home = tmp_path / 'home'
    package = home / 'analysis' / 'runs' / 'REFERENCE' / 'package'
    package.mkdir(parents=True)
    (home / marker).touch()
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: home))
    monkeypatch.chdir(home)
    monkeypatch.delenv('MAMEY_BLASTP_SCAN_ROOT', raising=False)
    assert G.find_workspace_root(package) == package.parent


def test_project_marker_inside_home_remains_authoritative(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    project = home / 'analysis'
    package = project / 'runs' / 'package'
    package.mkdir(parents=True)
    (home / '.claude').mkdir()
    (project / '.mamey_project').touch()
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: home))
    monkeypatch.delenv('MAMEY_BLASTP_SCAN_ROOT', raising=False)
    assert G.find_workspace_root(package) == project


def test_explicit_home_root_remains_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    monkeypatch.setenv('MAMEY_BLASTP_SCAN_ROOT', str(tmp_path))
    assert G.find_workspace_root(tmp_path / 'package') == tmp_path


@pytest.mark.parametrize('command', ['emit-modeb-template', 'compile-report', 'blastp-availability', 'ingest-blastp-trove', 'deliverable-queue'])
def test_cli_returns_typed_discovery_refusal(command, monkeypatch, capsys, tmp_path):
    def refuse(args):
        raise G.BlastpDiscoveryError('BLASTP_DISCOVERY_HOLD: configured evidence is unreadable')
    parser = argparse.ArgumentParser()
    parser.set_defaults(command=command, func=refuse, package=tmp_path)
    monkeypatch.setattr(cli, 'build_parser', lambda: parser)
    assert cli.main([]) == 3
    err = capsys.readouterr().err
    assert 'BLASTP_DISCOVERY_HOLD' in err
    assert 'MAMEY_BLASTP_SCAN_ROOT' in err
    assert 'Traceback' not in err


def test_cli_does_not_hide_unrelated_programming_error(monkeypatch):
    def broken(args):
        raise RuntimeError('implementation defect')
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=broken)
    monkeypatch.setattr(cli, 'build_parser', lambda: parser)
    with pytest.raises(RuntimeError, match='implementation defect'):
        cli.main([])
