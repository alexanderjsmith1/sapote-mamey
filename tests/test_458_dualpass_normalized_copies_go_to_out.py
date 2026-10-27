"""dualpass --out keeps every write out of the input folders, and a rerun refuses cleanly.

Before: the two *_norm.tsv copies were written beside the input ledgers even with --out, and a
second run into the same folder crashed with a raw FileExistsError.
"""
import argparse
from pathlib import Path

from mamey import dualpass_ledger as dl

HEADER = "task\tstrain\tbgc_id\tlocus_tag\tassertion_type\tvalue\tevidence\tconfidence\n"
ROW = "t1\tAS-9001\tBGC001\tctg1_1\tlead_flag\tlead\tsaved table\thigh\n"


def _ledgers(folder):
    folder.mkdir()
    a, b = folder / "ledger.tsv", folder / "ledger.txt"   # same stem: used to collide on ledger_norm.tsv
    a.write_text(HEADER + ROW); b.write_text(HEADER + ROW)
    return a, b


def test_out_keeps_input_folder_untouched(tmp_path):
    a, b = _ledgers(tmp_path / "inputs")
    before = sorted(p.name for p in (tmp_path / "inputs").iterdir())
    res = dl.merge(str(a), str(b), out_dir=str(tmp_path / "out"), normalize=True)
    assert sorted(p.name for p in (tmp_path / "inputs").iterdir()) == before
    written = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert written == ["DIVERGENCE.tsv", "claude_ledger_norm.tsv", "codex_ledger_norm.tsv"]
    assert res["AGREE"] == 1


def test_rerun_into_same_out_refuses_cleanly(tmp_path, capsys):
    a, b = _ledgers(tmp_path / "inputs")
    args = argparse.Namespace(claude=str(a), codex=str(b), out=str(tmp_path / "out"), no_normalize=False, miscalls=None)
    assert dl.dualpass_command(args) == 0
    assert dl.dualpass_command(args) == 1
    assert "choose a new --out folder" in capsys.readouterr().err


def test_default_still_writes_beside_the_claude_ledger(tmp_path):
    a, b = _ledgers(tmp_path / "inputs")
    dl.merge(str(a), str(b), normalize=True)
    assert (tmp_path / "inputs" / "claude_ledger_norm.tsv").is_file()
