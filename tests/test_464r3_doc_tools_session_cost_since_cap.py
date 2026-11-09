"""Synthetic transcripts only: --since reads the same file cap as other filters and says what it left out."""
import json
import os
import sys

from tools import session_cost_audit as mod


def _sessions(tmp_path, n):
    for i in range(n):
        p = tmp_path / f"{i:08d}-session.jsonl"
        p.write_text(json.dumps({"timestamp": "2026-01-02T00:00:00Z", "type": "assistant",
                                 "message": {"usage": {"input_tokens": 1, "output_tokens": 1}}}) + "\n")
        os.utime(p, (1_700_000_000 + i, 1_700_000_000 + i))


def _run(monkeypatch, capsys, *args):
    monkeypatch.setattr(sys, "argv", ["session_cost_audit", *args])
    code = mod.main()
    return code, capsys.readouterr().out


def test_since_reads_more_than_25_files(tmp_path, monkeypatch, capsys):
    _sessions(tmp_path, 26)
    code, out = _run(monkeypatch, capsys, "--proj", str(tmp_path), "--since", "2026-01-01T00:00:00Z")
    assert code == 0
    assert "read all 26 matching session file(s)" in out
    assert sum(1 for line in out.splitlines() if "-se" in line or "(0000" in line) == 26


def test_unfiltered_cap_reports_omitted_files(tmp_path, monkeypatch, capsys):
    _sessions(tmp_path, 27)
    code, out = _run(monkeypatch, capsys, "--proj", str(tmp_path))
    assert code == 0
    assert "read the newest 25 of 27" in out and "2 older file(s) NOT READ" in out
