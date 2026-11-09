"""dualpass merge refuses an output that is one of its inputs, and never replaces an earlier output.

Before: an input ledger named DIVERGENCE.tsv inside the output folder was read, then replaced by
the divergence report, and `merge` returned success.
"""
import argparse
import os

import pytest

from mamey import dualpass_ledger as dl

HEADER = "task\tstrain\tbgc_id\tlocus_tag\tassertion_type\tvalue\tevidence\tconfidence\n"
ROW = "t1\tSYN-1\tBGC001\tctg1_1\tlead_flag\tlead\tsaved table\thigh\n"


@pytest.mark.parametrize("normalize", [True, False])
def test_input_named_divergence_in_the_out_folder_is_refused(tmp_path, normalize):
    out = tmp_path / "out"
    out.mkdir()
    first = out / "DIVERGENCE.tsv"
    second = tmp_path / "other.tsv"
    first.write_text(HEADER + ROW)
    second.write_text(HEADER + ROW)
    with pytest.raises(dl.DualpassOutputAliasesInput):
        dl.merge(str(first), str(second), out_dir=str(out), normalize=normalize)
    assert first.read_text() == HEADER + ROW
    assert sorted(p.name for p in out.iterdir()) == ["DIVERGENCE.tsv"]


def test_input_reached_through_a_hard_link_is_refused(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    source = tmp_path / "claude.tsv"
    source.write_text(HEADER + ROW)
    os.link(source, out / "DIVERGENCE.tsv")
    with pytest.raises(dl.DualpassOutputAliasesInput):
        dl.merge(str(source), str(source), out_dir=str(out), normalize=False)
    assert source.read_text() == HEADER + ROW


def test_command_reports_the_alias_and_exits_1(tmp_path, capsys):
    out = tmp_path / "out"
    out.mkdir()
    first = out / "DIVERGENCE.tsv"
    first.write_text(HEADER + ROW)
    second = tmp_path / "b.tsv"
    second.write_text(HEADER + ROW)
    args = argparse.Namespace(claude=str(first), codex=str(second), out=str(out),
                              no_normalize=True, miscalls=None)
    assert dl.dualpass_command(args) == 1
    assert "is one of its inputs" in capsys.readouterr().err
    assert first.read_text() == HEADER + ROW


def test_existing_divergence_report_is_not_replaced_without_normalize(tmp_path, capsys):
    a, b = tmp_path / "a.tsv", tmp_path / "b.tsv"
    a.write_text(HEADER + ROW)
    b.write_text(HEADER + ROW)
    args = argparse.Namespace(claude=str(a), codex=str(b), out=str(tmp_path / "out"),
                              no_normalize=True, miscalls=None)
    assert dl.dualpass_command(args) == 0
    report = (tmp_path / "out" / "DIVERGENCE.tsv").read_text()
    assert dl.dualpass_command(args) == 1
    assert "choose a new --out folder" in capsys.readouterr().err
    assert (tmp_path / "out" / "DIVERGENCE.tsv").read_text() == report


def test_fresh_out_folder_still_works(tmp_path):
    a, b = tmp_path / "a.tsv", tmp_path / "b.tsv"
    a.write_text(HEADER + ROW)
    b.write_text(HEADER + ROW)
    res = dl.merge(str(a), str(b), out_dir=str(tmp_path / "out"), normalize=True)
    assert res["AGREE"] == 1
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        "DIVERGENCE.tsv", "claude_a_norm.tsv", "codex_b_norm.tsv"]
