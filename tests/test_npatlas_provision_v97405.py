"""test_npatlas_provision_v97405.py -- mamey/npatlas_provision.py + its operator front door
tools/npatlas_provision.py, plus mamey/npatlas_structure.py::render_structure_svg (NPA-03/04,
punch-card B7 steps 2-3). Steps 4/5 (Tanimoto, ChemSpider) are owner-gated and not covered here.

Synthetic fixtures only: fake NPAIDs/compound names, tmp_path-only paths, no real strain
identifiers, no absolute local paths baked into assertions -- mirrors the house convention in
tests/test_chitin_reference_eval_v97405.py / tests/test_wiki_in_bundle_v97401.py.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PY = sys.executable

from mamey import npatlas_provision as prov
from mamey.npatlas_provision import (
    FilterClause,
    NpatlasProvisionError,
    clause_from_dict,
    detect_json_root_prefix,
    doctor_report,
    evaluate_clause,
    inspect_source,
    iter_records,
    load_predicate_file,
    provision,
    record_matches,
    sha256_file,
)
from mamey.npatlas_structure import STRUCTURE_CAPTION_CEILING, render_structure_svg


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _synthetic_records():
    return [
        {"npaid": "NPA-SYN-0001", "name": "synthonamide", "origin_type": "bacterium",
         "genus": "Synthomyces", "origin_taxon": "Synthomyces fictus",
         "smiles": "CCO", "mol_formula": "C2H6O"},
        {"npaid": "NPA-SYN-0002", "name": "fungisynthol", "origin_type": "fungus",
         "genus": "Fungomonas", "origin_taxon": "Fungomonas imaginaria",
         "smiles": "*CC", "mol_formula": "C2H5*"},
        {"npaid": "NPA-SYN-0003", "name": "actinosynthone", "origin_type": "bacterium",
         "genus": "Actinofictus", "origin_taxon": "Actinofictus exemplaris",
         "smiles": "not-a-real-smiles(((", "mol_formula": "unknown"},
    ]


@pytest.fixture()
def json_array_source(tmp_path) -> Path:
    """A bare top-level JSON array -- the shape of the official NP Atlas download."""
    p = tmp_path / "npatlas_source_array.json"
    p.write_text(json.dumps(_synthetic_records()), encoding="utf-8")
    return p


@pytest.fixture()
def json_compounds_source(tmp_path) -> Path:
    """A {"compounds": [...]} wrapped shape -- this bundle's own add-on filtered-file shape."""
    p = tmp_path / "npatlas_source_wrapped.json"
    p.write_text(json.dumps({"compounds": _synthetic_records()}), encoding="utf-8")
    return p


@pytest.fixture()
def sdf_source(tmp_path) -> Path:
    p = tmp_path / "npatlas_source.sdf"
    p.write_text(
        "synthonamide\n  Synth\n\n  0  0  0  0  0  0  0  0  0  0999 V2000\nM  END\n"
        ">  <npaid>\nNPA-SYN-0001\n\n"
        ">  <origin_type>\nbacterium\n\n"
        ">  <genus>\nSynthomyces\n\n"
        "$$$$\n"
        "fungisynthol\n  Synth\n\n  0  0  0  0  0  0  0  0  0  0999 V2000\nM  END\n"
        ">  <npaid>\nNPA-SYN-0002\n\n"
        ">  <origin_type>\nfungus\n\n"
        ">  <genus>\nFungomonas\n\n"
        "$$$$\n",
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# streaming source detection + iteration
# ---------------------------------------------------------------------------

def test_detect_root_prefix_bare_array(json_array_source):
    assert detect_json_root_prefix(str(json_array_source)) == "item"


def test_detect_root_prefix_wrapped_object(json_compounds_source):
    assert detect_json_root_prefix(str(json_compounds_source)) == "compounds.item"


def test_detect_root_prefix_override_wins(json_array_source):
    assert detect_json_root_prefix(str(json_array_source), override="compounds.item") == "compounds.item"


def test_iter_records_json_array(json_array_source):
    recs = list(iter_records(str(json_array_source)))
    assert len(recs) == 3
    assert {r["npaid"] for r in recs} == {"NPA-SYN-0001", "NPA-SYN-0002", "NPA-SYN-0003"}


def test_iter_records_json_wrapped(json_compounds_source):
    recs = list(iter_records(str(json_compounds_source)))
    assert len(recs) == 3


def test_iter_records_sdf(sdf_source):
    recs = list(iter_records(str(sdf_source)))
    assert len(recs) == 2
    assert recs[0]["npaid"] == "NPA-SYN-0001"
    assert recs[0]["origin_type"] == "bacterium"
    assert recs[1]["genus"] == "Fungomonas"


def test_iter_records_unsupported_extension_refuses(tmp_path):
    p = tmp_path / "npatlas_source.tsv"
    p.write_text("npaid\tname\n", encoding="utf-8")
    with pytest.raises(NpatlasProvisionError):
        list(iter_records(str(p)))


# ---------------------------------------------------------------------------
# declarative filter clauses -- never executed code
# ---------------------------------------------------------------------------

def test_clause_from_dict_rejects_bad_op():
    with pytest.raises(NpatlasProvisionError):
        clause_from_dict({"field": "genus", "op": "exec", "value": "x"})


def test_clause_from_dict_requires_field():
    with pytest.raises(NpatlasProvisionError):
        clause_from_dict({"op": "eq", "value": "x"})


def test_evaluate_clause_in_and_icontains():
    rec = _synthetic_records()[0]
    assert evaluate_clause(rec, FilterClause("origin_type", "in", ["bacterium", "fungus"]))
    assert not evaluate_clause(rec, FilterClause("origin_type", "in", ["fungus"]))
    assert evaluate_clause(rec, FilterClause("origin_taxon", "icontains", "SYNTHOMYCES"))
    assert not evaluate_clause(rec, FilterClause("origin_taxon", "icontains", "nonexistent-taxon"))


def test_record_matches_ands_all_clauses():
    rec = _synthetic_records()[0]
    clauses = [FilterClause("origin_type", "eq", "bacterium"), FilterClause("genus", "in", ["Synthomyces"])]
    assert record_matches(rec, clauses)
    clauses_fail = clauses + [FilterClause("genus", "in", ["Fungomonas"])]
    assert not record_matches(rec, clauses_fail)


def test_record_matches_empty_clause_list_matches_everything():
    assert record_matches(_synthetic_records()[1], [])


def test_load_predicate_file_declarative_not_code(tmp_path):
    p = tmp_path / "predicate.json"
    p.write_text(json.dumps([{"field": "origin_type", "op": "eq", "value": "bacterium"}]), encoding="utf-8")
    clauses = load_predicate_file(str(p))
    assert len(clauses) == 1
    assert clauses[0].field == "origin_type"


def test_load_predicate_file_rejects_non_list(tmp_path):
    p = tmp_path / "predicate.json"
    p.write_text(json.dumps({"field": "origin_type", "op": "eq", "value": "bacterium"}), encoding="utf-8")
    with pytest.raises(NpatlasProvisionError):
        load_predicate_file(str(p))


def test_load_predicate_file_missing_refuses(tmp_path):
    with pytest.raises(NpatlasProvisionError):
        load_predicate_file(str(tmp_path / "nope.json"))


# ---------------------------------------------------------------------------
# sha256 + provision receipt content-addressing
# ---------------------------------------------------------------------------

def test_sha256_file_matches_hashlib(json_array_source):
    expected = hashlib.sha256(json_array_source.read_bytes()).hexdigest()
    assert sha256_file(str(json_array_source)) == expected


def test_provision_writes_filtered_subset_and_receipt(tmp_path, json_array_source):
    out = tmp_path / "filtered.json"
    clauses = [FilterClause("origin_type", "eq", "bacterium")]
    receipt = provision(str(json_array_source), str(out), clauses, dataset_version="vSYN_TEST")
    d = receipt.to_dict()

    assert out.exists()
    written = json.loads(out.read_text(encoding="utf-8"))
    assert len(written["compounds"]) == 2  # 2 bacterium records in the synthetic fixture
    assert d["included_count"] == 2
    assert d["excluded_count"] == 1
    assert d["source_sha256"] == hashlib.sha256(json_array_source.read_bytes()).hexdigest()
    assert d["output_sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert d["dataset_version"] == "vSYN_TEST"
    assert d["filter_rule"] == [{"field": "origin_type", "op": "eq", "value": "bacterium"}]
    assert d["licence_id"] == "CC-BY-NC-4.0"
    assert "CC BY-NC 4.0" in d["licence_text"]
    assert "not" in d["claim_ceiling"].lower()  # never a bare deliverable with no ceiling


def test_provision_no_filter_keeps_everything(tmp_path, json_array_source):
    out = tmp_path / "filtered_all.json"
    receipt = provision(str(json_array_source), str(out), [])
    d = receipt.to_dict()
    assert d["included_count"] == 3
    assert d["excluded_count"] == 0


def test_provision_missing_source_refuses(tmp_path):
    with pytest.raises(NpatlasProvisionError):
        provision(str(tmp_path / "nope.json"), str(tmp_path / "out.json"), [])


def test_provision_never_touches_source_file(tmp_path, json_array_source):
    before = json_array_source.read_bytes()
    out = tmp_path / "filtered.json"
    provision(str(json_array_source), str(out), [FilterClause("origin_type", "eq", "fungus")])
    assert json_array_source.read_bytes() == before


# ---------------------------------------------------------------------------
# inspect (read-only, never writes)
# ---------------------------------------------------------------------------

def test_inspect_source_reports_count_and_hash(tmp_path, json_array_source):
    report = inspect_source(str(json_array_source), sample_limit=2)
    assert report["total_records"] == 3
    assert len(report["sample_records"]) == 2
    assert report["source_sha256"] == hashlib.sha256(json_array_source.read_bytes()).hexdigest()
    assert report["json_root_prefix"] == "item"
    # inspect is read-only -- no new file appears alongside the source
    assert set(p.name for p in tmp_path.iterdir()) == {json_array_source.name}


def test_inspect_source_missing_refuses(tmp_path):
    with pytest.raises(NpatlasProvisionError):
        inspect_source(str(tmp_path / "nope.json"))


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

def test_doctor_report_shape():
    report = doctor_report()
    assert "ijson" in report and "available" in report["ijson"]
    assert "rdkit" in report and "available" in report["rdkit"]
    assert "npatlas_dataset" in report
    assert report["tool_version"] == prov.TOOL_VERSION


# ---------------------------------------------------------------------------
# NPA-03 -- structure rendering typed states (mamey/npatlas_structure.py)
# ---------------------------------------------------------------------------

def test_render_structure_svg_hold_on_empty_smiles():
    r = render_structure_svg("")
    assert r["state"] == "HOLD"
    assert r["svg"] is None
    assert r["caption"] == STRUCTURE_CAPTION_CEILING


def test_render_structure_svg_hold_on_wildcard():
    r = render_structure_svg("*CC")
    assert r["state"] == "HOLD"
    assert r["svg"] is None
    assert "wildcard" in r["reason"].lower()
    assert r["caption"] == STRUCTURE_CAPTION_CEILING


def test_render_structure_svg_caption_always_present_even_when_unavailable_or_invalid():
    # Whatever rdkit's availability is in this environment, the ceiling caption must always
    # be present -- rendered, held, or unavailable, a caller must never get an uncaptioned result.
    for smiles in ("", "*", "CCO", "not-a-real-smiles((("):
        r = render_structure_svg(smiles)
        assert r["state"] in ("RENDERED", "HOLD", "UNAVAILABLE")
        assert r["caption"] == STRUCTURE_CAPTION_CEILING
        if r["state"] != "RENDERED":
            assert r["svg"] is None


def test_render_structure_svg_unavailable_or_valid_render_for_real_smiles():
    r = render_structure_svg("CCO")  # ethanol -- a real, unambiguous, non-wildcard structure
    if r["state"] == "UNAVAILABLE":
        assert "rdkit" in r["reason"].lower()
    else:
        assert r["state"] == "RENDERED"
        assert isinstance(r["svg"], str) and "<svg" in r["svg"].lower()


def test_render_structure_svg_deterministic_when_rdkit_present():
    r1 = render_structure_svg("CCO")
    r2 = render_structure_svg("CCO")
    assert r1["state"] == r2["state"]
    if r1["state"] == "RENDERED":
        assert r1["svg"] == r2["svg"]


# ---------------------------------------------------------------------------
# operator front door: tools/npatlas_provision.py
# ---------------------------------------------------------------------------

def _run_tool(args, cwd=None):
    return subprocess.run([PY, str(TOOLS / "npatlas_provision.py"), *args],
                           capture_output=True, text=True, cwd=cwd)


def test_cli_doctor_stdout_only_json():
    proc = _run_tool(["doctor"])
    assert proc.returncode == 0
    assert proc.stderr == ""
    payload = json.loads(proc.stdout)
    assert "ijson" in payload


def test_cli_inspect_reads_synthetic_source(json_array_source):
    proc = _run_tool(["inspect", "--source", str(json_array_source)])
    assert proc.returncode == 0
    assert proc.stderr == ""
    payload = json.loads(proc.stdout)
    assert payload["total_records"] == 3


def test_cli_provision_writes_receipt_and_output(tmp_path, json_array_source):
    out = tmp_path / "cli_filtered.json"
    proc = _run_tool(["provision", "--source", str(json_array_source), "--out", str(out),
                       "--origin-type", "bacterium", "--dataset-version", "vCLI_TEST"])
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    payload = json.loads(proc.stdout)
    assert payload["included_count"] == 2
    assert payload["dataset_version"] == "vCLI_TEST"
    assert out.exists()


def test_cli_provision_tsv_format(tmp_path, json_array_source):
    out = tmp_path / "cli_filtered_tsv.json"
    proc = _run_tool(["provision", "--source", str(json_array_source), "--out", str(out),
                       "--format", "tsv"])
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.strip("\n").split("\n")
    assert len(lines) == 2
    header = lines[0].split("\t")
    assert "source_sha256" in header
    assert "licence_id" in header


def test_cli_provision_missing_source_refuses_to_stderr(tmp_path):
    proc = _run_tool(["provision", "--source", str(tmp_path / "nope.json"), "--out", str(tmp_path / "o.json")])
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "NPATLAS_PROVISION_REFUSAL" in proc.stderr


def test_cli_provision_predicate_file(tmp_path, json_array_source):
    predicate = tmp_path / "predicate.json"
    predicate.write_text(json.dumps([{"field": "genus", "op": "in", "value": ["Fungomonas"]}]), encoding="utf-8")
    out = tmp_path / "cli_predicate_filtered.json"
    proc = _run_tool(["provision", "--source", str(json_array_source), "--out", str(out),
                       "--predicate-file", str(predicate)])
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["included_count"] == 1


def test_cli_provision_taxon_contains(tmp_path, json_array_source):
    out = tmp_path / "cli_taxon_filtered.json"
    proc = _run_tool(["provision", "--source", str(json_array_source), "--out", str(out),
                       "--taxon-contains", "actinofictus"])
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["included_count"] == 1


def test_cli_stdout_never_mixes_with_refusal(tmp_path):
    proc = _run_tool(["inspect", "--source", str(tmp_path / "nope.json")])
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "NPATLAS_PROVISION_REFUSAL" in proc.stderr


# ---------------------------------------------------------------------------
# zero print() ratchet (AST-based, house convention -- see test_chitin_reference_eval_v97405.py)
# ---------------------------------------------------------------------------

def _find_print_calls(tree) -> list[int]:
    import ast
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            lines.append(node.lineno)
    return lines


@pytest.mark.parametrize("relpath", [
    "mamey/npatlas_provision.py",
    "tools/npatlas_provision.py",
])
def test_no_print_calls(relpath):
    import ast
    src = (ROOT / relpath).read_text(encoding="utf-8")
    tree = ast.parse(src, filename=relpath)
    assert _find_print_calls(tree) == [], f"print() call(s) found in {relpath}"
