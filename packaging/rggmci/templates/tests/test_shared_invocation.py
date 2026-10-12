"""Shared high-level defaults and canonical schema; offline synthetic records only."""
import csv
import io
import json
import zipfile
from pathlib import Path

import pytest
from rggmci import run
from rggmci import core
from rggmci.ref_completion import tsv_payload


def sample(path):
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_STORED) as z:
        z.writestr("SYNTH_FULL.1.region001.gbk", "\n".join([
            "LOCUS       SYNTH_FULL.1           60 bp    DNA     linear   BCT 01-JAN-2000",
            "DEFINITION  Synthetic metadata only.", "ACCESSION   SYNTH_FULL", "VERSION     SYNTH_FULL.1",
            "FEATURES             Location/Qualifiers", "     region          1..60", '                     /product="other"',
            "ORIGIN", "        1 " + "n" * 60, "//", ""]))
        z.writestr("input.fna", ">SYNTH_FULL.1\n" + "N" * 60 + "\n")
    return path


def test_default_shared_sequence_roster_full_identity_and_explicit_none(tmp_path):
    path = sample(tmp_path / "input.zip")
    automatic = run(path, label="SYNTH_LABEL", reference_completion="off")
    disabled = run(path, label="SYNTH_LABEL", reference_completion="off", contigs=None)
    assert automatic["invocation"]["sequence_context"]["available"] is True
    assert disabled["invocation"]["sequence_context"]["available"] is False
    assert automatic["regions"][0]["identity"] == "SYNTH_LABEL / SYNTH_FULL.1 / region001 / BGC001"
    assert automatic["reference_completion"]["completion_tier"] == "OFF"
    assert automatic["wrapper_context"]["distribution"] == "rggmci"
    assert len(core.canonical_artifacts(automatic, name="input")) == 8


def test_later_row_keys_and_nested_evidence_are_not_lost():
    payload = tsv_payload([{"a": 1}, {"a": 2, "later": {"data": [None, 3]}}], [])
    reader = csv.DictReader(io.StringIO(payload.decode()), delimiter="\t")
    rows = list(reader)
    assert reader.fieldnames == ["a", "later"]
    assert json.loads(rows[1]["later"]) == {"data": [None, 3]}


def test_invalid_label_refuses_before_any_analysis(tmp_path):
    with pytest.raises(ValueError, match="LOGICAL_LABEL"):
        run(tmp_path / "not-read.zip", label="\n", reference_completion="off")


def test_cli_label_batch_refuses_before_output(tmp_path):
    from rggmci.cli import main
    a, b = sample(tmp_path / "a.zip"), sample(tmp_path / "b.zip")
    out = tmp_path / "new/results"
    assert main([str(a), str(b), "--label", "ambiguous", "--out-dir", str(out), "--reference-completion", "off"]) == 2
    assert not out.exists()


def test_aggregate_groups_preserve_bound_full_member_identity(tmp_path, monkeypatch):
    from rggmci import cli
    source = sample(tmp_path / "input.zip")
    identity = "SYNTH_LABEL / SYNTH_FULL.1 / region001 / BGC001"
    result = {"regions": [{"identity": identity}], "ranked_pairs": [], "related_locus_pairs": [],
              "candidate_groups": [{"group": "SYNTH_GROUP", "n_regions": 1, "n_contigs": 1,
                  "n_at_contig_ends": 1, "high_pairs": 0, "regions": [{"bgc_id": "BGC001",
                      "contig": "SYNTH_FULL.1", "identity": identity, "products": "other", "edge_status": "Edge"}],
                  "pairs": [], "possible_moderate_links": []}],
              "reference_completion": {"completion_tier": "OFF"}}
    monkeypatch.setattr(cli, "run", lambda *args, **kwargs: result)
    out = tmp_path / "results"
    assert cli.main([str(source), "--out-dir", str(out), "--reference-completion", "off"]) == 0
    rows = list(csv.DictReader(io.StringIO((out / "CANDIDATE_GROUPS.tsv").read_text()), delimiter="\t"))
    assert rows[0]["regions"] == identity + " [other] Edge"


def test_public_run_refuses_snapshot_override_before_archive_read(tmp_path):
    with pytest.raises(ValueError, match="PUBLIC_SNAPSHOT_OVERRIDE_REFUSED"):
        run(tmp_path / "not-read.zip", core_snapshot={"records": [], "records_sha256": "caller supplied"})
