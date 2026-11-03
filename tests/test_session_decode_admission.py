"""Synthetic bytes only; no user transcript discovery."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/session_cost_audit.py"
spec = importlib.util.spec_from_file_location("session_decode_candidate", SCRIPT)
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)

def record(tokens=12, opaque="valid"):
    return {"type": "assistant", "message": {"role": "assistant", "usage": {"input_tokens": tokens}, "content": [], "opaque": opaque}}

@pytest.mark.parametrize("kind", ["value", "key", "role", "incomplete_multibyte"])
def test_decode_damage_cannot_be_admitted_as_replacement_json(tmp_path, capsys, kind):
    value = record(12, "PRIVATE_OPAQUE")
    raw = json.dumps(value).encode()
    if kind == "value": raw = raw.replace(b'PRIVATE_OPAQUE', b'PRIVATE_\xff_OPAQUE')
    elif kind == "key": raw = raw.replace(b'input_tokens', b'input_token\xffs')
    elif kind == "role": raw = raw.replace(b'"role": "assistant"', b'"role": "assistant\xff"')
    else: raw = raw.replace(b'PRIVATE_OPAQUE', b'PRIVATE_\xe2\x82_OPAQUE')
    # This exact corruption remains syntactically valid JSON under legacy replacement decoding.
    normalized = json.loads(raw.decode('utf-8', errors='replace'))
    assert '\ufffd' in json.dumps(normalized, ensure_ascii=False)
    p = tmp_path / "software.jsonl"
    p.write_bytes(json.dumps(record(10)).encode() + b'\n\n' + raw + b'\n' + json.dumps(record(20)).encode())
    before = p.read_bytes()
    assert [r['message']['usage']['input_tokens'] for r in tool.iter_records(p)] == [10, 20]
    out = capsys.readouterr()
    assert not out.out and out.err.count('SESSION_COST_PARTIAL') == 1 and ':3:' in out.err
    assert 'PRIVATE_' not in out.err and '\ufffd' not in out.err and '\udcff' not in out.err
    assert p.read_bytes() == before

@pytest.mark.parametrize("escaped", [False, True], ids=['literal-UFFFD', 'escaped-UFFFD'])
def test_valid_replacement_character_is_preserved(tmp_path, capsys, escaped):
    value = record(12, 'valid-\ufffd-character')
    p = tmp_path / 'software.jsonl'; p.write_bytes(json.dumps(value, ensure_ascii=escaped).encode('utf-8'))
    assert list(tool.iter_records(p)) == [value]
    assert tool.audit(p)['tokens']['in'] == 12
    assert capsys.readouterr().err == ''

@pytest.mark.parametrize("newline", [b'\n', b'\r\n', b'\r'])
def test_universal_newline_and_physical_numbering_preserved(tmp_path, capsys, newline):
    p = tmp_path / 'software.jsonl'
    p.write_bytes(newline.join([json.dumps(record(10)).encode(), b'{"opaque":"\xff"}', json.dumps(record(20)).encode()]))
    assert tool.audit(p)['tokens']['in'] == 30
    err = capsys.readouterr().err
    assert err.count('SESSION_COST_PARTIAL') == 1 and ':2:' in err


def test_decode_skips_remain_successful_cli_partial_result(tmp_path, monkeypatch, capsys):
    p = tmp_path / 'sessionA.jsonl'; p.write_bytes(json.dumps(record()).encode() + b'\n{"opaque":"PRIVATE_\xff"}')
    output = tmp_path / 'result.tsv'
    monkeypatch.setattr(sys, 'argv', ['session_cost_audit', '--proj', str(tmp_path), '--tsv', str(output)])
    assert tool.main() == 0
    capture = capsys.readouterr()
    assert 'SESSION_COST_PARTIAL' in capture.err and 'PRIVATE_' not in capture.err
    assert output.read_text().splitlines()[1].split('\t')[2] == '12'
