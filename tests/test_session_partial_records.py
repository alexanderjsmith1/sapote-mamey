"""Synthetic transcripts only; never reads user session directories."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest
import mamey
SOURCE = Path(os.environ.get("SAPOTE_TEST_BASELINE_ROOT", str(Path(mamey.__file__).resolve().parent.parent)))
SCRIPT = Path(__file__).resolve().parents[1] / "tools/session_cost_audit.py"
spec = importlib.util.spec_from_file_location("isolated_session_audit", SCRIPT)
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)

def record(tokens=10):
    return {"type": "assistant", "timestamp": "2026-01-01T12:00:00Z", "message": {"role": "assistant", "usage": {"input_tokens": tokens}, "content": []}}

@pytest.mark.parametrize("bad", ["broken SOFTWARE_PRIVATE_CONTENT", '{"type":', '"unterminated'])
@pytest.mark.parametrize("tail", [False, True], ids=["middle", "tail"])
def test_skipped_json_is_explicit_partial_input(tmp_path, capsys, bad, tail):
    p = tmp_path / "software.jsonl"
    text = json.dumps(record()) + "\n\n" + bad
    if not tail: text += "\n" + json.dumps(record(20)) + "\n"
    p.write_text(text); before = p.read_bytes()
    result = tool.audit(p)
    assert result["tokens"]["in"] == (10 if tail else 30)
    assert result["turns"] == (1 if tail else 2)
    output = capsys.readouterr()
    assert not output.out
    assert "SESSION_COST_PARTIAL" in output.err and str(p) in output.err
    assert ":3:" in output.err and "totals cover readable records only" in output.err
    assert "SOFTWARE_PRIVATE_CONTENT" not in output.err
    assert p.read_bytes() == before


def test_valid_and_blank_lines_keep_existing_result_without_warning(tmp_path, capsys):
    p = tmp_path / "software.jsonl"; p.write_text("\n" + json.dumps(record()) + "\n  \n")
    assert list(tool.iter_records(p)) == [record()]
    assert tool.audit(p)["tokens"]["in"] == 10
    assert capsys.readouterr().err == ""


def test_partial_cli_retains_exit_zero_and_tsv_schema(tmp_path, monkeypatch, capsys):
    p = tmp_path / "sessionA.jsonl"; p.write_text(json.dumps(record(12)) + "\n{broken tail")
    before = p.read_bytes(); output = tmp_path / "result.tsv"
    monkeypatch.setattr(sys, "argv", ["session_cost_audit", "--proj", str(tmp_path), "--tsv", str(output)])
    assert tool.main() == 0
    captured = capsys.readouterr()
    assert "SESSION_COST_PARTIAL" in captured.err and ":2:" in captured.err
    assert "LIFETIME" in captured.out and "wrote" in captured.out
    rows = output.read_text().splitlines()
    assert rows[0] == "session\tchat\ttotal\tcache_read\tcache_write\toutput\tturns\ttok_per_turn\tsubagents\tfiles_written"
    assert rows[1].split('\t')[2:] == ['12', '0', '0', '0', '1', '12', '0', '0']
    assert p.read_bytes() == before


def test_existing_broad_skip_is_preserved_but_visible(tmp_path, monkeypatch, capsys):
    p = tmp_path / "software.jsonl"; p.write_text('{}\n')
    def broken(value): raise RuntimeError("PRIVATE_EXCEPTION_CONTENT")
    monkeypatch.setattr(tool.json, "loads", broken)
    assert list(tool.iter_records(p)) == []
    err = capsys.readouterr().err
    assert "SESSION_COST_PARTIAL" in err and "PRIVATE_EXCEPTION_CONTENT" not in err

@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink", "existing"])
def test_existing_source_output_admission_is_retained(tmp_path, monkeypatch, alias):
    p = tmp_path / "software.jsonl"; p.write_text(json.dumps(record()) + "\n")
    output = tmp_path / "result.tsv"
    if alias == "direct": output = p
    elif alias == "symlink": output.symlink_to(p)
    elif alias == "hardlink": os.link(p, output)
    else: output.write_text("existing output")
    before = output.read_bytes(); source_before = p.read_bytes()
    monkeypatch.setattr(sys, "argv", ["session_cost_audit", "--proj", str(tmp_path), "--tsv", str(output)])
    assert tool.main() == 2
    assert output.read_bytes() == before and p.read_bytes() == source_before


def test_multiple_skips_report_each_physical_line(tmp_path, capsys):
    p = tmp_path / "software.jsonl"; p.write_text("{bad\n\n{also bad\n" + json.dumps(record()) + "\n")
    assert tool.audit(p)["tokens"]["in"] == 10
    err = capsys.readouterr().err
    assert err.count("SESSION_COST_PARTIAL") == 2 and ":1:" in err and ":3:" in err

@pytest.mark.parametrize("partial", [False, True], ids=["valid", "partial"])
def test_stdout_and_tsv_are_byte_compatible_with_baseline(tmp_path, monkeypatch, capsys, partial):
    spec = importlib.util.spec_from_file_location("original_session_for_parity", SOURCE / "tools/session_cost_audit.py")
    original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
    if (SOURCE / "tools/session_cost_audit.py").resolve() == SCRIPT.resolve():
        pytest.skip("no separate baseline tree: SAPOTE_TEST_BASELINE_ROOT points at the candidate itself")
    p = tmp_path / "sessionA.jsonl"
    p.write_text(json.dumps(record(12)) + ("\n{broken tail" if partial else "\n"))
    outputs = []
    for module, name in [(original, "baseline.tsv"), (tool, "candidate.tsv")]:
        target = tmp_path / name
        monkeypatch.setattr(sys, "argv", ["session_cost_audit", "--proj", str(tmp_path), "--tsv", str(target)])
        assert module.main() == 0
        captured = capsys.readouterr()
        outputs.append((captured.out.replace(str(target), "OUTPUT.tsv"), target.read_bytes(), captured.err))
    assert outputs[0][:2] == outputs[1][:2]
    assert outputs[0][2] == ""
    assert bool(outputs[1][2]) is partial


@pytest.mark.parametrize("kind", ["value", "runtime", "json"])
def test_consumer_throw_is_not_reported_as_unreadable_record(tmp_path, capsys, kind):
    p = tmp_path / "software.jsonl"
    p.write_text(json.dumps(record(10)) + "\n" + json.dumps(record(20)) + "\n")
    before = p.read_bytes()
    records = tool.iter_records(p)
    assert next(records) == record(10)
    if kind == "json":
        failure = json.JSONDecodeError("PRIVATE_CONSUMER_ERROR", "PRIVATE_CONTENT", 0)
    else:
        failure = (ValueError if kind == "value" else RuntimeError)("PRIVATE_CONSUMER_ERROR")
    with pytest.raises(type(failure)) as caught:
        records.throw(failure)
    assert caught.value is failure
    output = capsys.readouterr()
    assert output.out == output.err == ""
    assert p.read_bytes() == before


def test_consumer_close_does_not_warn(tmp_path, capsys):
    p = tmp_path / "software.jsonl"; p.write_text(json.dumps(record()) + "\n")
    records = tool.iter_records(p)
    assert next(records) == record()
    records.close()
    assert capsys.readouterr().err == ""
