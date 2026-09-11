"""CODEX19: bounded, approval-gated GToTree -> IQ-TREE planning."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "plan_gtotree_iqtree.py"
SPEC = importlib.util.spec_from_file_location("plan_gtotree_iqtree", TOOL_PATH)
tool = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = tool
SPEC.loader.exec_module(tool)

PANEL_TOOL_PATH = ROOT / "tools" / "build_phylo_panel.py"
PANEL_SPEC = importlib.util.spec_from_file_location("build_phylo_panel_for_planner_test", PANEL_TOOL_PATH)
panel_tool = importlib.util.module_from_spec(PANEL_SPEC)
assert PANEL_SPEC and PANEL_SPEC.loader
sys.modules[PANEL_SPEC.name] = panel_tool
PANEL_SPEC.loader.exec_module(panel_tool)


def _fasta(records):
    return "".join(f">contig{i}\n{seq}\n" for i, seq in enumerate(records, 1))


def _hmm(tmp_path: Path, n=6) -> Path:
    path = tmp_path / "targets.hmm"
    path.write_text("".join(f"HMMER3/f\nNAME  locus{i}\n//\n" for i in range(n)), encoding="utf-8")
    return path


FIELDS = ["role", "query_id", "strain_id", "label", "assembly_path", "archive_member",
          "accession", "reference_rank", "selection_basis"]


def _panel(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "panel.tsv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _row(path: Path | str, *, role="QUERY", query="Q1", strain="AS-441",
         label="Streptomyces sp. AS-441", rank="", member="", accession=""):
    return {"role": role, "query_id": query, "strain_id": strain, "label": label,
            "assembly_path": str(path), "archive_member": member, "accession": accession,
            "reference_rank": rank, "selection_basis": "ClusterBlast recurrence"}


def _args(tmp_path: Path, panel: Path, **overrides):
    base = dict(panel_tsv=str(panel), prepared_panel=None,
                workspace=str(tmp_path / "work"), run_id="run-001",
                hmm=str(_hmm(tmp_path)), panel_cap=40, references_per_query=3,
                max_concurrent_cores=4, gtotree_bin="/fake/GToTree",
                iqtree_bin="/fake/iqtree3")
    base.update(overrides)
    return SimpleNamespace(**base)


def _outgroup(tmp_path: Path) -> dict:
    path = tmp_path / "outgroup.fna"
    path.write_text(_fasta(["TTTTCCCCAAAAGGGG"]), encoding="utf-8")
    return _row(path, role="OUTGROUP", query="", strain="OUT-1", label="Sister genus outgroup")


@pytest.fixture()
def good_probe(monkeypatch):
    payload = {
        "gtotree": {"status": "PRESENT", "path": "/fake/GToTree",
                     "version": "GToTree v1.8.16", "help_contract": "PASS",
                     "verified_interface": "PASS"},
        "iqtree": {"status": "PRESENT", "path": "/fake/iqtree3",
                   "version": "IQ-TREE 3.1.2", "help_contract": "PASS"},
        "helpers": {name: {"status": "PRESENT", "path": f"/fake/{name}"}
                    for name in ("hmmsearch", "prodigal", "muscle", "gtt-cat-alignments")},
    }
    monkeypatch.setattr(tool, "resolve_executable", lambda explicit, names: explicit)
    monkeypatch.setattr(tool, "resolve_iqtree", lambda explicit=None: explicit)
    monkeypatch.setattr(tool, "probe_toolchain", lambda g, i: payload)
    return payload


def test_defaults_surface_40_and_hard_60():
    parser = tool.build_parser()
    args = parser.parse_args(["plan", "--panel-tsv", "p.tsv", "--workspace", "w",
                              "--run-id", "x", "--hmm", "h.hmm"])
    assert args.panel_cap is None
    assert tool.DEFAULT_PANEL_CAP == 40
    assert args.references_per_query == 3
    assert args.max_concurrent_cores == 4
    assert tool.HARD_PANEL_CAP == 60


@pytest.mark.parametrize("cap", (2, 61))
def test_panel_cap_outside_3_to_60_is_rejected(tmp_path, cap, good_probe):
    q = tmp_path / "q.fna"; q.write_text(_fasta(["ACGT"]), encoding="utf-8")
    args = _args(tmp_path, _panel(tmp_path, [_row(q), _outgroup(tmp_path)]), panel_cap=cap)
    with pytest.raises(ValueError, match="panel-cap"):
        tool.plan(args)
    assert not (tmp_path / "work" / "runs" / "run-001").exists()


def test_reference_selection_is_ranked_and_capped_one_to_three(tmp_path):
    q = _row(tmp_path / "q.fna")
    refs = [_row(tmp_path / f"r{i}.fna", role="REFERENCE", rank=str(i),
                 strain=f"REF-{i}", label=f"Reference {i}") for i in range(1, 6)]
    rows = tool.read_panel(_panel(tmp_path, [q, _outgroup(tmp_path), *refs]))
    selected = tool.select_reference_rows(rows, 3)
    assert [r.strain_id for r in selected] == ["AS-441", "OUT-1", "REF-1", "REF-2", "REF-3"]
    with pytest.raises(ValueError):
        tool.select_reference_rows(rows, 4)


def test_normalized_hash_deduplicates_header_and_contig_order():
    a = _fasta(["AAAACCCC", "GGGGTTTT"]).encode()
    b = ">different\nGGGGTTTT\n>also_different\nAAAACCCC\n".encode()
    assert tool.sha256_bytes(a) != tool.sha256_bytes(b)
    assert tool.normalized_assembly_sha256(a) == tool.normalized_assembly_sha256(b)


def test_relative_assembly_paths_resolve_from_panel_directory(tmp_path):
    q = tmp_path / "q.fna"; q.write_text(_fasta(["ACGT"]), encoding="utf-8")
    panel = _panel(tmp_path, [_row("q.fna")])
    assert tool.read_panel(panel)[0].assembly_path == str(q.resolve())


def test_prepared_panel_is_canonical_ingress_and_hash_contract_matches(tmp_path, good_probe):
    sources = tmp_path / "sources"
    sources.mkdir()
    for name, sequence in (("q", "AAAA"), ("r", "CCCC"), ("o", "GGGG")):
        (sources / f"{name}.fna").write_text(_fasta([sequence]), encoding="utf-8")
    manifest = tmp_path / "candidates.tsv"
    fields = ["candidate_id", "role", "source_path", "source_member", "priority",
              "cohort", "taxonomy", "display_label", "tree_label", "selection_basis",
              "related_query_ids", "reference_status"]
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows([
            {"candidate_id": "AS-441", "role": "QUERY", "source_path": "sources/q.fna",
             "tree_label": "AS-441", "display_label": "Streptomyces sp. AS-441"},
            {"candidate_id": "REF-1", "role": "REFERENCE", "source_path": "sources/r.fna",
             "tree_label": "REF-1", "selection_basis": "curator comparator",
             "related_query_ids": "AS-441"},
            {"candidate_id": "OUT-1", "role": "OUTGROUP", "source_path": "sources/o.fna",
             "tree_label": "OUT-1"},
        ])
    prepared = tmp_path / "prepared"
    panel_tool.build(manifest, prepared, 3, 3)
    rows, meta = tool.read_prepared_panel(prepared, 3)
    assert len(rows) == 3 and meta["role_counts"] == {
        "QUERY": 1, "REFERENCE": 1, "OUTGROUP": 1
    }
    for row in rows:
        data = Path(row.assembly_path).read_bytes()
        assert tool.normalized_assembly_sha256(data) in {
            source["content_sha256"] for source in csv.DictReader(
                (prepared / "panel_selected.tsv").open(), delimiter="\t"
            )
        }
    args = _args(tmp_path, manifest, panel_tsv=None, prepared_panel=str(prepared), panel_cap=None)
    assert tool.plan(args) == 0
    run_manifest = json.loads(
        (tmp_path / "work/runs/run-001/RUN_MANIFEST.json").read_text(encoding="utf-8")
    )
    assert run_manifest["panel_policy"]["panel_cap_selected_by_user"] == 3
    assert run_manifest["source_panel"]["prepared_panel"]["selected_count"] == 3


def test_plan_stages_one_object_per_normalized_assembly_and_never_runs_tree(
        tmp_path, good_probe, monkeypatch):
    q = tmp_path / "q.fna"; q.write_text(_fasta(["AAAACCCC", "GGGGTTTT"]), encoding="utf-8")
    rdup = tmp_path / "rdup.fna"; rdup.write_text(
        ">x\nGGGGTTTT\n>y\nAAAACCCC\n", encoding="utf-8")
    r2 = tmp_path / "r2.fna"; r2.write_text(_fasta(["ACGTACGT"]), encoding="utf-8")
    panel = _panel(tmp_path, [
        _row(q),
        _outgroup(tmp_path),
        _row(rdup, role="REFERENCE", rank="1", strain="REF-DUP", label="Duplicate reference"),
        _row(r2, role="REFERENCE", rank="2", strain="REF-2", label="Reference 2"),
    ])
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("planner must not launch any analysis subprocess")))
    assert tool.plan(_args(tmp_path, panel)) == 0
    run = tmp_path / "work" / "runs" / "run-001"
    manifest = json.loads((run / "RUN_MANIFEST.json").read_text())
    state = json.loads((run / "RUN_STATE.json").read_text())
    assert manifest["execution_authorized"] is False
    assert manifest["hmm"]["kind"] == "PROTEIN_PROFILE_SET_FOR_GTOTREE"
    assert state["state"] == "PLANNED_AWAITING_APPROVAL"
    assert manifest["panel_policy"]["admitted_unique_assemblies"] == 3
    assert manifest["panel_policy"]["duplicate_rows_excluded"] == 1
    assert len(list((run / "input_objects").glob("*.fna"))) == 3
    command = (run / "COMMAND.sh").read_text()
    assert "-j 1 -n 1 -M 1 -N -k" in command
    assert "-T 1" in command
    assert "<DISCOVERED_ALIGNMENT_PATH>" in command
    assert "-f input_view/genomes.txt" in command
    assert "-H resources/" in command
    assert all(" " not in line for line in (run / "input_view/genomes.txt").read_text().splitlines())
    labels = (run / "input_view" / "labels.tsv").read_text().splitlines()
    assert len(labels) == 3 and not labels[0].startswith("input\t")
    assert labels[0].endswith("\tStreptomyces sp. AS-441")


def test_zip_member_is_hashed_and_source_archive_is_unchanged(tmp_path, good_probe):
    archive = tmp_path / "antismash.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("whole_genome.fna", _fasta(["ACGTACGTACGT"]))
        zf.writestr("x.region001.gbk", "LOCUS x\n")
    before = tool.file_sha256(archive)
    panel = _panel(tmp_path, [_row(archive, member="whole_genome.fna"), _outgroup(tmp_path)])
    assert tool.plan(_args(tmp_path, panel)) == 0
    manifest = json.loads((tmp_path / "work/runs/run-001/RUN_MANIFEST.json").read_text())
    assert manifest["assemblies"][0]["source_type"] == "zip_member"
    assert manifest["assemblies"][0]["archive_member"] == "whole_genome.fna"
    assert tool.file_sha256(archive) == before


def test_accession_without_local_assembly_is_network_hold_not_download(tmp_path, good_probe):
    q = tmp_path / "q.fna"; q.write_text(_fasta(["ACGTACGT"]), encoding="utf-8")
    rows = [_row(q), _outgroup(tmp_path), _row("", role="REFERENCE", rank="1", strain="GCF_1",
                          label="Reference accession", accession="GCF_000000001.1")]
    rc = tool.plan(_args(tmp_path, _panel(tmp_path, rows)))
    run = tmp_path / "work/runs/run-001"
    state = json.loads((run / "RUN_STATE.json").read_text())
    assert rc == 2 and state["state"] == "HOLD_NETWORK_APPROVAL"
    assert json.loads((run / "RUN_MANIFEST.json").read_text())["network_inputs_pending"]


def test_duplicate_query_is_explicit_hold(tmp_path, good_probe):
    a = tmp_path / "a.fna"; a.write_text(_fasta(["ACGTACGT"]), encoding="utf-8")
    b = tmp_path / "b.fna"; b.write_text(">renamed\nACGTACGT\n", encoding="utf-8")
    rows = [_row(a, query="Q1", strain="AS-921", label="Streptomyces sp. AS-921"),
            _outgroup(tmp_path),
            _row(b, query="Q2", strain="SID10815", label="Streptomyces sp. SID10815")]
    rc = tool.plan(_args(tmp_path, _panel(tmp_path, rows)))
    run = tmp_path / "work/runs/run-001"
    assert rc == 2
    assert json.loads((run / "RUN_STATE.json").read_text())["state"] == "HOLD_DUPLICATE_QUERY_REVIEW"
    duplicates = (run / "qa/DUPLICATES.tsv").read_text()
    assert "NORMALIZED_ASSEMBLY_SHA256_DUPLICATE" in duplicates and "SID10815" in duplicates


def test_existing_run_is_never_overwritten(tmp_path, good_probe):
    q = tmp_path / "q.fna"; q.write_text(_fasta(["ACGT"]), encoding="utf-8")
    panel = _panel(tmp_path, [_row(q), _outgroup(tmp_path)])
    args = _args(tmp_path, panel)
    assert tool.plan(args) == 0
    manifest = tmp_path / "work/runs/run-001/RUN_MANIFEST.json"
    before = tool.file_sha256(manifest)
    with pytest.raises(FileExistsError, match="resume"):
        tool.plan(args)
    assert tool.file_sha256(manifest) == before


def test_iqtree_resolution_order_and_explicit_override(monkeypatch, tmp_path):
    explicit = tmp_path / "iq-special"; explicit.write_text("x")
    explicit.chmod(0o755)
    assert tool.resolve_iqtree(str(explicit)) == str(explicit.resolve())
    monkeypatch.setattr(tool.shutil, "which", lambda name: f"/bin/{name}" if name in {"iqtree2", "iqtree"} else None)
    # resolve_executable canonicalises via Path.resolve(); on usrmerge Linux /bin -> usr/bin, so
    # compare against the resolved form of the expected pick (intent: iqtree2 wins over iqtree).
    from pathlib import Path as _P
    assert tool.resolve_iqtree() == str(_P("/bin/iqtree2").resolve())


def test_probe_only_uses_version_and_help(monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv[0].endswith("GToTree"):
            text = "GToTree v1.8.16" if argv[1] == "-v" else " ".join(tool.REQUIRED_GTOTREE_HELP)
        else:
            text = "IQ-TREE 3.1.2" if argv[1] == "--version" else " ".join(tool.REQUIRED_IQTREE_HELP)
        return SimpleNamespace(stdout=text, stderr="", returncode=0)

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    result = tool.probe_toolchain("/x/GToTree", "/x/iqtree3")
    assert result["gtotree"]["verified_interface"] == "PASS"
    assert result["gtotree"]["help_contract"] == result["iqtree"]["help_contract"] == "PASS"
    assert calls == [["/x/GToTree", "-v"], ["/x/GToTree", "-h"],
                     ["/x/iqtree3", "--version"], ["/x/iqtree3", "-h"]]


def test_discovery_finds_observed_alignment_without_assuming_filename(tmp_path):
    run = tmp_path / "run"
    out = run / "outputs/gtotree_alignment"
    out.mkdir(parents=True)
    (run / "RUN_MANIFEST.json").write_text(json.dumps({
        "run_id": "x", "panel_policy": {"admitted_unique_assemblies": 3}
    }), encoding="utf-8")
    (out / "Genomes_summary_info.tsv").write_text(
        "genome\tstatus\na\tok\nb\tok\n", encoding="utf-8")
    arbitrary = out / "observed_name_without_convention.aln"
    arbitrary.write_text(">a\nAAAA\n>b\nAAAA\n", encoding="utf-8")
    individual = out / "run_files/individual_alignments/locus1.faa"
    individual.parent.mkdir(parents=True)
    individual.write_text(">a\nAA\n>b\nAA\n", encoding="utf-8")
    receipt = tmp_path / "receipt.json"
    rc = tool.discover_outputs(SimpleNamespace(run_dir=str(run), receipt=str(receipt)))
    data = json.loads(receipt.read_text())
    assert rc == 0 and data["status"] == "PASS_UNIQUE_ALIGNMENT"
    assert data["retained_taxa_from_summary"] == 2
    assert data["alignment_candidates"][0]["path"] == str(arbitrary)
    assert data["alignment_candidates"][0]["sha256"] == tool.file_sha256(arbitrary)


def test_discovery_holds_when_two_root_alignments_are_plausible(tmp_path):
    run = tmp_path / "run"; out = run / "outputs/gtotree_alignment"; out.mkdir(parents=True)
    (run / "RUN_MANIFEST.json").write_text(json.dumps({
        "run_id": "x", "panel_policy": {"admitted_unique_assemblies": 2}
    }))
    (out / "Genomes_summary_info.tsv").write_text("g\ts\na\tok\nb\tok\n")
    for name in ("one", "two"):
        (out / name).write_text(">a\nAA\n>b\nAA\n")
    assert tool.discover_outputs(SimpleNamespace(run_dir=str(run), receipt=None)) == 2


def test_command_never_contains_overwrite_or_auto_threads(tmp_path):
    text = tool._command_text(tmp_path, Path("resources/h.hmm"), "GToTree", "iqtree3")
    assert " -F " not in text and "--redo" not in text and "-T AUTO" not in text
    assert "-j 1 -n 1 -M 1" in text and "-T 1" in text
