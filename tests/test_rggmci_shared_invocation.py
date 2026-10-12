"""Independent metadata/config/export contracts; no live searches or private inputs."""
import copy
import csv
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
from mamey import parsers, ref_completion as rc, rggmci as rg

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "tests/fixtures/rggmci_public_VWPH00000000.1_subset.zip"


def archive(path, *, fasta=True):
    """N-only source: coordinates and identities, no functional proteins."""
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_STORED) as z:
        for i in (1, 2):
            cid = f"SYNTH_FULL_{i}.1"
            text = "\n".join([f"LOCUS       {cid:<16}     120 bp    DNA     linear   BCT 01-JAN-2000",
                "DEFINITION  Synthetic metadata control.", f"ACCESSION   {cid.split('.')[0]}", f"VERSION     {cid}",
                "COMMENT     Orig. start :: 0", "            Orig. end :: 120",
                "FEATURES             Location/Qualifiers", "     region          1..120",
                '                     /product="other"', '                     /contig_edge="True"',
                "ORIGIN", "        1 " + "n" * 60, "       61 " + "n" * 60, "//", ""])
            z.writestr(f"{cid}.region001.gbk", text)
        if fasta:
            z.writestr("input.fna", ">SYNTH_FULL_1.1\n" + "N" * 120 + "\n>SYNTH_FULL_2.1\n" + "N" * 120 + "\n")
    return path


def table(payload):
    reader = csv.DictReader(io.StringIO(payload.decode()), delimiter="\t")
    return reader.fieldnames, list(reader)


def analytical(result):
    value = copy.deepcopy(result)
    value.pop("wrapper_context", None)
    # Compare the complete JSON-domain contract: ordered tuple evidence is an array.
    return json.loads(json.dumps(value))


@pytest.mark.parametrize("context", [None, {}, "AUTO"])
def test_none_empty_auto_semantics_and_exact_roster(tmp_path, context):
    path = archive(tmp_path / "input.zip")
    got = rg.prepare_archive_inputs(path, **({} if context == "AUTO" else {"contigs": context}))
    assert got["sequence_context"]["available"] is (context is not None)
    if context == "AUTO":
        assert got["contigs"] == {"SYNTH_FULL_1.1": "N" * 120, "SYNTH_FULL_2.1": "N" * 120}
        assert [x["length"] for x in got["sequence_context"]["records"]] == [120, 120]
    else:
        assert got["contigs"] == context
        assert got["sequence_context"]["records"] == []
    assert inspect.signature(rg.compute_rggmci).parameters["contigs"].default is None
    assert inspect.signature(rg.run_rggmci).parameters["contigs"].default is None


def test_region_only_sequence_fallback_is_explicit_and_not_whole_genome(tmp_path):
    got = rg.prepare_archive_inputs(archive(tmp_path / "region_only.zip", fasta=False))
    assert [len(x) for x in got["contigs"].values()] == [120, 120]
    assert got["sequence_context_origin"] == "archive_fasta_else_longest_gbk_per_contig"
    assert [b.contig_length for b in got["bgcs"]] == [0, 0]


def test_snapshot_is_before_enrichment_and_matches_fresh_common_intake(tmp_path):
    path = archive(tmp_path / "input.zip")
    snapshot = {}
    enriched = parsers.parse_bgcs_from_zip(path, evidence={}, core_snapshot_out=snapshot)
    enriched[0].products.append("later_wrapper_annotation")
    enriched[0].contig = "later_wrapper_identity"
    before = copy.deepcopy(snapshot)
    prepared = rg.prepare_archive_inputs(path, core_snapshot=snapshot)
    assert prepared["records"] == rg.prepare_archive_inputs(path)["records"]
    prepared["bgcs"][0].products.append("scorer_mutation")
    assert snapshot == before and snapshot["records"][0]["products"] == ["other"]


@pytest.mark.parametrize("damage", ["checksum", "extra_field", "duplicate_alias", "region_conflict"])
def test_unbound_or_ambiguous_snapshot_refuses(tmp_path, damage):
    path = archive(tmp_path / "input.zip")
    snapshot = {}
    parsers.parse_bgcs_from_zip(path, evidence={}, core_snapshot_out=snapshot)
    if damage == "checksum": snapshot["input_sha256"] = "0" * 64
    elif damage == "extra_field": snapshot["records"][0]["invented"] = True
    elif damage == "duplicate_alias": snapshot["records"][1]["bgc_id"] = snapshot["records"][0]["bgc_id"]
    else: snapshot["records"][0]["region_number"] = 2
    with pytest.raises(ValueError, match="RGGMCI_CORE"):
        rg.prepare_archive_inputs(path, core_snapshot=snapshot)


def test_common_preflight_refuses_relevant_member_before_partial_admission(tmp_path, monkeypatch):
    path = tmp_path / "refused.zip"
    with zipfile.ZipFile(path, "x") as z:
        z.writestr("small.region001.gbk", b"small")
        z.writestr("large.region002.gbk", b"N" * 600)
    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "512")
    monkeypatch.setattr(rg, "run_rggmci", lambda *a, **k: pytest.fail("scorer must not run on partial admission"))
    with pytest.raises(parsers.GbkSizeGuardRefusal) as exc:
        rg.run_archive(path, reference_completion="off")
    assert exc.value.member == "large.region002.gbk"


def test_common_default_sequence_context_reaches_real_complexity_gate(tmp_path, monkeypatch):
    path = archive(tmp_path / "input.zip")
    # Noncoding homopolymer control, never a functional sequence or protein design.
    monkeypatch.setattr(rg, "extract_contig_sequences", lambda path: {"SYNTH_FULL_1.1": "A" * 120})
    seen = []
    def observed(path, bgcs, contigs=None, **kwargs):
        control = copy.deepcopy(bgcs[0])
        control.edge_status, control.start, control.end, control.contig_length = "Edge", 1, 60, 120
        seen.append(rg._terminus_sequence_state(control, contigs))
        return {"ranked_pairs": [], "related_locus_pairs": [], "reference_completion": {"completion_tier": "OFF"}}
    monkeypatch.setattr(rg, "run_rggmci", observed)
    rg.run_archive(path, reference_completion="off")
    rg.run_archive(path, contigs=None, reference_completion="off")
    assert seen == ["HOMOPOLYMER_TERMINUS", "TERMINUS_SEQUENCE_UNAVAILABLE"]


@pytest.mark.parametrize("resolver,env_name,filename", [
    (rc.resolve_mibig_db, "RGGMCI_MIBIG_DB", rc.DB_FAA),
    (rc.resolve_pfam_hmm, "RGGMCI_PFAM_HMM", None),
])
def test_existing_resource_precedence_and_missing_source_stop(tmp_path, monkeypatch, resolver, env_name, filename):
    explicit, env = tmp_path / "explicit", tmp_path / "env"
    if filename:
        for path in (explicit, env): path.mkdir(); (path / filename).write_text("metadata fixture")
    else:
        for path in (explicit, env): path.write_text("metadata fixture")
    monkeypatch.setenv(env_name, str(env))
    assert resolver(explicit) == (str(explicit), "explicit")
    assert resolver(None) == (str(env), "env")
    assert resolver(tmp_path / "absent")[0] is None
    assert resolver(tmp_path / "absent")[1].startswith("explicit_path")


def test_resource_fingerprint_detects_changed_actual_content(tmp_path):
    resource = tmp_path / "metadata_asset"
    resource.write_bytes(b"old")
    bound = rc.resource_descriptor(resource, found_by="explicit")
    assert bound["files"][resource.name]["sha256"] == hashlib.sha256(b"old").hexdigest()
    resource.write_bytes(b"new")
    with pytest.raises(ValueError, match="RESOURCE_CHANGED"):
        rc.verify_resource_descriptor(bound)


def test_completion_off_does_not_probe_optional_aligner(tmp_path, monkeypatch):
    path = archive(tmp_path / "input.zip")
    monkeypatch.setattr(rc, "find_aligner", lambda *a, **k: pytest.fail("OFF must not probe aligner"))
    result = rg.run_archive(path, reference_completion="off")
    assert result["reference_completion"]["completion_tier"] == "OFF"
    assert result["invocation"]["resources"]["completion_aligner"]["found_by"] == "not_used"


def test_shared_threads_forwarded_at_actual_residue_boundary_only_when_requested(tmp_path, monkeypatch):
    from mamey import residue_tiling
    path = archive(tmp_path / "input.zip")
    bgcs = rg.prepare_archive_inputs(path)["bgcs"]
    calls = []
    def observed(*args, **kwargs): calls.append(kwargs)
    monkeypatch.setattr(residue_tiling, "add_residue_tiling", observed)
    rg.run_rggmci(path, bgcs, reference_completion="off", diamond_db="unopened-control", threads=1)
    rg.run_archive(path, reference_completion="off", diamond_db="unopened-control", threads=1)
    assert "threads" not in calls[0] and "resource_receipt" not in calls[0]
    assert calls[1]["threads"] == 1 and isinstance(calls[1]["resource_receipt"], dict)


def test_all_row_fields_nested_cells_and_empty_tables_are_lossless():
    payload = rc.tsv_payload([{"first": "plain"}, {"first": "second", "later": {"values": [1, None, "x"]}}], ["unused"])
    headers, rows = table(payload)
    assert headers == ["first", "later"]
    assert json.loads(rows[1]["later"]) == {"values": [1, None, "x"]}
    empty = rg.canonical_artifacts({"ranked_pairs": [], "related_locus_pairs": [], "candidate_groups": [],
                                    "reference_completion": {"completion_tier": "OFF"}}, name="empty")
    assert len(empty) == 8
    for name in ("pairs", "related_loci"):
        columns, rows = table(empty[f"empty_{name}.tsv"])
        assert {"identity_a", "region_a", "contig_a", "identity_b", "region_b", "contig_b"} <= set(columns)
        assert rows == []
    assert table(empty["empty_candidate_groups.tsv"])[1] == []
    assert table(empty["empty_reference_completion.tsv"])[1][0]["completion_tier"] == "OFF"


def test_same_region_number_on_distinct_contigs_keeps_full_identity(tmp_path, monkeypatch):
    path = archive(tmp_path / "input.zip")
    def scored(*args, **kwargs):
        return {"ranked_pairs": [{"bgc_a": "BGC001", "contig_a": "SYNTH_FULL_1.1", "bgc_b": "BGC002",
            "contig_b": "SYNTH_FULL_2.1", "rggmci_confidence": "LOW_SHARED_REFERENCE_SIGNAL"}], "related_locus_pairs": []}
    monkeypatch.setattr(rg, "run_rggmci", scored)
    result = rg.run_archive(path, reference_completion="off", label="SYNTH_LABEL")
    pair = result["ranked_pairs"][0]
    assert pair["identity_a"] == "SYNTH_LABEL / SYNTH_FULL_1.1 / region001 / BGC001"
    assert pair["identity_b"] == "SYNTH_LABEL / SYNTH_FULL_2.1 / region001 / BGC002"


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    output = tmp_path_factory.mktemp("shared_invocation_build") / "pkg"
    process = subprocess.run([sys.executable, str(ROOT / "packaging/rggmci/build_rggmci_package.py"),
                              "--bundle", str(ROOT), "--out", str(output)], capture_output=True, text=True)
    assert process.returncode == 0, process.stdout + process.stderr
    return output


@pytest.mark.parametrize("without_bio", [False, True], ids=["available_backend", "builtin_backend"])
@pytest.mark.parametrize("profile", ["default_missing", "off", "none"])
def test_actual_generated_highlevel_full_analytical_result_matches_embedded_snapshot(generated, tmp_path, monkeypatch, profile, without_bio):
    for key in ("RGGMCI_MIBIG_DB", "RGGMCI_DIAMOND", "RGGMCI_PFAM_HMM"):
        monkeypatch.delenv(key, raising=False)
    snapshot = {}
    parsers.parse_bgcs_from_zip(PUBLIC, evidence={}, core_snapshot_out=snapshot)
    options = {"label": "PUBLIC_BOUND_LABEL"}
    if profile == "off": options["reference_completion"] = "off"
    if profile == "none": options.update(reference_completion="off", contigs=None)
    expected = rg.run_archive(PUBLIC, core_snapshot=snapshot,
                              **({"contigs": parsers.extract_contig_sequences(PUBLIC)} if profile != "none" else {}), **options)
    script = """
import json,sys
if sys.argv[3] == "builtin": sys.modules["Bio"] = None
from rggmci import run
result=run(sys.argv[1], **json.loads(sys.argv[2]))
result.pop('wrapper_context',None)
print(json.dumps(result,sort_keys=True))
"""
    env = dict(os.environ, PYTHONPATH=str(generated / "src"), PYTHONDONTWRITEBYTECODE="1")
    process = subprocess.run([sys.executable, "-c", script, str(PUBLIC), json.dumps(options), "builtin" if without_bio else "available"], cwd=tmp_path,
                             env=env, capture_output=True, text=True)
    assert process.returncode == 0, process.stdout + process.stderr
    assert json.loads(process.stdout) == analytical(expected)
    assert len(expected["regions"]) == 5
    assert all(" / region" in r["identity"] for r in expected["regions"])


@pytest.mark.slow
def test_actual_mamey_gate_and_preseal_canonical_exports(tmp_path, synthetic_single_contig_full_locus_zip, monkeypatch):
    from mamey import cli
    for key in ("RGGMCI_MIBIG_DB", "RGGMCI_DIAMOND", "RGGMCI_PFAM_HMM"):
        monkeypatch.delenv(key, raising=False)
    original = cli.run_archive
    calls = []
    def observed(path, **kwargs):
        result = original(path, **kwargs)
        calls.append((kwargs, copy.deepcopy(result)))
        return result
    monkeypatch.setattr(cli, "run_archive", observed)
    label = "SYNTH_SHARED_ROUTE"
    result = cli.run_one_strain(label, label, str(synthetic_single_contig_full_locus_zip), str(tmp_path / "runs"),
                               "gold", "Synthetic metadata fixture", "unknown", release="PRIVATE", json_mode="off",
                               brief="none", locus_maps="off", reference_completion="off", rggmci_threads=1,
                               rggmci_label=label)
    assert result["status"] in {"MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES"}, result
    assert len(calls) == 1 and calls[0][0]["threads"] == 1
    assert calls[0][0]["mibig_db_registry_from"] is None
    assert calls[0][0]["core_snapshot"]["input_sha256"] == hashlib.sha256(synthetic_single_contig_full_locus_zip.read_bytes()).hexdigest()
    package = tmp_path / "runs" / label / "package"
    assert Path(result["package_zip"]).is_file()
    expected = rg.canonical_artifacts(calls[0][1], name=f"{label}_4A_RGGMCI_canonical")
    for name, payload in expected.items():
        actual = (package / name).read_bytes()
        if name.endswith(".json"):
            actual_result, expected_result = json.loads(actual), json.loads(payload)
            actual_context = actual_result.pop("wrapper_context")
            expected_context = expected_result.pop("wrapper_context")
            assert actual_context == {**expected_context, "distribution": "mamey"}
            assert actual_result == expected_result
        else:
            assert actual == payload
    assert (package / f"{label}_4A_RGGMCI_full.json").is_file()


def test_actual_residue_selection_receipt_uses_one_selection_without_process(tmp_path, monkeypatch):
    from mamey import residue_tiling
    binary, database = tmp_path / "synthetic_binary", tmp_path / "synthetic_database"
    binary.write_bytes(b"metadata-only executable binding control")
    database.write_bytes(b"metadata-only database binding control")
    calls = []
    def selected(explicit=None):
        calls.append(explicit)
        return str(binary)
    monkeypatch.setattr(residue_tiling, "find_diamond", selected)
    receipt, result = {}, {"ranked_pairs": []}
    residue_tiling.add_residue_tiling(result, "unopened.zip", [], {}, database, resource_receipt=receipt)
    assert calls == [None]
    assert result["residue_tiling_status"]["state"] == "NO_PAIRS_IN_SCOPE"
    assert receipt["residue_aligner"]["files"][binary.name]["sha256"] == hashlib.sha256(binary.read_bytes()).hexdigest()
    assert receipt["residue_database"]["files"][database.name]["sha256"] == hashlib.sha256(database.read_bytes()).hexdigest()


def test_case_only_sequence_backend_difference_has_same_context_binding(tmp_path):
    path = archive(tmp_path / "input.zip")
    lower = rg.prepare_archive_inputs(path, contigs={"SYNTH_FULL_1.1": "n" * 120})
    upper = rg.prepare_archive_inputs(path, contigs={"SYNTH_FULL_1.1": "N" * 120})
    assert lower["sequence_context"] == upper["sequence_context"]
    assert lower["contigs"] == upper["contigs"] == {"SYNTH_FULL_1.1": "N" * 120}


def test_pair_full_contig_mismatch_refuses_before_success_export(tmp_path, monkeypatch):
    path = archive(tmp_path / "input.zip")
    monkeypatch.setattr(rg, "run_rggmci", lambda *a, **k: {"ranked_pairs": [
        {"bgc_a": "BGC001", "contig_a": "WRONG_FULL.1", "bgc_b": "BGC002", "contig_b": "SYNTH_FULL_2.1"}]})
    with pytest.raises(ValueError, match="PAIR_IDENTITY_CONFLICT"):
        rg.run_archive(path, reference_completion="off")


def test_documented_on_completion_alias_resolves_to_shared_auto(tmp_path, monkeypatch):
    path = archive(tmp_path / "input.zip")
    calls = []
    def observed(*args, **kwargs):
        calls.append(kwargs["reference_completion"])
        return {"ranked_pairs": [], "related_locus_pairs": []}
    monkeypatch.setattr(rg, "run_rggmci", observed)
    result = rg.run_archive(path, reference_completion="on")
    assert calls == ["auto"]
    assert result["invocation"]["reference_completion"] == "auto"


@pytest.mark.parametrize("forgery", ["json_only", "rehashed_records", "rehashed_diagnostics", "replaced_capability"])
def test_caller_rehashed_snapshot_is_not_archive_derivation(tmp_path, forgery):
    from dataclasses import replace
    path = archive(tmp_path / "input.zip")
    snapshot = {}
    parsers.parse_bgcs_from_zip(path, evidence={}, core_snapshot_out=snapshot)
    if forgery == "json_only":
        snapshot.pop("_sealed_snapshot")
    elif forgery == "rehashed_diagnostics":
        snapshot["diagnostics"].append({"code": "CALLER_FORGED"})
    else:
        snapshot["records"][0]["products"] = ["caller_forged_annotation"]
        payload = json.dumps(snapshot["records"], sort_keys=True).encode()
        snapshot["records_sha256"] = hashlib.sha256(payload).hexdigest()
        if forgery == "replaced_capability":
            snapshot["_sealed_snapshot"] = replace(snapshot["_sealed_snapshot"], records_payload=payload,
                                                     records_sha256=snapshot["records_sha256"])
    with pytest.raises(ValueError, match="RGGMCI_CORE_SNAPSHOT"):
        rg.prepare_archive_inputs(path, core_snapshot=snapshot)


def test_process_snapshot_capability_is_immutable_and_copies_without_reparse(tmp_path, monkeypatch):
    from dataclasses import FrozenInstanceError
    path = archive(tmp_path / "input.zip")
    snapshot = {}
    parsers.parse_bgcs_from_zip(path, evidence={}, core_snapshot_out=snapshot)
    sealed = snapshot["_sealed_snapshot"]
    with pytest.raises(FrozenInstanceError): sealed.records_payload = b"[]"
    monkeypatch.setattr(rg, "iter_region_core_inputs", lambda *a, **k: pytest.fail("bound snapshot must avoid reparse"))
    assert rg.prepare_archive_inputs(path, core_snapshot=copy.deepcopy(snapshot))["records"] == snapshot["records"]


def test_json_domain_comparison_keeps_every_ordered_evidence_field():
    value = {"evidence_rows": [{"a_only_subjects": ("ONE", "TWO"), "nested": {"scores": (1, None, 3)}}],
             "ranked_pairs": [], "wrapper_context": {"distribution": "observer"}}
    actual = analytical(value)
    assert actual == {"evidence_rows": [{"a_only_subjects": ["ONE", "TWO"], "nested": {"scores": [1, None, 3]}}],
                      "ranked_pairs": []}
    changed = copy.deepcopy(actual)
    changed["evidence_rows"][0]["a_only_subjects"].reverse()
    assert changed != actual
