"""Known-answer full report joins; every accession/strain/category below is synthetic.

The first test spies only the external gappa/R subprocess boundaries. The second
uses an explicitly selected actual Rscript and the same real native producer,
report, metadata builder, diagnostic renderer and artifact admission. Neither
case establishes biological type material, geography or sequence identity.
"""
import csv
import hashlib
import itertools
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
Phylo = pytest.importorskip("Bio.Phylo")
from tools import phylo_place as native, graft_integrity as gi

TYPE = "MZ000001_1_Genus_alpha_strain_A1_16S_ribosomal_RNA_partial_sequence"
UNKNOWN = "NR_000002_1_Genus_beta_strain_B2_16S_ribosomal_RNA_partial_sequence"
OMIT = "NR_000003_1_Genus_gamma_strain_C3_16S_ribosomal_RNA_partial_sequence"
OG = "Outgenus_thermophila_ATCC_1_NR_000009_1_outgroup_for_Genus_Outgenus_thermophila_strain_ATCC_1_16S_ribosomal_RNA_partial_sequence"
QUERY = "QUERY"
LABELS = {
    TYPE: "MZ000001.1 Genus alpha strain A1 16S ribosomal RNA, partial sequence",
    UNKNOWN: "NR_000002.1 Genus beta strain B2 16S ribosomal RNA, partial sequence",
    OMIT: "NR_000003.1 Genus gamma strain C3 16S ribosomal RNA, partial sequence",
    OG: "NR_000009.1 Outgenus thermophila strain ATCC 1 16S ribosomal RNA, partial sequence [outgroup for Genus]",
    QUERY: "Synthetic public query",
}
REFERENCE = f"(({TYPE}:0.2,{UNKNOWN}:0):0.3,{OMIT}:0.1,{OG}:0.5);\n"
BACKBONE = f"(({TYPE}:0.2{{0}},{UNKNOWN}:0.1053605157{{1}}):0.3{{2}},{OMIT}:0.1{{3}},{OG}:0.5{{4}}){{5}};"
RAW = f"(({TYPE}:0.2,({UNKNOWN}:0.04,{QUERY}:0.07):0.0653605157):0.3,{OMIT}:0.1,{OG}:0.5);\n"
# Hand-summed paths from the specified reference edges after zero-edge restoration.
# These are independent expected values, not calculated using an implementation metric helper.
DISTANCES = {
    frozenset((TYPE, UNKNOWN)): .20, frozenset((TYPE, QUERY)): .27,
    frozenset((UNKNOWN, QUERY)): .07, frozenset((TYPE, OMIT)): .60,
    frozenset((UNKNOWN, OMIT)): .40, frozenset((QUERY, OMIT)): .47,
    frozenset((TYPE, OG)): 1.0, frozenset((UNKNOWN, OG)): .80,
    frozenset((QUERY, OG)): .87, frozenset((OMIT, OG)): .60,
}
TYPE_LABEL = "Genus alpha A1 [Type; Marine-associated; South America] (MZ000001.1)"
UNKNOWN_LABEL = "Genus beta B2 [Soil; Europe] (NR_000002.1)"
QUERY_LABEL = "Synthetic public query [Soil; Europe]"


def _write_table(path, rows):
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    return path


def _rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _fixture(tmp_path, *, owner_tip=QUERY):
    run = tmp_path/"run"; place = run/"place"; report = run/"report"; ref = run/"refpkg"
    for path in (place, report, ref): path.mkdir(parents=True)
    sources = dict(jplace=place/"epa_result.jplace", reference_tree=ref/"ref.tree",
                   reference_alignment=ref/"ref.aln.fasta", query_alignment=place/"query.aligned.fasta",
                   model=ref/"ref.bestModel", placement_provenance=place/"_provenance.json",
                   reference_provenance=ref/"_provenance.json")
    data = dict(tree=BACKBONE, fields=["edge_num", "likelihood", "like_weight_ratio", "distal_length", "pendant_length"],
                placements=[dict(n=[QUERY], p=[[1, -1, 1, .04, .07]])])
    sources["jplace"].write_text(json.dumps(data))
    sources["reference_tree"].write_text(REFERENCE)
    # Tiny synthetic placeholder alignments are bound by the producer, never searched/inferred.
    sources["reference_alignment"].write_text("".join(f">{tip}\nACGT\n" for tip in (TYPE, UNKNOWN, OMIT, OG)))
    sources["query_alignment"].write_text(">QUERY\nACGA\n")
    sources["model"].write_text("GTR+G")
    sources["placement_provenance"].write_text('{"group":"Genus"}')
    sources["reference_provenance"].write_text('{"molecule":"nucleotide","model":"GTR+G","n_ref":4,"versions":{"synthetic_source":"recorded_fixture"}}')
    labelmap = _write_table(place/"labelmap.tsv", [dict(safe=tip, original=label) for tip, label in LABELS.items()])
    owner = _write_table(tmp_path/"owner table.tsv", [dict(tip=owner_tip, label=QUERY_LABEL, sample_id="Synthetic experiment 1",
                  role="query", source_category="Soil", geography_category="Europe", Candida="", MRSA="", label_original=LABELS[QUERY])])
    resolved = _write_table(tmp_path/"resolved table.tsv", [
        dict(exact_accession="MZ000001.1", verification_status="STRAIN_CONFIRMED", isolation_source="marine sponge", location="Brazil", evidence_url="https://example.org/synthetic/A1", isolation_source_provenance="synthetic deposited source", location_provenance="synthetic deposited location"),
        dict(exact_accession="NR_000002.1", verification_status="STRAIN_CONFIRMED", isolation_source="forest soil", location="Italy", evidence_url="https://example.org/synthetic/B2", isolation_source_provenance="synthetic deposited source", location_provenance="synthetic deposited location"),
        dict(exact_accession="NR_000003.1", verification_status="STRAIN_CONFIRMED", isolation_source="soil", location="Not recorded", evidence_url="https://example.org/synthetic/C3", isolation_source_provenance="synthetic deposited source", location_provenance="synthetic missing location"),
        dict(exact_accession="NR_000009.1", verification_status="STRAIN_CONFIRMED_NO_METADATA", isolation_source="Not recorded", location="Not recorded", evidence_url="https://example.org/synthetic/OG", isolation_source_provenance="synthetic missing source", location_provenance="synthetic missing location"),
    ])
    proof = dict(tip=TYPE, accession="MZ000001.1", source_accession="MZ000001.1", taxon="Genus alpha", strain="A1",
                 role="type_reference", type_strain_of="Genus alpha", type_evidence="synthetic explicit type-material record",
                 review_state="REVIEWED", source_url="https://example.org/synthetic/type-A1", strain_identity_basis="synthetic exact deposited strain A1")
    reviewed = _write_table(tmp_path/"reviewed type.tsv", [proof])
    args = SimpleNamespace(outdir=str(report), jplace=str(sources["jplace"]), refpkg=str(ref), taxonomy=None,
                           owner_table=[str(owner)], owner_table_original=[], resolved_metadata=[str(resolved)],
                           reviewed=[str(reviewed)], query_override=[], query_prefix="ZZ", threads=2, rscript="synthetic-Rscript")
    inputs = list(sources.values()) + [labelmap, owner, resolved, reviewed]
    before = {str(path): path.read_bytes() for path in inputs}
    return run, report, sources, args, proof, before


def _fake_r_outputs(child, variant):
    """Independent tiny child outputs; intentionally not valid images or actual R proof."""
    md = _rows(child/"metadata.tsv")
    # Literal known-answer retained geometry; never copy the producer's displayed tree.
    (child/"tree_display.newick").write_text(f"({TYPE}:0.2,{UNKNOWN}:0,{QUERY}:0.07);\n")
    stem = f"EPAng_Genus_R04_{variant}"
    for extension in ("png", "pdf"):
        (child/f"{stem}.{extension}").write_bytes(b"synthetic image boundary; no graphics claim")
    (child/f"{stem}_caption.txt").write_text("synthetic external R boundary only")
    (child/"R_SESSION.txt").write_text("synthetic boundary; R never executed")
    _write_table(child/f"{stem}_display_audit.tsv", [dict(tip=row["tip"],
        label=row["label"] + (" {"+row["sample_id"]+"}" if variant=="experiment_id" and row["role"]=="query" else ""),
        source=row["source_category"], geography=row["geography_category"], Candida="", MRSA="") for row in md])
    _write_table(child/f"{stem}_validation.tsv", [dict(check=check, status="PASS") for check in
        ("tip_metadata_bijection", "retained_pairwise_branch_distances", "source_category_palette", "geography_category_palette")])


def _run_report(tmp_path, monkeypatch, args, *, real_r=None):
    # Initialize matplotlib's font inventory before installing the explicit external-tool spy.
    # The actual diagnostic renderer below stays unpatched and produces its real tiny images.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot  # noqa: F401
    original_run = subprocess.run
    selected = Path(real_r) if real_r else tmp_path/"selected synthetic Rscript"
    if not real_r:
        selected.write_text("synthetic executable identity only; never executed")
    actual_which = shutil.which
    monkeypatch.setattr(shutil, "which", lambda command: str(selected) if str(command) in {"synthetic-Rscript", str(selected)} else actual_which(command))
    monkeypatch.setattr(native, "_which", lambda command, *bins: "synthetic-gappa" if command=="gappa" else None)
    monkeypatch.setattr(native, "ROOT", str(tmp_path/"no-ancillary-signoff"))
    args.rscript = str(selected)
    calls = []
    def dispatch(argv, **kwargs):
        calls.append((list(argv), kwargs))
        if argv[0]=="synthetic-gappa":
            assert argv[1:3]==["examine", "graft"] and kwargs["check"] is True
            Path(argv[argv.index("--out-dir")+1], "epa_result.newick").write_text(RAW)
            return SimpleNamespace(returncode=0)
        assert Path(argv[0])==selected and Path(argv[1]).name=="render_placement_COLOR_STRIPS.R"
        assert argv[-1] in {"concise", "experiment_id"}
        child = Path(kwargs["cwd"])
        assert child.is_absolute() and Path(argv[1]).parent==child and Path(argv[1]).is_file()
        assert all(kwargs["env"][key]=="2" for key in gi.RESOURCE_KEYS)
        if real_r:
            # A selected failing graphics runtime remains a failure; no alternative renderer.
            return original_run(argv, **dict(kwargs, timeout=120))
        _fake_r_outputs(child, argv[-1])
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(subprocess, "run", dispatch)
    result = native.cmd_report(args)
    return result, calls


def _assert_full_report(report, sources, proof, before, calls, *, real_r=False):
    assert {path: Path(path).read_bytes() for path in before} == before
    assert len(calls)==3 and calls[0][0][0]=="synthetic-gappa"
    assert [row[0][-1] for row in calls[1:]]==["concise", "experiment_id"]
    summary_path = report/"Genus_REPORT_ATTEMPT.json"
    summary = json.loads(summary_path.read_text())
    assert summary["state"]=="COMPLETE" and summary["length_state"]=="PASS_LENGTH_QA"
    assert summary["profile"]=="metadata requested"
    admission = gi.admit_graft_length_evidence(summary["length_receipt"], sources)
    raw, restored = [Path(admission["selected"][field]) for field in ("raw", "restored")]
    assert raw.read_text()==RAW and raw.read_bytes()!=restored.read_bytes()
    restored_tree = Phylo.read(restored, "newick")
    assert {tip.name for tip in restored_tree.get_terminals()}==set(LABELS)
    for pair, expected in DISTANCES.items():
        first, second = tuple(pair)
        assert restored_tree.distance(first, second)==pytest.approx(expected, abs=1e-12)
    assert next(tip for tip in restored_tree.get_terminals() if tip.name==UNKNOWN).branch_length==0
    assert gi.query_pendant_paths(restored_tree, {TYPE, UNKNOWN, OMIT, OG})[QUERY]==pytest.approx(.07, abs=1e-12)
    best = _rows(report/"Genus_placements.tsv")
    assert best==[dict(query=LABELS[QUERY], best_edge="1", best_edge_lwr="1.000", pendant_length="0.0700", distal_length="0.0400")]
    alternatives = _rows(report/"Genus_placement_alternatives.tsv")
    assert len(alternatives)==1 and alternatives[0]["query_id"]==QUERY
    assert alternatives[0]["retained_placement_count"]=="1" and alternatives[0]["retained_lwr_sum"]=="1.000000"
    neighbors = _rows(report/"Genus_neighborhoods.tsv")
    assert neighbors==[dict(as_query=LABELS[QUERY], nearest_type_strain=LABELS[TYPE], patristic_dist="0.2700",
                           nearest_reference_any="NR 000002.1 Genus beta strain B2 16S ribosomal RNA, partial sequence", nearest_reference_dist="0.0700")]
    diagnostic = summary["diagnostic_figure"]
    assert diagnostic["state"]=="PRODUCED_DIAGNOSTIC" and diagnostic["sha256"]==_digest(diagnostic["path"])
    diagnostic_roles = json.loads((report/"Genus_placement_tree.svg.labels.json").read_text())
    assert diagnostic_roles["roles"][TYPE]=="reference_type"
    assert diagnostic_roles["roles"][UNKNOWN]=="reference_nontype"
    assert diagnostic_roles["roles"][QUERY]=="query"
    strips = summary["metadata_strips"]
    assert strips["requested"] and strips["state"]=="RENDERED_WITH_OMISSIONS"
    assert strips["kept"]==3 and strips["omitted"]==2
    built = strips["builder"]; panel = Path(built["dir"])
    assert built["query_kept"]==1 and built["owner_joins"]=={QUERY:QUERY}
    assert built["query_role_basis"]=="exact jplace roster"
    assert set(built["kept_tips"])=={TYPE, UNKNOWN, QUERY} and set(built["omitted_tips"])=={OMIT, OG}
    assert (panel/"tree_input.newick").read_bytes()==Path(diagnostic["path"]).read_bytes()
    md = {row["tip"]:row for row in _rows(panel/"metadata.tsv")}
    assert md[TYPE]["label"]==TYPE_LABEL and md[TYPE]["type_display"]=="Type"
    assert md[UNKNOWN]["label"]==UNKNOWN_LABEL and md[UNKNOWN]["type_display"]==""
    assert md[QUERY]["label"]==QUERY_LABEL and md[QUERY]["role"]=="query"
    assert md[QUERY]["sample_id"]=="Synthetic experiment 1" and md[QUERY]["Candida"]==md[QUERY]["MRSA"]==""
    omission = {row["tip"]:row for row in _rows(panel/"OMITTED_TIPS.tsv")}
    assert "no deposited or reviewed geography" in omission[OMIT]["reason"]
    assert "used for rooting, then dropped" in omission[OG]["reason"]
    context = {row["field"]:row["value"] for row in _rows(panel/"figure_context.tsv")}
    assert {key:context[key] for key in ("input_tips","kept_tips","input_queries","kept_queries","omitted_queries")}==dict(input_tips="5",kept_tips="3",input_queries="1",kept_queries="1",omitted_queries="0")
    assert context["length_state"]=="PASS_LENGTH_QA" and context["length_receipt_sha256"]==_digest(summary["length_receipt"])
    actual_proof = json.loads((panel/"TYPE_EVIDENCE.json").read_text())
    expected_proof = {key:value for key,value in proof.items() if key!="accession"}
    assert actual_proof["roles"]=={TYPE:expected_proof} and summary["reviewed_type_evidence"]==actual_proof
    provenance = {(row["tip"],row["field"]):row for row in _rows(panel/"METADATA_PROVENANCE.tsv")}
    assert provenance[(TYPE,"type_material")]["provenance"]=="SOURCE_REVIEWED"
    assert provenance[(TYPE,"type_material")]["evidence_url"]==proof["source_url"]
    assert provenance[(UNKNOWN,"type_material")]["provenance"]=="NOT_RECORDED"
    assert provenance[(QUERY,"source")]["provenance"]=="OWNER_REGISTRY"
    for record in built["artifacts"]:
        assert _digest(record["path"])==record["sha256"]
    for path, record in summary["metadata_source_bindings"].items():
        assert Path(path).read_bytes()==before[path] and _digest(path)==record["sha256"]
    assert _digest(strips["receipt"])==strips["receipt_sha256"]
    disk_strips = json.loads(Path(strips["receipt"]).read_text())
    assert disk_strips["state"]=="RENDERED_WITH_OMISSIONS" and disk_strips["builder"]==built
    for record in summary["table_artifacts"] + diagnostic["artifacts"]:
        assert _digest(record.get("path",record.get("creation_path")))==record["sha256"]
    for variant, child_record in zip(("concise","experiment_id"),strips["variants"]):
        assert child_record["state"]=="RENDERED" and child_record["variant"]==variant
        assert child_record["executable_before"]==child_record["executable_after"]
        assert _digest(child_record["receipt"])==child_record["receipt_sha256"]
        child = Path(child_record["receipt"]).parent
        disk_receipt = json.loads(Path(child_record["receipt"]).read_text())
        assert disk_receipt["state"]=="RENDERED" and disk_receipt["argv"]==child_record["argv"]
        for record in disk_receipt["inputs"].values():
            assert _digest(record["creation_path"])==record["sha256"]
        for artifact in child_record["artifacts"]:
            assert _digest(artifact["path"])==artifact["sha256"]
        displayed = Phylo.read(child/"tree_display.newick", "newick")
        assert {tip.name for tip in displayed.get_terminals()}=={TYPE,UNKNOWN,QUERY}
        for first,second in itertools.combinations((TYPE,UNKNOWN,QUERY),2):
            assert displayed.distance(first,second)==pytest.approx(DISTANCES[frozenset((first,second))], abs=1e-12)
        audit = {row["tip"]:row for row in _rows(child/f"EPAng_Genus_R04_{variant}_display_audit.tsv")}
        assert audit[TYPE]["label"]==TYPE_LABEL and "[Type;" not in audit[UNKNOWN]["label"]
        assert audit[QUERY]["label"]==QUERY_LABEL + (" {Synthetic experiment 1}" if variant=="experiment_id" else "")
        assert audit[TYPE]["source"]=="Marine-associated" and audit[TYPE]["geography"]=="South America"
        assert audit[UNKNOWN]["source"]=="Soil" and audit[UNKNOWN]["geography"]=="Europe"
        if real_r:
            assert audit[TYPE]["source_colour"]=="#332288" and audit[TYPE]["geography_colour"]=="#D55E00"
            assert (child/f"EPAng_Genus_R04_{variant}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
            assert (child/f"EPAng_Genus_R04_{variant}.pdf").read_bytes().startswith(b"%PDF-")
            caption = (child/f"EPAng_Genus_R04_{variant}_caption.txt").read_text()
            assert "Displayed 3 of 5 source tips and 1 of 1 query tips; 0 query tips omitted" in caption
            assert "Unknown type status is unmarked" in caption
            assert "accession prefixes do not establish type material" in caption
            assert "Length evidence state: PASS_LENGTH_QA" in caption
            assert "units are not independently established by this renderer" in caption
            assert "Branch lengths are substitutions per site" not in caption
            assert "This display does not establish species identity or biological activity" in caption
    assert {path:Path(path).read_bytes() for path in before}==before


def test_real_length_producer_report_metadata_builder_and_fake_r_close_exact_query_join(tmp_path, monkeypatch):
    _run, report, sources, args, proof, before = _fixture(tmp_path)
    result, calls = _run_report(tmp_path, monkeypatch, args)
    assert result==0
    _assert_full_report(report, sources, proof, before, calls)


def test_wrong_owner_query_row_holds_actual_report_before_any_r_child(tmp_path, monkeypatch):
    _run, report, sources, args, _proof, before = _fixture(tmp_path, owner_tip="PUBLIC_QUERY_01")
    result, calls = _run_report(tmp_path, monkeypatch, args)
    assert result==2 and len(calls)==1 and calls[0][0][0]=="synthetic-gappa"
    summary = json.loads((report/"Genus_REPORT_ATTEMPT.json").read_text())
    assert summary["length_state"]=="PASS_LENGTH_QA" and summary["state"]=="HOLD"
    strips = summary["metadata_strips"]
    assert strips["requested"] and strips["state"]=="HOLD_REQUESTED_STRIPS"
    assert "STRIP_NO_QUERY_OR_EMPTY_DISPLAY" in strips["reason"] and strips["variants"]==[]
    assert strips["builder"]["query_kept"]==0 and strips["builder"]["owner_joins"]=={}
    omission = {row["tip"]:row for row in _rows(Path(strips["builder"]["dir"])/"OMITTED_TIPS.tsv")}
    assert omission[QUERY]["reason"].startswith("query row absent")
    assert (report/"Genus_placements.tsv").is_file() and (report/"Genus_neighborhoods.tsv").is_file()
    assert {path:Path(path).read_bytes() for path in before}==before


def test_explicit_real_r_full_report_preserves_reviewed_non_nr_type_and_nr_unknown(tmp_path, monkeypatch):
    selected = os.environ.get("SAPOTE_TEST_RSCRIPT")
    if not selected:
        pytest.skip("root-selected actual R graphics gate not requested; synthetic child tests are not R validation")
    executable = Path(selected).absolute()
    assert executable.is_file() and os.access(executable,os.X_OK)
    _run, report, sources, args, proof, before = _fixture(tmp_path)
    result, calls = _run_report(tmp_path, monkeypatch, args, real_r=executable)
    assert result==0
    _assert_full_report(report, sources, proof, before, calls, real_r=True)
