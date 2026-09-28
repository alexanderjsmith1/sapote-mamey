"""Hostile regression fixtures for the public inspect recommendation."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import zipfile

from mamey.package_inspector import inspect_command, _inspect_strain_guess


def archive(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('NODE_1_length_1000_cov_1.region001.gbk',
                   'LOCUS       NODE_1 1000 bp DNA\nCOMMENT     antiSMASH 8.0.4\n//\n')
    return path


def command(path, capsys):
    assert inspect_command(argparse.Namespace(zip=str(path))) == 0
    out = capsys.readouterr().out
    block = out.split('Capped-session run command', 1)[1]
    return block[block.index('    python '):block.index('    Then validate:')].strip()


def test_recommendation_preserves_input_outside_working_directory(tmp_path, capsys, monkeypatch):
    path = archive(tmp_path / 'external inputs' / 'sample.zip')
    work = tmp_path / 'work'
    work.mkdir()
    monkeypatch.chdir(work)
    args = shlex.split(command(path, capsys).replace('\\\n', ''))
    named = Path(args[args.index('--input-zip') + 1])
    assert named.resolve() == path.resolve()
    assert named.is_file()


def test_recommendation_does_not_execute_filename_substitution(tmp_path, capsys):
    path = archive(tmp_path / 'external inputs' / 'sample$(touch SHELL_SIDE_EFFECT).zip')
    cmd = command(path, capsys).replace("<PUBLIC|PRIVATE>", "PRIVATE")
    fakebin = tmp_path / 'bin'
    fakebin.mkdir()
    stub = fakebin / 'python'
    stub.write_text('#!' + sys.executable + '\nimport json,os,sys\n'
                    'open(os.environ["CAPTURE_ARGV"],"w").write(json.dumps(sys.argv[1:]))\n')
    stub.chmod(0o755)
    captured = tmp_path / 'argv.json'
    env = dict(os.environ, PATH=str(fakebin) + os.pathsep + os.environ['PATH'],
               CAPTURE_ARGV=str(captured))
    done = subprocess.run(['bash', '-c', cmd], cwd=tmp_path, env=env,
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert not (tmp_path / 'SHELL_SIDE_EFFECT').exists()
    args = json.loads(captured.read_text())
    assert args[args.index('--input-zip') + 1] == str(path.resolve())


def test_quote_characters_round_trip_as_one_input_argument(tmp_path, capsys):
    path = archive(tmp_path / 'external inputs' / 'sample"with\'quotes.zip')
    args = shlex.split(command(path, capsys).replace('\\\n', ''))
    assert args[args.index('--input-zip') + 1] == str(path.resolve())


def test_empty_sanitized_guess_is_safe_and_not_raw_filename():
    guess = _inspect_strain_guess(Path('$().zip'))
    assert guess
    assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', guess)


def test_leading_option_name_is_not_a_strain_flag(tmp_path, capsys):
    path = archive(tmp_path / '--help.zip')
    args = shlex.split(command(path, capsys).replace('\\\n', ''))
    assert not args[args.index('--strain') + 1].startswith('-')
