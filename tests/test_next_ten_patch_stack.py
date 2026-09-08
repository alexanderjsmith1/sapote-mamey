"""Acceptance tests for v9.7.138 research stack."""

from pathlib import Path
import csv
import zipfile

from mamey.efls import (
    LinkageEvidence, classify_linkage, forbidden_node_merge,
    write_efls_outputs,
)
from mamey.validators.modeb_full20 import missing_modeb_sections
from mamey.citations.resolver import gate_status
from mamey.background_control import streptophenazine_background
from mamey.legacy_feature_gate import validate_legacy_rows
from mamey.pre_sapote.lite import run_pre_sapote_lite
from mamey.figures.locus_renderer_v2 import render_locus_map_v2
from mamey.directed_studies.pks import DirectedPKSStudySpec, run_directed_pks_study
from mamey.directed_studies.cddr_pks import build_cddr_pks_report
from mamey.legacy_feature_gate import write_default_legacy_matrix, write_legacy_gate_outputs
from mamey.llm_handoff import build_handoff_receipt, scan_instruction_files, HANDSHAKE
from mamey.release_qa import run_release_qa
from mamey.lcms.handle_registry import write_lcms_handles, infer_handle_key
from mamey.workbooks.directed_study_workbook import write_directed_study_workbook, REQUIRED_SHEETS
from mamey.citations.resolver import write_citation_outputs, build_citation_rows
from mamey.comparators.antismash_ingest import (
    ingest_comparator_inputs,
    compare_query_to_comparator,
    compare_domain_order,
)


def test_efls_does_not_merge_streptophenazine_into_set_a():
    assert forbidden_node_merge("NODE_11", "NODE_96")
    evidence = LinkageEvidence("NODE_11", "NODE_96", forbidden_merge=True)
    assert classify_linkage(evidence) == "do_not_merge"


def test_modeb_full20_fails_missing_sections():
    missing = missing_modeb_sections("# Mode B\n\nStable identity and node-first locator")
    assert "§20 — Next actions" in missing


def test_citation_resolver_pass_structure_for_unverified_mibig():
    assert gate_status([{"citation_status": "mibig_supplied_unverified_primary"}]) == "PASS_STRUCTURE"


def test_background_control_branch_excludes_bgc011():
    branch = streptophenazine_background()
    assert branch.bgc_id == "BGC011"
    assert "excluded" in branch.activity_mapping_status


def test_legacy_feature_gate_requires_p0_recovery_action():
    failures = validate_legacy_rows([{"legacy_feature": "Run Controller", "current_status": "active"}])
    assert failures


def _write_source_csv(path: Path) -> None:
    rows = [
        {
            "node_num": "96", "record_length": "5000", "locus_tag": "ctg96_5",
            "start": "100", "end": "2600", "strand": "+", "aa_len": "900",
            "role": "PKS core", "domains_order": "CAL_domain;ACP;PKS_KS;PKS_AT;PKS_DH;PKS_KR;PKS_PP;Thioesterase",
            "product": "", "mibig_context": "LC529898 desertomycin-family comparator",
        },
        {
            "node_num": "96", "record_length": "5000", "locus_tag": "ctg96_6",
            "start": "2700", "end": "3300", "strand": "-", "aa_len": "200",
            "role": "other", "domains_order": "", "product": "hypothetical protein",
        },
        {
            "node_num": "107", "record_length": "4200", "locus_tag": "ctg107_7",
            "start": "100", "end": "2100", "strand": "+", "aa_len": "700",
            "role": "NRPS/adenylation", "domains_order": "AMP-binding;PCP;Heterocyclization;AMP-binding;PCP",
            "product": "", "mibig_context": "BGC0000116.5 nystatin-like Pseudonocardia polyene A1",
        },
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_pre_sapote_lite_blocks_unsupported_labels_and_renderer_ready(tmp_path):
    source = tmp_path / "source.csv"
    _write_source_csv(source)
    groups = {"SetA": ["NODE_96", "NODE_107"]}
    outputs = run_pre_sapote_lite(source, groups, tmp_path / "pre")
    evidence = Path(outputs["gene_evidence_table"])
    text = evidence.read_text()
    assert "ctg96_5: CAL_domain" in text
    assert "ctg96_6: hypothetical/context ORF" in text

    preflight = render_locus_map_v2(evidence, "SetA", tmp_path / "figures", "SetA_test")
    assert preflight.status == "READY"
    assert preflight.self_rating >= 9.0
    assert (tmp_path / "figures" / "SetA_test.svg").exists()
    assert (tmp_path / "figures" / "SetA_test.png").exists()
    assert (tmp_path / "figures" / "SetA_test_preflight.json").exists()


def test_directed_pks_study_consumes_pre_sapote_lite_and_emits_efls(tmp_path):
    source = tmp_path / "source.csv"
    _write_source_csv(source)
    spec = DirectedPKSStudySpec(
        study_id="SYNTH_STUDY_test",
        groups={"SetA": ["NODE_96", "NODE_107"]},
        excluded_bgcs={"BGC011": "streptophenazines purified; active antifungal likely elsewhere"},
    )
    receipt = run_directed_pks_study(source, spec, tmp_path / "study")
    assert receipt["status"] == "READY"
    assert Path(receipt["gene_evidence_table"]).exists()
    assert Path(receipt["group_machinery_summary"]).exists()
    assert Path(receipt["excluded_bgc_table"]).exists()
    assert Path(receipt["efls_outputs"]["linkage_table"]).exists()
    assert Path(receipt["lcms_outputs"]["lcms_csv"]).exists()
    assert Path(receipt["workbook"]).exists()
    assert (tmp_path / "study" / "DIRECTED_PKS_STUDY_SUMMARY.md").exists()
    assert (tmp_path / "study" / "figures" / "SYNTH_STUDY_test_SetA_locus_map.svg").exists()
    excluded_text = Path(receipt["excluded_bgc_table"]).read_text()
    assert "BGC011" in excluded_text


def test_efls_outputs_linkage_tables(tmp_path):
    source = tmp_path / "source.csv"
    _write_source_csv(source)
    outputs = run_pre_sapote_lite(source, {"SetA": ["NODE_96", "NODE_107"]}, tmp_path / "pre")
    efls = write_efls_outputs(Path(outputs["gene_evidence_table"]), tmp_path / "efls")
    assert Path(efls["linkage_table"]).exists()
    assert Path(efls["group_assignments"]).exists()
    report = Path(efls["report"]).read_text()
    assert "functional_grouping" in report or "possible_split_pathway" in report


def _minimal_gbk(locus: str = "TEST0001", product: str = "type I polyketide synthase") -> str:
    translation = "M" + ("A" * 120)
    seq = "atgc" * 1250
    return f"""LOCUS       {locus}                 5000 bp    DNA     linear   BCT 01-JAN-2000
FEATURES             Location/Qualifiers
     CDS             100..2400
                     /locus_tag="{locus}_gene1"
                     /protein_id="WP_TEST001"
                     /product="{product}"
                     /translation="{translation}"
     aSDomain        150..400
                     /aSDomain="PKS_KS"
                     /label="PKS_KS"
     aSDomain        600..900
                     /aSDomain="PKS_AT"
                     /label="PKS_AT"
     aSDomain        1200..1500
                     /aSDomain="PKS_KR"
                     /label="PKS_KR"
ORIGIN
        1 {seq}
//
"""


def test_comparator_antismash_ingest_parses_gbk_domains_and_deduplicates(tmp_path):
    gbk1 = tmp_path / "LC529898.1.gbk"
    gbk2 = tmp_path / "BGC0001215.gbk"
    text1 = _minimal_gbk("LC529898")
    text2 = _minimal_gbk("BGC0001215")
    gbk1.write_text(text1)
    gbk2.write_text(text2)
    zpath = tmp_path / "comparators.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.write(gbk1, arcname=gbk1.name)
        z.write(gbk2, arcname=gbk2.name)
    outputs = ingest_comparator_inputs([zpath], tmp_path / "comparators")
    gene_table = Path(outputs["comparator_gene_table"])
    context_table = Path(outputs["comparator_context_table"])
    assert gene_table.exists()
    assert context_table.exists()
    text = gene_table.read_text()
    assert "KS;AT;KR" in text
    assert "type I polyketide synthase" in text
    assert "duplicate_sequence_context" in context_table.read_text()


def test_comparator_pairwise_domain_similarity(tmp_path):
    source = tmp_path / "source.csv"
    _write_source_csv(source)
    outputs = run_pre_sapote_lite(source, {"SetA": ["NODE_96", "NODE_107"]}, tmp_path / "pre")
    comp_csv = tmp_path / "comparator_gene_table.csv"
    with comp_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "comparator_id", "locus_tag", "product", "domain_order"
        ])
        writer.writeheader()
        writer.writerow({
            "comparator_id": "LC529898.1",
            "locus_tag": "des_gene1",
            "product": "type I polyketide synthase",
            "domain_order": "CAL_domain;ACP;KS;AT;DH;KR;PP;TE",
        })
    out = compare_query_to_comparator(Path(outputs["gene_evidence_table"]), comp_csv, tmp_path / "pairwise")
    assert out.exists()
    assert "comparator_context_not_product_identity" in out.read_text()
    assert compare_domain_order("KS;AT;KR", "KS;AT;KR") == 1.0


def test_lcms_handle_registry_outputs_bench_guidance(tmp_path):
    source = tmp_path / "source.csv"
    _write_source_csv(source)
    outputs = run_pre_sapote_lite(source, {"SetA": ["NODE_96", "NODE_107"]}, tmp_path / "pre")
    lcms = write_lcms_handles(Path(outputs["gene_evidence_table"]), tmp_path / "lcms")
    csv_text = Path(lcms["lcms_csv"]).read_text()
    md_text = Path(lcms["lcms_md"]).read_text()
    assert "identity_safety_statement" in csv_text
    assert "candidate signal only" in csv_text or "bioinformatic candidate only" in csv_text
    assert "Comparator context is not product identity" in md_text
    assert infer_handle_key({"mibig_context": "nystatin-like polyene", "antiSMASH_domains": "KS;AT"}) == "polyene_macrolide_like"


def test_directed_study_workbook_full_output(tmp_path):
    source = tmp_path / "source.csv"
    _write_source_csv(source)
    outputs = run_pre_sapote_lite(source, {"SetA": ["NODE_96", "NODE_107"]}, tmp_path / "pre")
    efls = write_efls_outputs(Path(outputs["gene_evidence_table"]), tmp_path / "efls")
    lcms = write_lcms_handles(Path(outputs["gene_evidence_table"]), tmp_path / "lcms")
    fig_json = tmp_path / "figure_quality_receipts.json"
    fig_json.write_text('[{"figure_id":"test","group":"SetA","status":"READY","self_rating":9.2}]')
    out_xlsx = tmp_path / "directed_study.xlsx"
    result = write_directed_study_workbook(
        out_xlsx,
        study_id="SYNTH_STUDY_test",
        gene_evidence_csv=Path(outputs["gene_evidence_table"]),
        group_machinery_csv=None,
        efls_linkage_csv=Path(efls["linkage_table"]),
        efls_fragments_csv=Path(efls["fragment_summary"]),
        lcms_handles_csv=Path(lcms["lcms_csv"]),
        figure_receipt_json=fig_json,
    )
    assert result.exists()
    assert result.stat().st_size > 1000
    # Required sheet list remains stable for downstream workbook QA.
    assert "Gene_Evidence" in REQUIRED_SHEETS
    assert "LCMS_Handles" in REQUIRED_SHEETS


def test_citation_resolver_outputs_workorder_and_pass_structure(tmp_path):
    source = tmp_path / "source.csv"
    _write_source_csv(source)
    outputs = run_pre_sapote_lite(source, {"SetA": ["NODE_96", "NODE_107"]}, tmp_path / "pre")
    lcms = write_lcms_handles(Path(outputs["gene_evidence_table"]), tmp_path / "lcms")
    citations = write_citation_outputs(
        tmp_path / "citations",
        gene_evidence_csv=Path(outputs["gene_evidence_table"]),
        lcms_handles_csv=Path(lcms["lcms_csv"]),
    )
    assert Path(citations["citation_workorder"]).exists()
    assert Path(citations["citation_ledger"]).exists()
    assert Path(citations["literature_workorder"]).exists()
    assert "PASS_STRUCTURE" in Path(citations["citation_ledger"]).read_text()
    rows = build_citation_rows(gene_evidence_csv=Path(outputs["gene_evidence_table"]))
    assert rows


def test_directed_pks_wires_comparator_tracks_and_citations_into_workbook(tmp_path):
    source = tmp_path / "source.csv"
    _write_source_csv(source)
    comp_csv = tmp_path / "comparator_gene_table.csv"
    with comp_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "comparator_id", "locus_tag", "product", "domain_order"
        ])
        writer.writeheader()
        writer.writerow({
            "comparator_id": "LC529898.1",
            "locus_tag": "des_gene1",
            "product": "type I polyketide synthase",
            "domain_order": "CAL_domain;ACP;KS;AT;DH;KR;PP;TE",
        })
    spec = DirectedPKSStudySpec(
        study_id="SYNTH_STUDY_comparator_citation_test",
        groups={"SetA": ["NODE_96", "NODE_107"]},
        excluded_bgcs={"BGC011": "streptophenazines purified; active antifungal likely elsewhere"},
        comparator_gene_table=str(comp_csv),
    )
    receipt = run_directed_pks_study(source, spec, tmp_path / "study")
    assert receipt["status"] == "READY"
    assert "pairwise_domain_table" in receipt["comparator_outputs"]
    assert Path(receipt["comparator_outputs"]["pairwise_domain_table"]).exists()
    assert Path(receipt["citation_outputs"]["citation_workorder"]).exists()
    assert Path(receipt["workbook"]).exists()
    assert "comparator_context_not_product_identity" in Path(receipt["comparator_outputs"]["pairwise_domain_table"]).read_text()


def test_cddr_pks_report_type_builds_from_directed_study(tmp_path):
    source = tmp_path / "source.csv"
    _write_source_csv(source)
    comp_csv = tmp_path / "comparator_gene_table.csv"
    with comp_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "comparator_id", "locus_tag", "product", "domain_order"
        ])
        writer.writeheader()
        writer.writerow({
            "comparator_id": "LC529898.1",
            "locus_tag": "des_gene1",
            "product": "type I polyketide synthase",
            "domain_order": "CAL_domain;ACP;KS;AT;DH;KR;PP;TE",
        })
    spec = DirectedPKSStudySpec(
        study_id="SYNTH_STUDY_cddr_test",
        groups={"SetA": ["NODE_96", "NODE_107"]},
        excluded_bgcs={"BGC011": "streptophenazines purified; active antifungal likely elsewhere"},
        comparator_gene_table=str(comp_csv),
    )
    receipt = run_directed_pks_study(source, spec, tmp_path / "study")
    assert Path(receipt["cddr_pks_report"]).exists()
    cddr = build_cddr_pks_report(tmp_path / "study", tmp_path / "report")
    assert Path(cddr.report_md).exists()
    report_text = Path(cddr.report_md).read_text()
    assert "CDDR-PKS" in report_text
    assert "Comparator context is not product identity" in report_text
    assert "EFLS linkage interpretation" in report_text


def test_cli_parser_has_directed_pks_and_cddr_pks_commands():
    from mamey.cli import build_parser
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert "directed-pks-study" in choices
    assert "cddr-pks" in choices


def test_legacy_feature_matrix_gate_default_passes(tmp_path):
    matrix = tmp_path / "LEGACY_FEATURE_MATRIX.csv"
    write_default_legacy_matrix(matrix)
    outputs = write_legacy_gate_outputs(matrix, tmp_path / "legacy")
    assert outputs["status"] == "PASS"
    assert Path(outputs["receipt"]).exists()
    assert "All P0 legacy features" in Path(outputs["report"]).read_text()


def test_llm_handoff_receipt_scans_start_files(tmp_path):
    (tmp_path / "CHATGPT_START_HERE.md").write_text(f"# start\n\n{HANDSHAKE}\n")
    (tmp_path / "CLAUDE_START_HERE.md").write_text("# Claude start\n")
    receipt = build_handoff_receipt(
        tmp_path,
        llm="chatgpt",
        handshake_visible=True,
        chatgpt_safe_mode_requested=True,
    )
    assert receipt.status == "PASS"
    assert receipt.chatgpt_safe_mode_active
    assert receipt.instruction_file_count >= 2


def test_release_qa_runs_legacy_and_llm_gates(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "CHATGPT_START_HERE.md").write_text(f"# ChatGPT\n\n{HANDSHAKE}\n")
    (bundle / "CLAUDE_START_HERE.md").write_text("# Claude\n")
    receipt = run_release_qa(
        bundle,
        tmp_path / "release_qa",
        create_default_legacy_matrix=True,
        llm="chatgpt",
        handshake_visible=True,
        chatgpt_safe_mode_requested=True,
    )
    assert receipt["status"] == "PASS"
    assert (tmp_path / "release_qa" / receipt["receipt"]).exists()
    assert (tmp_path / "release_qa" / receipt["report"]).exists()


def test_llm_handoff_excludes_pycache_and_bytecode(tmp_path):
    (tmp_path / "CHATGPT_START_HERE.md").write_text(f"# ChatGPT\n\n{HANDSHAKE}\n")
    (tmp_path / "CLAUDE_START_HERE.md").write_text(f"# Claude\n\n{HANDSHAKE}\n")
    pycache = tmp_path / "mamey" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "chatgpt_commands.cpython-313.pyc").write_bytes(b"fake bytecode")
    found = scan_instruction_files(tmp_path)
    paths = [item.path for item in found]
    assert "mamey/__pycache__/chatgpt_commands.cpython-313.pyc" not in paths
    assert all("__pycache__" not in path and not path.endswith((".pyc", ".pyo")) for path in paths)


def test_release_qa_receipt_subpaths_are_relative(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "CHATGPT_START_HERE.md").write_text(f"# ChatGPT\n\n{HANDSHAKE}\n")
    (bundle / "CLAUDE_START_HERE.md").write_text(f"# Claude\n\n{HANDSHAKE}\n")
    receipt = run_release_qa(
        bundle,
        bundle / "release_qa",
        create_default_legacy_matrix=True,
        llm="chatgpt",
        handshake_visible=True,
        chatgpt_safe_mode_requested=True,
    )
    assert receipt["status"] == "PASS"
    assert Path(receipt["bundle_root"]).is_absolute()
    assert not receipt["out_dir"].startswith("/")
    assert not receipt["receipt"].startswith("/")
    assert not receipt["report"].startswith("/")
    assert not receipt["legacy_feature_gate"]["receipt"].startswith("/")
    assert not receipt["legacy_feature_gate"]["report"].startswith("/")
    assert not receipt["legacy_feature_gate"]["findings_csv"].startswith("/")
    assert not receipt["llm_handoff"]["receipt_json"].startswith("/")
    assert not receipt["llm_handoff"]["receipt_md"].startswith("/")
