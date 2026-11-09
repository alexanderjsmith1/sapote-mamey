"""Chitin evaluation: whole-genome scope is a claim that needs a bound source, not an assertion."""
import importlib.util
import json
from pathlib import Path
import pytest
from mamey import chitin_reference_eval as lib

TOOL = Path(__file__).parents[1] / "tools" / "chitin_reference_eval.py"
REG = "reference_id\treference_taxon\tsource_path\tsource_sha256\tani_pct\taligned_fragment_fraction\n"


def _tool():
    spec = importlib.util.spec_from_file_location("chitin_tool_464r3", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_library_default_is_unresolved_and_note_is_not_an_assertion():
    ev = lib.evaluate_strain("EXAMPLE", {f: 0 for f in lib.CHITIN_FAMILIES}, [], "Streptomyces")
    d = ev.to_dict()
    assert d["source_scope_state"] == "UNRESOLVED_SCOPE_COUNTS_NOT_SOURCE_BOUND"
    assert "not tested absence" in d["zero_count_interpretation"]
    assert not d["scope_note"].startswith("Whole-genome measurement")
    with pytest.raises(lib.ChitinReferenceEvalError):
        lib.evaluate_strain("EXAMPLE", {}, [], "", source_scope_state="WHOLE_GENOME_VERIFIED")


def test_override_json_route_receipt_is_unresolved(tmp_path, capsys):
    counts = tmp_path / "counts.json"; counts.write_text(json.dumps({f: 0 for f in lib.CHITIN_FAMILIES}))
    reg = tmp_path / "reg.tsv"; reg.write_text(REG + "R1\tStreptomyces x\tNR\tNR\t\t\n")
    assert _tool().main(["--cgad-json", str(counts), "--registry", str(reg), "--strain-id", "EXAMPLE"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["source_scope_state"] == "UNRESOLVED_SCOPE_COUNTS_NOT_SOURCE_BOUND"
    assert "Whole-genome measurement" not in out["scope_note"]


def test_package_route_names_the_scan_record_but_not_coverage(tmp_path, capsys):
    pkg = tmp_path / "pkg"; pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "EXAMPLE", "taxonomy": "Streptomyces",
        "source_scans": {"chitinase": {"counts": {"GH18": 2}}}}))
    reg = tmp_path / "reg.tsv"; reg.write_text(REG + "R1\tStreptomyces x\tNR\tNR\t\t\n")
    assert _tool().main(["--package", str(pkg), "--registry", str(reg)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["source_scope_state"] == "PACKAGE_MANIFEST_SCAN_RECORD_COVERAGE_UNREVIEWED"


def test_out_json_aliasing_the_counts_input_is_refused(tmp_path):
    counts = tmp_path / "counts.json"; counts.write_text(json.dumps({f: 0 for f in lib.CHITIN_FAMILIES}))
    before = counts.read_text()
    reg = tmp_path / "reg.tsv"; reg.write_text(REG + "R1\tStreptomyces x\tNR\tNR\t\t\n")
    assert _tool().main(["--cgad-json", str(counts), "--registry", str(reg), "--strain-id", "EXAMPLE",
                         "--out-json", str(counts)]) == 1
    assert counts.read_text() == before


def test_existing_or_colliding_outputs_are_refused(tmp_path):
    counts = tmp_path / "counts.json"; counts.write_text(json.dumps({f: 0 for f in lib.CHITIN_FAMILIES}))
    reg = tmp_path / "reg.tsv"; reg.write_text(REG + "R1\tStreptomyces x\tNR\tNR\t\t\n")
    old = tmp_path / "old.json"; old.write_text("earlier receipt\n")
    base = ["--cgad-json", str(counts), "--registry", str(reg), "--strain-id", "EXAMPLE"]
    assert _tool().main(base + ["--out-json", str(old)]) == 1
    assert old.read_text() == "earlier receipt\n"
    same = tmp_path / "same.out"
    assert _tool().main(base + ["--out-json", str(same), "--out-tsv", str(same)]) == 1
    assert not same.exists()
    assert _tool().main(base + ["--out-json", str(tmp_path / "new.json")]) == 0
