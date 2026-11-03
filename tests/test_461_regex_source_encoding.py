"""Encoding admission fixtures only; no repository-wide or research evidence scan."""
import ast
import importlib.util
import os
from pathlib import Path
import pytest
TARGET=Path(__file__).resolve().parents[1]/'tools/check_regex_interpolation.py'
spec=importlib.util.spec_from_file_location('regex_encoding_gate',TARGET)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


BAD=[b'x="\xff"\n',b'#\xff\n',b'# coding: missing_codec\nx=1\n',b'\xef\xbb\xbf# coding: latin-1\nx=1\n']
@pytest.mark.parametrize('payload',BAD)
@pytest.mark.parametrize('mixed',[False,True])
def test_invalid_source_bytes_refuse_without_pass(tmp_path,capsys,payload,mixed):
    source=tmp_path/'invalid.py';source.write_bytes(payload)
    if mixed:(tmp_path/'valid.py').write_text('x=1\n')
    assert mod.main(['--root',str(tmp_path),'--json'])==2
    captured=capsys.readouterr()
    assert 'PASS' not in captured.out
    assert captured.out==''
    assert 'cannot parse' in captured.err and 'invalid.py' in captured.err
    assert source.read_bytes()==payload


@pytest.mark.parametrize('encoding,header', [('utf-8',''),('utf-8','# coding: utf-8\n'),('latin-1','# coding: latin-1\n'),('cp1252','# coding: cp1252\n'),('utf-8-sig','')])
def test_valid_encodings_keep_exact_decoded_constant(tmp_path,encoding,header):
    source=tmp_path/'encoded.py'
    text=header+'import re\nTOKENS="café|other"\nPAT=re.compile(rf"^{TOKENS}$")\n'
    payload=text.encode(encoding);source.write_bytes(payload)
    ast.parse(payload)
    records=list(mod.scan_file(source))
    assert len(records)==1
    assert records[0]['value']=='café|other'
    assert source.read_bytes()==payload


def test_valid_clean_source_still_passes(tmp_path,capsys):
    source=tmp_path/'valid.py';source.write_text('x=1\n')
    assert mod.main(['--root',str(source)])==0
    assert 'PASS' in capsys.readouterr().out


@pytest.mark.parametrize('payload,expected',[(b'x="\xff"\n',2),('# coding: latin-1\nimport re\nTOKENS="café|other"\nPAT=re.compile(rf"^{TOKENS}$")\n'.encode('latin-1'),1)])
def test_actual_cli_preserves_exit_contract(tmp_path,payload,expected):
    import subprocess
    import sys
    source=tmp_path/'cli_source.py';source.write_bytes(payload)
    result=subprocess.run([sys.executable,'-B',str(TARGET),'--root',str(source),'--json'],capture_output=True,text=True)
    assert result.returncode==expected
    assert 'Traceback' not in result.stderr
    if expected==2:
        assert result.stdout==''
        assert 'cannot parse' in result.stderr
    else:
        import json
        assert json.loads(result.stdout)['new'][0]['value']=='café|other'
