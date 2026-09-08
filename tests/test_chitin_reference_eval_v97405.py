"""test_chitin_reference_eval_v97405.py -- mamey/chitin_reference_eval.py + its operator front
door tools/chitin_reference_eval.py.

Synthetic fixtures only: no real strain identifiers (no AS-###/SID###/AJS-### style ids) and no
absolute local paths -- every path is built from pytest's tmp_path. This mirrors the house
wiki/public-tier scan convention (tests/test_wiki_in_bundle_v97401.py) even though this file is
not itself bundle payload, so a future scan reuse never has to special-case it.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module  # dataclass processing requires the module registered
    spec.loader.exec_module(module)
    return module


mod = _load("chitin_reference_eval_lib", ROOT / "mamey" / "chitin_reference_eval.py")


# ---------------------------------------------------------------------------
# architecture_profile
# ---------------------------------------------------------------------------

def test_multi_arm_capacity_requires_all_three():
    p = mod.architecture_profile("SYN-001", {"GH18": 2, "GH19": 0, "AA10_LPMO": 1, "CBM_CHITIN": 1, "GlcNAc": 0})
    assert p.architecture_state == "MULTI_ARM_CHITIN_CAPACITY"
    assert p.domains_total == 4
    assert p.claim_ceiling == mod.CLAIM_CEILING


def test_partial_coordinated_needs_endo_plus_one_support():
    p = mod.architecture_profile("SYN-002", {"GH18": 1, "AA10_LPMO": 1})
    assert p.architecture_state == "PARTIAL_COORDINATED_CHITIN_CAPACITY"


def test_chitinase_only_without_supporting_arms():
    p = mod.architecture_profile("SYN-003", {"GH19": 3})
    assert p.architecture_state == "CHITINASE_FAMILY_CAPACITY_WITHOUT_SUPPORTING_ARMS"
    assert p.domains_total == 3


def test_non_endochitinase_context_when_support_present_but_no_endo():
    # CBM + LPMO present, no GH18/GH19 -> total 2+... wait total must exceed the minimal ceiling
    p = mod.architecture_profile("SYN-004", {"CBM_CHITIN": 2, "AA10_LPMO": 2})
    assert p.architecture_state == "NON_ENDOCHITINASE_CHITIN_CONTEXT"
    assert p.domains_total == 4


def test_minimal_measured_capacity_at_or_below_ceiling():
    p = mod.architecture_profile("SYN-005", {"CBM_CHITIN": 1})
    assert p.architecture_state == "MINIMAL_MEASURED_CHITIN_DOMAIN_CAPACITY"
    assert p.domains_total == 1


def test_absent_when_core_and_context_both_zero():
    p = mod.architecture_profile("SYN-006", {})
    assert p.architecture_state == "ABSENT_NO_MEASURED_CHITIN_DOMAINS"
    assert p.domains_total == 0


def test_glcnac_alone_is_context_not_core_but_not_absent():
    # GlcNAc-only: total (core) is 0, but context != 0, so this is NOT the "absent" state --
    # it falls through the total<=2 minimal branch (0 <= 2).
    p = mod.architecture_profile("SYN-007", {"GlcNAc": 5})
    assert p.architecture_state == "MINIMAL_MEASURED_CHITIN_DOMAIN_CAPACITY"
    assert p.domains_total == 0
    assert p.counts["GlcNAc"] == 5


def test_missing_family_keys_default_to_zero():
    p = mod.architecture_profile("SYN-008", {"GH18": 4})
    assert p.counts == {"GH18": 4, "GH19": 0, "AA10_LPMO": 0, "CBM_CHITIN": 0, "GlcNAc": 0}


def test_non_numeric_count_refuses():
    with pytest.raises(mod.ChitinReferenceEvalError):
        mod.architecture_profile("SYN-009", {"GH18": "many"})


def test_negative_count_refuses():
    with pytest.raises(mod.ChitinReferenceEvalError):
        mod.architecture_profile("SYN-010", {"GH18": -1})


# ---------------------------------------------------------------------------
# build_reference_rows / reference_quality
# ---------------------------------------------------------------------------

_REGISTRY = [
    {"reference_id": "ref_alpha", "taxon": "Genusalpha", "source_path": "genomes/alpha.fna",
     "source_sha256": "aaaa", "ani_pct": "96.2", "aligned_fragment_fraction": "0.55",
     "chitin_domains_total": "12"},
    {"reference_id": "ref_beta", "taxon": "Genusalpha", "source_path": "genomes/beta.fna",
     "source_sha256": "bbbb", "ani_pct": "", "aligned_fragment_fraction": "",
     "chitin_domains_total": "7"},
    {"reference_id": "ref_gamma", "taxon": "Genusalpha", "source_path": "genomes/gamma.fna",
     "source_sha256": "cccc", "ani_pct": "91.0", "aligned_fragment_fraction": "0.6",
     "chitin_domains_total": "9"},
    {"reference_id": "ref_delta", "taxon": "Genusalpha", "source_path": "genomes/delta.fna",
     "source_sha256": "dddd", "ani_pct": "70.0", "aligned_fragment_fraction": "0.55",
     "chitin_domains_total": "3"},
    {"reference_id": "ref_far", "taxon": "Genusbeta", "source_path": "genomes/far.fna",
     "source_sha256": "eeee", "ani_pct": "99.0", "aligned_fragment_fraction": "0.9",
     "chitin_domains_total": "20"},
]


def test_build_reference_rows_filters_by_taxon():
    rows = mod.build_reference_rows(_REGISTRY, "Genusalpha")
    assert {r.reference_id for r in rows} == {"ref_alpha", "ref_beta", "ref_gamma", "ref_delta"}


def test_build_reference_rows_respects_genus_alias():
    rows = mod.build_reference_rows(_REGISTRY, "Genusgamma", genus_aliases=["Genusbeta"])
    assert {r.reference_id for r in rows} == {"ref_far"}


def test_missing_ani_types_not_scored_never_zero_similarity():
    rows = mod.build_reference_rows(_REGISTRY, "Genusalpha")
    beta = next(r for r in rows if r.reference_id == "ref_beta")
    assert beta.row_state == "NOT_SCORED"
    assert beta.ani_pct is None


def test_reference_quality_species_level():
    rows = mod.build_reference_rows(_REGISTRY, "Genusalpha")
    assert mod.reference_quality(rows) == "SPECIES_LEVEL_SIMILARITY_CANDIDATE_NOT_TAXONOMIC_CONFIRMATION"


def test_reference_quality_higher_similarity_nonspecies():
    registry = [{"reference_id": "ref_h", "taxon": "Genusalpha", "source_path": "h.fna",
                 "source_sha256": "hhhh", "ani_pct": "92.0", "aligned_fragment_fraction": "0.55",
                 "chitin_domains_total": "5"}]
    rows = mod.build_reference_rows(registry, "Genusalpha")
    assert mod.reference_quality(rows) == "HIGHER_SIMILARITY_NONSPECIES_REFERENCE_CONTEXT"


def test_reference_quality_distant_when_below_thresholds():
    registry = [{"reference_id": "ref_d", "taxon": "Genusalpha", "source_path": "d.fna",
                 "source_sha256": "dddd", "ani_pct": "60.0", "aligned_fragment_fraction": "0.55",
                 "chitin_domains_total": "5"}]
    rows = mod.build_reference_rows(registry, "Genusalpha")
    assert mod.reference_quality(rows) == "DISTANT_AVAILABLE_TAXON_MATCHED_REFERENCE_CONTEXT"


def test_reference_quality_no_panel():
    assert mod.reference_quality([]) == "NO_TAXON_MATCHED_REFERENCE_PANEL"


def test_reference_quality_panel_but_no_ani():
    registry = [{"reference_id": "ref_n", "taxon": "Genusalpha", "source_path": "n.fna",
                 "source_sha256": "nnnn"}]
    rows = mod.build_reference_rows(registry, "Genusalpha")
    assert mod.reference_quality(rows) == "TAXON_MATCHED_PANEL_BUT_NO_ANI_AT_MIN_FRACTION"


def test_low_aligned_fraction_species_ani_still_distant_not_species():
    # ANI clears the species threshold but aligned_fragment_fraction is below the 0.5 quality gate.
    registry = [{"reference_id": "ref_lowaf", "taxon": "Genusalpha", "source_path": "l.fna",
                 "source_sha256": "llll", "ani_pct": "97.0", "aligned_fragment_fraction": "0.1",
                 "chitin_domains_total": "5"}]
    rows = mod.build_reference_rows(registry, "Genusalpha")
    assert mod.reference_quality(rows) == "DISTANT_AVAILABLE_TAXON_MATCHED_REFERENCE_CONTEXT"


# ---------------------------------------------------------------------------
# evaluate_strain end-to-end
# ---------------------------------------------------------------------------

def test_evaluate_strain_picks_top_by_ani():
    ev = mod.evaluate_strain("SYN-020", {"GH18": 2, "AA10_LPMO": 1, "CBM_CHITIN": 1}, _REGISTRY, "Genusalpha")
    assert ev.top_reference.reference_id == "ref_alpha"
    assert len(ev.reference_panel) == 4
    assert ev.claim_ceiling == mod.CLAIM_CEILING
    assert "not routed through triage or scoring" in ev.scope_note


def test_evaluate_strain_to_dict_roundtrips_through_json():
    ev = mod.evaluate_strain("SYN-021", {"GH18": 1}, _REGISTRY, "Genusalpha")
    d = ev.to_dict()
    dumped = json.loads(json.dumps(d))
    assert dumped["strain_id"] == "SYN-021"
    assert dumped["profile"]["architecture_state"] == "CHITINASE_FAMILY_CAPACITY_WITHOUT_SUPPORTING_ARMS"
    assert dumped["reference_quality"] == "SPECIES_LEVEL_SIMILARITY_CANDIDATE_NOT_TAXONOMIC_CONFIRMATION"


def test_evaluate_strain_no_panel_when_taxon_unmatched():
    ev = mod.evaluate_strain("SYN-022", {"GH18": 1}, _REGISTRY, "Genusnowhere")
    assert ev.reference_panel == ()
    assert ev.reference_quality == "NO_TAXON_MATCHED_REFERENCE_PANEL"
    assert ev.top_reference is None


# ---------------------------------------------------------------------------
# verify_reference_hash
# ---------------------------------------------------------------------------

def test_verify_reference_hash_matches(tmp_path):
    f = tmp_path / "genome.fna"
    f.write_text(">contig1\nACGTACGT\n", encoding="utf-8")
    import hashlib
    digest = hashlib.sha256(f.read_bytes()).hexdigest()
    assert mod.verify_reference_hash(str(f), digest) is True


def test_verify_reference_hash_mismatch(tmp_path):
    f = tmp_path / "genome.fna"
    f.write_text(">contig1\nACGTACGT\n", encoding="utf-8")
    assert mod.verify_reference_hash(str(f), "0" * 64) is False


def test_verify_reference_hash_missing_path_returns_none(tmp_path):
    missing = tmp_path / "nope.fna"
    assert mod.verify_reference_hash(str(missing), "0" * 64) is None


def test_verify_reference_hash_no_declared_hash_returns_none(tmp_path):
    f = tmp_path / "genome.fna"
    f.write_text(">contig1\nACGT\n", encoding="utf-8")
    assert mod.verify_reference_hash(str(f), "") is None
    assert mod.verify_reference_hash(str(f), "NR") is None


# ---------------------------------------------------------------------------
# operator front door (tools/chitin_reference_eval.py) -- subprocess, real CLI surface
# ---------------------------------------------------------------------------

def _write_package(tmp_path, counts, strain_id="SYN-100", taxon="Genusalpha"):
    pkg = tmp_path / "package"
    pkg.mkdir()
    manifest = {
        "strain_id": strain_id, "taxonomy": taxon,
        "source_scans": {"chitinase": {"status": "SOURCE_DERIVED", "counts": counts}},
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pkg


def _write_registry(tmp_path):
    reg = tmp_path / "registry.tsv"
    header = "reference_id\ttaxon\tsource_path\tsource_sha256\tani_pct\taligned_fragment_fraction\tchitin_domains_total\n"
    row = "ref_alpha\tGenusalpha\tgenomes/alpha.fna\taaaa\t96.2\t0.55\t12\n"
    reg.write_text(header + row, encoding="utf-8")
    return reg


def _run_cli(args):
    return subprocess.run([sys.executable, str(TOOLS / "chitin_reference_eval.py"), *args],
                           capture_output=True, text=True)


def test_cli_package_mode_json_stdout(tmp_path):
    pkg = _write_package(tmp_path, {"GH18": 2, "AA10_LPMO": 1, "CBM_CHITIN": 1})
    reg = _write_registry(tmp_path)
    proc = _run_cli(["--package", str(pkg), "--registry", str(reg)])
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["strain_id"] == "SYN-100"
    assert payload["profile"]["architecture_state"] == "MULTI_ARM_CHITIN_CAPACITY"
    assert proc.stderr == ""


def test_cli_tsv_format(tmp_path):
    pkg = _write_package(tmp_path, {"GH18": 1})
    reg = _write_registry(tmp_path)
    proc = _run_cli(["--package", str(pkg), "--registry", str(reg), "--format", "tsv"])
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.strip("\n").split("\n")
    assert lines[0].startswith("strain_id\t")
    assert lines[1].startswith("SYN-100\t")


def test_cli_cgad_json_mode_requires_strain_id(tmp_path):
    cgad = tmp_path / "cgad.json"
    cgad.write_text(json.dumps({"counts": {"GH18": 2}}), encoding="utf-8")
    reg = _write_registry(tmp_path)
    proc = _run_cli(["--cgad-json", str(cgad), "--registry", str(reg)])
    assert proc.returncode != 0
    assert "MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL" in proc.stderr
    assert proc.stdout == ""


def test_cli_cgad_json_mode_with_explicit_ids(tmp_path):
    cgad = tmp_path / "cgad.json"
    cgad.write_text(json.dumps({"counts": {"GH18": 2, "AA10_LPMO": 1, "CBM_CHITIN": 1}}), encoding="utf-8")
    reg = _write_registry(tmp_path)
    proc = _run_cli(["--cgad-json", str(cgad), "--registry", str(reg),
                      "--strain-id", "SYN-200", "--taxon", "Genusalpha"])
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["strain_id"] == "SYN-200"


def test_cli_refuses_missing_registry_via_stderr(tmp_path):
    pkg = _write_package(tmp_path, {"GH18": 1})
    proc = _run_cli(["--package", str(pkg), "--registry", str(tmp_path / "nope.tsv")])
    assert proc.returncode == 1
    assert "MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL" in proc.stderr
    assert proc.stdout == ""


def test_cli_refuses_manifest_without_cgad_scan(tmp_path):
    pkg = tmp_path / "package_nocgad"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "SYN-300", "taxonomy": "Genusalpha"}),
                                        encoding="utf-8")
    reg = _write_registry(tmp_path)
    proc = _run_cli(["--package", str(pkg), "--registry", str(reg)])
    assert proc.returncode == 1
    assert "MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL" in proc.stderr


def test_cli_out_json_and_out_tsv_write_files(tmp_path):
    pkg = _write_package(tmp_path, {"GH18": 1, "AA10_LPMO": 1, "CBM_CHITIN": 1})
    reg = _write_registry(tmp_path)
    out_json = tmp_path / "out.json"
    out_tsv = tmp_path / "out.tsv"
    proc = _run_cli(["--package", str(pkg), "--registry", str(reg),
                      "--out-json", str(out_json), "--out-tsv", str(out_tsv)])
    assert proc.returncode == 0, proc.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["strain_id"] == "SYN-100"
    assert out_tsv.read_text(encoding="utf-8").startswith("strain_id\t")


def test_cli_never_mixes_refusal_into_stdout(tmp_path):
    """Deliverable stdout and refusal stderr must never share a stream."""
    pkg = _write_package(tmp_path, {"GH18": 1})
    proc = _run_cli(["--package", str(pkg), "--registry", str(tmp_path / "nope.tsv")])
    assert proc.stdout == ""
    assert "MAMEY_CHITIN_REFERENCE_EVAL_REFUSAL" in proc.stderr


def _find_print_calls(path: Path) -> list[int]:
    """AST-based print() call finder -- unlike a regex, this cannot be fooled by a docstring
    that merely mentions the word 'print(' (as this file's own module docstrings do)."""
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            lines.append(node.lineno)
    return lines


def test_library_has_zero_print_calls():
    """Ratchet guard: mamey/chitin_reference_eval.py is a library and must stay print-free."""
    hits = _find_print_calls(ROOT / "mamey" / "chitin_reference_eval.py")
    assert hits == [], f"unexpected print() call(s) at line(s) {hits}"


def test_tool_has_zero_print_calls():
    """Ratchet guard: the operator tool uses sys.stdout.write/sys.stderr.write, not print()."""
    hits = _find_print_calls(ROOT / "tools" / "chitin_reference_eval.py")
    assert hits == [], f"unexpected print() call(s) at line(s) {hits}"
