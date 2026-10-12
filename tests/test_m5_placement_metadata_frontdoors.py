"""Real CLI/parser forwarding and report outcomes; synthetic child boundaries only."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from tools import phylo_place as native, phylo_autopilot as autopilot
from .test_m5_placement_metadata_contract import table
from .test_m5_restored_graft_receipt import fixture_sources
from .test_m5_placement_display_length_admission import setup_native, native_args


def owner(tmp_path):
    return table(tmp_path/"owner table.tsv", [dict(tip="PUBLIC_QUERY_01", label="Synthetic query", source_category="Soil", geography_category="Europe")])


def test_actual_all_parser_keeps_build_scalar_separate_and_forwards_report_lists(tmp_path, monkeypatch):
    path = owner(tmp_path)
    captured = []
    monkeypatch.setattr(native, "cmd_all", lambda args: captured.append(args) or 0)
    monkeypatch.setattr(sys, "argv", ["phylo_place.py", "all", "ref.fasta", "--group", "synthetic", "--query", "q.fasta",
                                    "--reference-metadata", "build metadata.tsv", "--owner-table", path,
                                    "--resolved", "resolved one.tsv", "--resolved", "resolved two.tsv", "--reviewed", "reviewed.tsv"])
    assert native.main() == 0
    args = captured[0]
    assert args.reference_metadata == "build metadata.tsv"
    assert args.resolved_metadata == ["resolved one.tsv", "resolved two.tsv"]
    assert args.owner_table == [path] and args.reviewed == ["reviewed.tsv"]


def test_report_legacy_reference_metadata_is_repeatable_resolved_alias(monkeypatch):
    captured = []
    monkeypatch.setattr(native, "cmd_report", lambda args: captured.append(args) or 0)
    monkeypatch.setattr(sys, "argv", ["phylo_place.py", "report", "--jplace", "input.jplace", "--reference-metadata", "one.tsv", "--resolved", "two.tsv"])
    assert native.main() == 0
    assert captured[0].resolved_metadata == ["one.tsv", "two.tsv"]


def test_all_invalid_metadata_refuses_before_build_or_place(tmp_path, monkeypatch):
    args = SimpleNamespace(owner_table=[str(tmp_path/"missing.tsv")], threads=1, refpkg=None, outdir=str(tmp_path/"output"))
    monkeypatch.setattr(native, "cmd_build_ref", lambda *a: pytest.fail("build started before metadata preflight"))
    monkeypatch.setattr(native, "cmd_place", lambda *a: pytest.fail("place started before metadata preflight"))
    with pytest.raises(ValueError, match="PATH_INVALID"):
        native.cmd_all(args)
    assert not (tmp_path/"output").exists()


def test_autopilot_actual_run_forwards_whole_metadata_paths_to_all(tmp_path, monkeypatch):
    query = tmp_path/"q.fasta"; query.write_text(">PUBLIC_QUERY_01\n" + "ACGT"*350 + "\n")
    path = owner(tmp_path)
    reference_metadata = table(tmp_path/"build metadata.tsv", [dict(tip="SYNTHETIC_REF", taxon="Genus alpha", role="reference")])
    resolved = table(tmp_path/"resolved table.tsv", [dict(exact_accession="NR_1.1", verification_status="STRAIN_CONFIRMED", isolation_source="soil", location="Italy")])
    monkeypatch.setattr(autopilot, "assign_genus", lambda *a, **k: {"PUBLIC_QUERY_01": {"genus": "Streptomyces", "routing_state": "ASSIGNED", "pident": 99.0, "aln_len": 1400, "title": "synthetic reference"}})
    def build(genera, db, out, **kwargs):
        Path(out).write_text(">SYNTHETIC_REF\nACGT\n"); return 1
    monkeypatch.setattr(autopilot, "build_reference_fasta", build)
    calls = []
    monkeypatch.setattr(autopilot.subprocess, "run", lambda argv, **kw: calls.append((argv, kw)) or SimpleNamespace(returncode=0))
    args = autopilot.build_argparser().parse_args(["run-16s", "--query", str(query), "--db", "synthetic-db", "--group", "streptomyces",
               "--outdir", str(tmp_path/"out"), "--approved-by", "synthetic owner", "--owner-table", path,
               "--resolved", resolved, "--reference-metadata", reference_metadata, "--rscript", "/synthetic/Rscript selected"])
    assert autopilot.cmd_run_16s(args) == 0
    argv, kwargs = calls[0]
    assert argv[2] == "all"
    for flag, value in [("--owner-table", path), ("--resolved", resolved), ("--reference-metadata", reference_metadata), ("--rscript", "/synthetic/Rscript selected")]:
        assert argv[argv.index(flag)+1] == value
    assert "--one-per-species" in argv


def test_autopilot_invalid_metadata_refuses_before_output_or_routing(tmp_path, monkeypatch):
    monkeypatch.setattr(autopilot, "assign_genus", lambda *a, **k: pytest.fail("routing before metadata preflight"))
    args = autopilot.build_argparser().parse_args(["run-16s", "--query", "missing.fa", "--db", "synthetic-db", "--group", "streptomyces",
                 "--outdir", str(tmp_path/"out"), "--dry-run"])
    args.owner_table = [""]
    with pytest.raises(ValueError, match="PATH_EMPTY"):
        autopilot.cmd_run_16s(args)
    assert not (tmp_path/"out").exists()


@pytest.mark.parametrize("requested,state,expected", [(False,"NOT_REQUESTED",0), (True,"HOLD_REQUESTED_STRIPS",2),
                     (True,"RENDERED",0), (True,"RENDERED_WITH_OMISSIONS",0)])
def test_real_report_records_current_requested_outcome_and_exit(tmp_path, monkeypatch, requested, state, expected):
    run, report, sources, calls = fixture_sources(tmp_path, monkeypatch)
    setup_native(monkeypatch, tmp_path)
    args = native_args(report, sources)
    if requested:
        args.owner_table = [owner(tmp_path)]
    monkeypatch.setattr(native, "_grafted_neighborhoods", lambda *a, **k: 0)
    monkeypatch.setattr(native, "_render_tree", lambda *a, **k: None)
    def strip(args, outdir, group, selected, labelmap):
        assert selected.endswith("lengths_restored.newick")
        assert args._report_molecule == "nucleotide"
        assert args._report_query_names == ["QUERY"]
        assert args._report_length_admission["state"] == "PASS_LENGTH_QA"
        return dict(state=state, requested=requested, variants=[], artifacts=[], kept=4, omitted=int(state.endswith("OMISSIONS")))
    monkeypatch.setattr(native, "_color_strips_deliverable", strip)
    assert native.cmd_report(args) == expected
    receipt = json.loads((report/"synthetic_REPORT_ATTEMPT.json").read_text())
    assert receipt["metadata_strips"]["state"] == state
    assert receipt["state"] == ("COMPLETE" if expected == 0 else "HOLD")
    assert receipt["reviewed_type_evidence"]["roles"] == {}
    assert receipt["table_artifacts"]


def test_occupied_report_receipt_refuses_before_length_producer_and_preserves_bytes(tmp_path, monkeypatch):
    run, report, sources, calls = fixture_sources(tmp_path, monkeypatch)
    setup_native(monkeypatch, tmp_path)
    receipt = report/"synthetic_REPORT_ATTEMPT.json"; receipt.write_text("historical receipt")
    from tools import graft_integrity
    monkeypatch.setattr(graft_integrity, "produce_graft_length_evidence", lambda *a, **k: pytest.fail("occupied report entered producer"))
    with pytest.raises(ValueError, match="REPORT_ATTEMPT_EXISTS"):
        native.cmd_report(native_args(report, sources))
    assert receipt.read_text() == "historical receipt" and not (report/"graft_length_evidence").exists()


@pytest.mark.parametrize("command", ["build-ref", "all", "report"])
def test_native_actual_parser_refuses_explicit_empty_metadata_path_before_handler(tmp_path, monkeypatch, command):
    for name in ("cmd_build_ref", "cmd_all", "cmd_report"):
        monkeypatch.setattr(native, name, lambda *args: pytest.fail("handler reached after explicit empty metadata"))
    argv = {"build-ref": ["ref.fa", "--group", "synthetic"],
            "all": ["ref.fa", "--group", "synthetic", "--query", "q.fa"],
            "report": ["--jplace", "p.jplace"]}[command]
    monkeypatch.setattr(sys, "argv", ["phylo_place.py", command, *argv, "--reference-metadata", ""])
    with pytest.raises(SystemExit) as exc:
        native.main()
    assert exc.value.code == 2


def test_actual_report_missing_owner_is_requested_hold_with_durable_tables(tmp_path, monkeypatch):
    run, report, sources, calls = fixture_sources(tmp_path, monkeypatch)
    setup_native(monkeypatch, tmp_path)
    args = native_args(report, sources)
    args.resolved_metadata = [table(tmp_path/"resolved.tsv", [dict(exact_accession="NR_1.1", verification_status="STRAIN_CONFIRMED", isolation_source="soil", location="Italy")])]
    monkeypatch.setattr(native, "_grafted_neighborhoods", lambda *a, **k: 0)
    monkeypatch.setattr(native, "_render_tree", lambda *a, **k: None)
    assert native.cmd_report(args) == 2
    summary = json.loads((report/"synthetic_REPORT_ATTEMPT.json").read_text())
    assert summary["metadata_strips"]["state"] == "HOLD_PREREQUISITE_MISSING"
    assert summary["metadata_strips"]["requested"]
    assert (report/"synthetic_placements.tsv").is_file()
    assert not (report/"color_strips").exists()


def test_late_metadata_change_retains_explicit_report_hold(tmp_path, monkeypatch):
    run, report, sources, calls = fixture_sources(tmp_path, monkeypatch)
    setup_native(monkeypatch, tmp_path)
    args = native_args(report, sources); path = owner(tmp_path); args.owner_table = [path]
    monkeypatch.setattr(native, "_grafted_neighborhoods", lambda *a, **k: 0)
    monkeypatch.setattr(native, "_render_tree", lambda *a, **k: None)
    def mutate(*args):
        Path(path).write_text("changed after source admission")
        return dict(state="RENDERED", requested=True, variants=[], artifacts=[])
    monkeypatch.setattr(native, "_color_strips_deliverable", mutate)
    assert native.cmd_report(args) == 2
    summary = json.loads((report/"synthetic_REPORT_ATTEMPT.json").read_text())
    assert summary["state"] == "HOLD" and "metadata changed" in summary["reason"]
    assert summary["metadata_source_bindings"][path]["sha256"]
