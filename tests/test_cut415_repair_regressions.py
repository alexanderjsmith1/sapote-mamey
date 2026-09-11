"""Bounded 415 repair regressions with isolated synthetic inputs."""
import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(rel, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / Path(rel).parent))
    spec = importlib.util.spec_from_file_location("cut415_" + Path(rel).stem, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("channel", ["nr", "swissprot", "clustered_nr"])
def test_ingest_writers_agree_on_hsp_length_and_preserve_unknown_query_length(tmp_path, monkeypatch, channel):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    mod = _load("deliverable_tools/ingest_blastp.py", monkeypatch)
    monkeypatch.setattr(mod, "EXCLUDE", set())
    raw = tmp_path / "raw"; raw.mkdir()
    source = raw / "synthetic-Alignment-HitTable.csv"
    with source.open("w", newline="") as handle:
        csv.writer(handle).writerow(["SYNTHETIC-001__NODE_1_length_10000_cov_10__region001__BGC001__gene1", "TEST000001.1", "87", "340", "0", "0", "1", "340", "1", "340", "1e-20", "250", "90"])
    monkeypatch.setattr(sys, "argv", ["ingest", "--raw", str(raw), "--repo", str(tmp_path / "repo"), "--master", str(tmp_path / "master"), "--channel", channel, "--date", "2026-01-01"])
    mod.main()
    outputs = list((tmp_path / "repo").rglob("*.csv")) + list((tmp_path / "master").rglob("*.csv"))
    assert len(outputs) == 4
    for output in outputs:
        with output.open() as handle: rows = list(csv.DictReader(handle))
        assert len(rows) == 1
        assert rows[0]["align_length"] == "340"
        assert rows[0]["aa_length"] == rows[0]["query_coverage"] == ""
        assert rows[0]["pct_identity"] == "87" and rows[0]["pct_positives"] == "90"


def test_asset_without_cosmetic_note_still_blocks_redundant_fetch(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    mod = _load("tools/find_asset.py", monkeypatch)
    registry = tmp_path / "registry.tsv"
    registry.write_text("asset_id\tkind\tpath\tsize\tguard_tokens\tnote\nlocal_ref\treference\tref.fa\t10\tunique-reference\nshort\tbroken\n")
    monkeypatch.setattr(mod, "REG", registry)
    assert mod.main(["--check", "curl unique-reference"]) == 3
    output = capsys.readouterr()
    assert "no trailing note; retained" in output.err and "fewer than 5 columns" in output.err
    assert mod.rows()[0]["note"] == ""
    assert mod.main(["--check", "cat unique-reference"]) == 0


@pytest.mark.parametrize("value", [None, ""])
def test_inspector_rejects_missing_native_strain(tmp_path, value):
    from mamey.package_inspector import bgc_json_list_from_board
    from mamey.exact_identity import ExactLocusIdentityError
    row = dict(Strain="SYNTHETIC-001", Contig="NODE_1_length_40000", Node_ID="NODE_1_length_40000", antiSMASH_Region="region001", BGC_ID="BGC001")
    if value is None: del row["Strain"]
    else: row["Strain"] = value
    board = tmp_path / "SYNTHETIC-001_4_triage_board.csv"
    with board.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row)); writer.writeheader(); writer.writerow(row)
    with pytest.raises(ExactLocusIdentityError): bgc_json_list_from_board(board)


def test_malformed_render_command_blocks_with_hook_exit_two(tmp_path):
    result = subprocess.run(["bash", str(ROOT / "hooks/require_phylo_workflow.sh")], input=json.dumps({"tool_input": {"command": 'render_clean_tree "unterminated.nwk'}}), text=True, capture_output=True, env=dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(tmp_path)))
    assert result.returncode == 2 and "cannot parse" in result.stderr


def test_blast_concurrency_hook_still_denies_at_cap_after_json_port(tmp_path):
    binary = tmp_path / "ps"
    binary.write_text("#!/bin/sh\nprintf '%s\\n' '/tmp/python3 /tmp/nr_rid_runner.py run'\n")
    binary.chmod(0o755)
    result = subprocess.run(["bash", str(ROOT / "hooks/block_blastp_overconcurrency.sh")], input=json.dumps({"tool_input": {"command": "nr_rid_runner.py run"}}), text=True, capture_output=True, env=dict(os.environ, PATH=str(tmp_path)+os.pathsep+os.environ["PATH"], SAPOTE_BLASTP_MAX_LANES="1"))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_majority_read_actual_cohort_writer_preserves_existing_file_unless_forced(tmp_path, monkeypatch):
    from mamey.canonical_write_guard import CanonicalOverwriteRefused
    import mamey.exclusions
    monkeypatch.setattr(mamey.exclusions, "raw_analysis_excluded", lambda: set())
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(tmp_path))
    (tmp_path / "sapote-mamey-vSYNTHETIC-CODE-fixture").mkdir()
    mod = _load("deliverable_tools/whole_bgc_majority_read.py", monkeypatch)
    runs = tmp_path / "runs"; runs.mkdir()
    out = tmp_path / "results_2026-01-01"; out.mkdir()
    target = out / "whole_bgc_majority_read_cohort.csv"; target.write_text("retained bytes\n")
    monkeypatch.setattr(mod, "RUNS", runs)
    monkeypatch.setattr(sys, "argv", ["majority", "--cohort", "--out", str(out)])
    monkeypatch.delenv("MAMEY_ALLOW_CANONICAL_OVERWRITE", raising=False)
    with pytest.raises(CanonicalOverwriteRefused): mod.main()
    assert target.read_text() == "retained bytes\n"
    monkeypatch.setattr(sys, "argv", ["majority", "--cohort", "--out", str(out), "--force"])
    assert mod.main() == 0
    assert target.read_text().startswith("strain,")
