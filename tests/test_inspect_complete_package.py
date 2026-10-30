"""Result archives route to saved results; raw antiSMASH inputs keep their route."""
import argparse
import json
import zipfile
from pathlib import Path

import pytest
from mamey.package_inspector import inspect_command


def manifest():
    return {'strain_id': 'software-fixture', 'workflow_version': 'Mamey v1.9.177',
            'bundle_version': '9.7.460', 'bgcs': [], 'bgc_counts': {}}


def archive(tmp_path, members, name='saved-results.zip'):
    path = tmp_path / name
    with zipfile.ZipFile(path, 'w') as z:
        for member, value in members:
            z.writestr(member, json.dumps(value) if isinstance(value, (dict, list)) else value)
    return path


@pytest.mark.parametrize('prefix', ['', 'package/', 'saved/package/'])
def test_result_manifest_routes_to_read_results(tmp_path, capsys, prefix):
    path = archive(tmp_path, [(prefix+'manifest.json', manifest()),
                              (prefix+'OPEN_ME_FIRST.html', '<html>fixture</html>')])
    before = path.read_bytes()
    assert inspect_command(argparse.Namespace(zip=str(path))) == 0
    out = capsys.readouterr().out
    assert 'Sapote-Mamey Complete Package' in out
    assert 'docs/reader/03_READ_RESULTS.md' in out
    assert prefix+'OPEN_ME_FIRST.html' in out
    assert 'Run antiSMASH first' not in out and 'run --input-zip' not in out
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == [path.name]


def test_saved_manifest_takes_precedence_over_embedded_region_files(tmp_path, capsys):
    path = archive(tmp_path, [('manifest.json', manifest()),
                             ('fixture.region001.gbk', 'LOCUS fixture\n//\n')])
    assert inspect_command(argparse.Namespace(zip=str(path))) == 0
    out = capsys.readouterr().out
    assert 'Sapote-Mamey Complete Package' in out
    assert 'Capped-session run command' not in out
    assert 'Read results' in out
    assert 'open OPEN_ME_FIRST.html' not in out


def test_filename_and_foreign_manifest_do_not_identify_results(tmp_path, capsys):
    path = archive(tmp_path, [('manifest.json', {'tool': 'another program'}),
                             ('fixture.region001.gbk', 'LOCUS fixture\nCOMMENT antiSMASH 8.0.4\n//\n')],
                   name='fixture_Complete_Package.zip')
    assert inspect_command(argparse.Namespace(zip=str(path))) == 0
    out = capsys.readouterr().out
    assert 'Capped-session run command' in out
    assert 'Sapote-Mamey Complete Package' not in out


@pytest.mark.parametrize('value', [{'tool': 'another program'}, [], {'strain_id': 'x', 'workflow_version': 'Mamey v1'}])
def test_unrelated_or_incomplete_manifest_is_not_a_result_package(tmp_path, capsys, value):
    path = archive(tmp_path, [('manifest.json', value)])
    assert inspect_command(argparse.Namespace(zip=str(path))) == 1
    assert 'Sapote-Mamey Complete Package' not in capsys.readouterr().out


@pytest.mark.parametrize('second', ['manifest.json', 'other/manifest.json'])
def test_duplicate_or_multiple_result_manifests_are_reported(tmp_path, capsys, second):
    with pytest.warns(UserWarning) if second == 'manifest.json' else __import__('contextlib').nullcontext():
        path = archive(tmp_path, [('manifest.json', manifest()), (second, manifest())])
    assert inspect_command(argparse.Namespace(zip=str(path))) == 1
    captured = capsys.readouterr()
    assert 'PACKAGE_MANIFEST_AMBIGUOUS' in captured.err
    assert 'Run antiSMASH first' not in captured.out


def test_inspect_help_names_both_input_types(capsys):
    from mamey.cli import main
    with pytest.raises(SystemExit) as caught:
        main(['inspect', '--help'])
    assert caught.value.code == 0
    out = capsys.readouterr().out
    assert 'antiSMASH' in out and 'Complete Package' in out


def test_unreadable_manifest_reports_the_manifest_problem(tmp_path, capsys):
    path = archive(tmp_path, [('manifest.json', '{broken')])
    assert inspect_command(argparse.Namespace(zip=str(path))) == 1
    captured = capsys.readouterr()
    assert 'PACKAGE_MANIFEST_UNREADABLE' in captured.err
    assert 'Run antiSMASH first' not in captured.out


def test_oversize_manifest_is_refused_before_open(tmp_path, capsys, monkeypatch):
    from mamey.antismash_evidence import FULL_MAX_JSON_BYTES
    path = archive(tmp_path, [('manifest.json', manifest())])
    original = zipfile.ZipFile.getinfo
    def getinfo(z, name):
        info = original(z, name)
        if name == 'manifest.json':
            info.file_size = FULL_MAX_JSON_BYTES + 1
        return info
    monkeypatch.setattr(zipfile.ZipFile, 'getinfo', getinfo)
    assert inspect_command(argparse.Namespace(zip=str(path))) == 1
    assert 'PACKAGE_MANIFEST_TOO_LARGE' in capsys.readouterr().err


@pytest.mark.parametrize('member', ['/manifest.json', '../manifest.json', 'C:/manifest.json'])
def test_unsafe_manifest_paths_are_not_recommended_for_extraction(tmp_path, capsys, member):
    path = archive(tmp_path, [(member, manifest())])
    assert inspect_command(argparse.Namespace(zip=str(path))) == 1
    captured = capsys.readouterr()
    assert 'PACKAGE_MANIFEST_PATH_UNSAFE' in captured.err
    assert 'Extract the ZIP' not in captured.out
