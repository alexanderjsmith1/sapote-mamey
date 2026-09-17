"""Generic, offline checks for the optional antiSMASH-to-MLSA route."""

import importlib.util
import json
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "phylo_mlsa_from_antismash", ROOT / "tools/phylo_mlsa_from_antismash.py")
mlsa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mlsa)


def _zip(path, members):
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members:
            archive.writestr(name, data)
    return path


def _assembly():
    return ">contig_one example assembly\nACGTACGTACGT\n>contig_two\nNNNNACGT\n"


def test_plan_selects_full_assembly_without_writing(tmp_path, capsys):
    source = _zip(tmp_path / "antismash.zip", [
        ("input/example.fna", _assembly()),
        ("example.region001.gbk", "region-only fixture"),
    ])
    assert mlsa.main(["--input-zip", str(source), "--query-label", "QUERY_A",
                      "--min-bp", "20"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["assembly_members"] == ["input/example.fna"]
    assert "completeness requires user review" in plan["assembly_scope"]
    assert plan["query_bp"] == 20 and plan["query_contigs"] == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == ["antismash.zip"]


def test_prepare_stages_query_and_reference_with_receipt(tmp_path, capsys):
    source = _zip(tmp_path / "antismash.zip", [("input/example.fna", _assembly())])
    refs = tmp_path / "references"
    refs.mkdir()
    (refs / "REFERENCE_A.fna").write_text(">ref\nACGTACGTACGT\n")
    out = tmp_path / "mlsa_stage"
    assert mlsa.main(["--input-zip", str(source), "--query-label", "QUERY_A",
                      "--references-dir", str(refs), "--outdir", str(out),
                      "--min-bp", "20", "--mode", "prepare"]) == 0
    assert Path(capsys.readouterr().out.strip()) == out / "mlsa_antismash_receipt.json"
    receipt = json.loads((out / "mlsa_antismash_receipt.json").read_text())
    assert receipt["status"] == "PREPARED"
    assert sorted(p.name for p in (out / "genomes").iterdir()) == [
        "QUERY_A.fna", "REFERENCE_A.fna"]
    assert (out / "genomes/QUERY_A.fna").read_text().startswith(">contig_one\n")
    assert receipt["references"][0]["name"] == "REFERENCE_A.fna"
    # Existing evidence is never reused or overwritten.
    assert mlsa.main(["--input-zip", str(source), "--query-label", "QUERY_A",
                      "--outdir", str(out), "--min-bp", "20",
                      "--mode", "prepare"]) == 1


def test_region_only_and_ambiguous_assemblies_fail_closed(tmp_path):
    region = _zip(tmp_path / "region.zip", [("example.region001.gbk", "region")])
    assert mlsa.main(["--input-zip", str(region), "--query-label", "QUERY_A",
                      "--min-bp", "1"]) == 1
    ambiguous = _zip(tmp_path / "ambiguous.zip", [
        ("input/a.fna", _assembly()), ("input/b.fna", _assembly())])
    assert mlsa.main(["--input-zip", str(ambiguous), "--query-label", "QUERY_A",
                      "--min-bp", "20"]) == 1
    assert mlsa.assembly_from_zip(ambiguous, member="input/a.fna", min_bp=20)[
        "members"] == ["input/a.fna"]


def test_full_genbank_fallback_is_explicit(tmp_path):
    gbk = ("LOCUS       CONTIG_ONE                20 bp    DNA     linear   BCT 01-JAN-2000\n"
           "DEFINITION  Generic full-assembly fixture.\n"
           "ACCESSION   CONTIG_ONE\n"
           "VERSION     CONTIG_ONE\n"
           "FEATURES             Location/Qualifiers\n"
           "     source          1..20\n"
           "                     /organism=\"Example bacterium\"\n"
           "ORIGIN\n"
           "        1 acgtacgtac gtacgtacgt\n"
           "//\n")
    source = _zip(tmp_path / "antismash.zip", [("example.gbk", gbk),
                                              ("example.region001.gbk", "region-only fixture")])
    assembly = mlsa.assembly_from_zip(source, min_bp=20)
    assert assembly["members"] == ["example.gbk"]
    assert assembly["total_bp"] == 20


def test_duplicate_member_refused(tmp_path):
    source = tmp_path / "duplicate.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        _zip(source, [("input/example.fna", _assembly()),
                      ("input/example.fna", _assembly())])
    assert mlsa.main(["--input-zip", str(source), "--query-label", "QUERY_A",
                      "--min-bp", "20"]) == 1


def test_run_requires_nonempty_tree_not_only_zero_exit(tmp_path, monkeypatch):
    source = _zip(tmp_path / "antismash.zip", [("input/example.fna", _assembly())])
    refs = tmp_path / "references"
    refs.mkdir()
    (refs / "REFERENCE_A.fna").write_text(">ref\nACGTACGT\n")
    (refs / "REFERENCE_OUTGROUP.fna").write_text(">ref\nTTTTACGT\n")
    monkeypatch.setattr(mlsa.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0))
    out = tmp_path / "run"
    assert mlsa.main(["--input-zip", str(source), "--query-label", "QUERY_A",
                      "--references-dir", str(refs), "--outdir", str(out),
                      "--min-bp", "20", "--mode", "run"]) == 1
    assert json.loads((out / "mlsa_antismash_receipt.json").read_text())[
        "status"] == "MLSA_FAILED"


def test_launcher_failure_retains_terminal_receipt(tmp_path, monkeypatch):
    source = _zip(tmp_path / "antismash.zip", [("input/example.fna", _assembly())])
    refs = tmp_path / "references"
    refs.mkdir()
    (refs / "REFERENCE_A.fna").write_text(">ref\nACGTACGT\n")
    (refs / "REFERENCE_OUTGROUP.fna").write_text(">ref\nTTTTACGT\n")

    def fail(*_args, **_kwargs):
        raise OSError("simulated companion launch error")

    monkeypatch.setattr(mlsa.subprocess, "run", fail)
    out = tmp_path / "run"
    assert mlsa.main(["--input-zip", str(source), "--query-label", "QUERY_A",
                      "--references-dir", str(refs), "--outdir", str(out),
                      "--min-bp", "20", "--mode", "run"]) == 1
    receipt = json.loads((out / "mlsa_antismash_receipt.json").read_text())
    assert receipt["status"] == "MLSA_LAUNCH_FAILED"
    assert "simulated companion launch error" in receipt["launch_error"]


def test_public_cli_offers_route():
    result = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"),
                             "phylo-mlsa", "--help"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "--input-zip" in result.stdout and "--mode" in result.stdout
