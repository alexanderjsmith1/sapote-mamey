"""The placement display always emits an explicit, machine-readable dropped-tip ledger."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _module():
    spec = importlib.util.spec_from_file_location(
        "placement_display_under_test", ROOT / "tools" / "placement_display.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HEADER = (
    "tip\trepresentative_tip\taction\tmismatches_to_representative\tshared_columns\t"
    "max_pair_mismatches\tmin_pair_shared_columns\toriginal_metadata_json\n"
)


def test_dropped_tips_is_present_and_contains_only_removed_tips(tmp_path):
    ledger = tmp_path / "panel_collapse_ledger.tsv"
    ledger.write_text(
        HEADER
        + 'A\tA\tRETAINED\t0\t100\t\t\t{}\n'
        + 'B\tA\tCOLLAPSED_MEMBER\t0\t100\t0\t100\t{}\n'
        + 'O\tO\tOUTGROUP_PRUNED_FOR_DISPLAY\t0\t100\t\t\t{}\n',
        encoding="utf-8",
    )
    out = tmp_path / "DROPPED_TIPS.tsv"
    assert _module().write_dropped_tips(ledger, out) == 2
    text = out.read_text(encoding="utf-8")
    assert text.startswith(HEADER)
    assert "\nB\tA\tCOLLAPSED_MEMBER\t" in text
    assert "\nO\tO\tOUTGROUP_PRUNED_FOR_DISPLAY\t" in text
    assert "\nA\t" not in text


def test_no_drop_still_writes_header_only_ledger(tmp_path):
    ledger = tmp_path / "panel_collapse_ledger.tsv"
    ledger.write_text(HEADER + 'A\tA\tRETAINED\t0\t100\t\t\t{}\n', encoding="utf-8")
    out = tmp_path / "DROPPED_TIPS.tsv"
    assert _module().write_dropped_tips(ledger, out) == 0
    assert out.read_text(encoding="utf-8") == HEADER


def test_unknown_collapse_action_is_refused(tmp_path):
    ledger = tmp_path / "panel_collapse_ledger.tsv"
    ledger.write_text(HEADER + 'A\tA\tSILENTLY_GONE\t0\t100\t\t\t{}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="COLLAPSE_LEDGER_ROW_INVALID"):
        _module().write_dropped_tips(ledger, tmp_path / "DROPPED_TIPS.tsv")


def test_complete_methods_are_computed_from_bound_artifacts(tmp_path):
    module = _module()
    run = tmp_path / "run"
    out = tmp_path / "display"
    (run / "refpkg").mkdir(parents=True)
    (run / "place").mkdir()
    (run / "report").mkdir()
    out.mkdir()
    refs = run / "refpkg" / "ref.aln.fasta"
    queries = run / "place" / "query.aligned.fasta"
    refs.write_text(">REF_NR_000001_1\nACGT\n>OUTGROUP_NR_000002_1\nACGT\n")
    queries.write_text(">AS_1\nACGT\n")
    (run / "report" / "epa_result.newick").write_text(
        "(REF_NR_000001_1:0.1,OUTGROUP_NR_000002_1:0.1,AS_1:0.1);\n")
    (run / "report" / "example_placement_FIGURE_CAPTION.txt").write_text(
        "Tools: mafft v7.5; raxml-ng v2.0; epa-ng v0.3; gappa v0.9.\n")
    (run / "refpkg" / "reference_dedup.tsv").write_text(
        "action\tspecies\nkept\ta\nkept\tb\n")
    prefix = out / "example"
    Path(f"{prefix}_display.nwk").write_text(
        "(REF_NR_000001_1:0.1,OUTGROUP_NR_000002_1:0.1,AS_1:0.1);\n")
    Path(f"{prefix}_collapse_ledger.tsv").write_text(
        "tip\trepresentative_tip\taction\nREF_NR_000001_1\tREF_NR_000001_1\tRETAINED\n"
        "OUTGROUP_NR_000002_1\tOUTGROUP_NR_000002_1\tRETAINED\nAS_1\tAS_1\tRETAINED\n")
    Path(f"{prefix}_reference_selection.tsv").write_text(
        "query_tip\treference_tip\tneighbor_rank\tpatristic_distance\tselection_mode\n"
        "AS_1\tREF_NR_000001_1\t1\t0.2\tnearest_per_query\n")
    png, pdf = out / "example.png", out / "example.pdf"
    png.write_bytes(b"png")
    pdf.write_bytes(b"pdf")
    rows = [
        {"tip": "REF_NR_000001_1", "role": "reference", "category": "soil", "source": "Brazil"},
        {"tip": "OUTGROUP_NR_000002_1", "role": "outgroup", "category": "", "source": ""},
        {"tip": "AS_1", "role": "query", "category": "moss", "source": "USA"},
    ]
    args = SimpleNamespace(group="example", name="example", label_style="withloc", max_nt=0,
                           min_cols=500, keep_all_references=False, neighbors_per_query=1)
    ledger, methods = module.write_methods_package(
        run, out, prefix, refs, queries, rows, [], "OUTGROUP_NR_000002_1", args, 0, png, pdf)
    data = json.loads(ledger.read_text())
    assert data["counts"]["reference_alignment_records"] == 2
    assert data["counts"]["query_alignment_records"] == 1
    assert data["counts"]["alignment_columns"] == 4
    assert data["counts"]["analysis_tree_tips"] == 3
    assert data["counts"]["final_display_tips"] == 3
    assert data["counts"]["query_reference_pairings"] == 1
    text = methods.read_text()
    for tool in ("MAFFT", "RAxML-NG", "EPA-ng", "gappa", "ggtree", "ggplot2"):
        assert tool in text


def test_project_accession_cannot_be_reused_as_reference(tmp_path):
    module = _module()
    host = tmp_path / "host.tsv"
    host.write_text("strain\tgenbank_accession\nAS-1\tPX123456.1\n")
    builder = module._load("build_placement_ggtree_inputs")
    rows = [{"tip": "REF_PX123456_1", "role": "reference"}]
    with pytest.raises(ValueError, match="PROJECT_STRAIN_IN_REFERENCE_ROLE"):
        module.refuse_project_strains_as_references(rows, str(host), builder)


def test_display_grouping_key_is_species_not_genus():
    module = _module()
    rows = module.display_rows([
        {"tip": "REF_A", "kind": "reference", "ref_label": "Streptomyces alpha (NR_000001)",
         "reference_species": "Streptomyces alpha", "reference_genus": "Streptomyces"},
        {"tip": "REF_B", "kind": "reference", "ref_label": "Streptomyces beta (NR_000002)",
         "reference_species": "Streptomyces beta", "reference_genus": "Streptomyces"},
    ])
    assert [row["taxon"] for row in rows] == ["Streptomyces alpha", "Streptomyces beta"]


def test_pruned_display_accepts_full_alignment_but_refuses_a_missing_tip(tmp_path):
    module = _module()
    full_tree = tmp_path / "full.nwk"
    pruned_tree = tmp_path / "pruned.nwk"
    alignment = tmp_path / "all.fasta"
    full_tree.write_text("(query_A:0.1,ref_B:0.1,ref_C:0.2);\n", encoding="utf-8")
    pruned_tree.write_text("(query_A:0.1,ref_B:0.1);\n", encoding="utf-8")
    alignment.write_text(">query_A\nAAAA\n>ref_B\nAAAT\n>ref_C\nAATT\n", encoding="utf-8")

    assert set(module.coverage_check(full_tree, alignment)) == {"query_A", "ref_B", "ref_C"}
    with pytest.raises(ValueError, match="ALIGNMENT_COVERAGE"):
        module.coverage_check(pruned_tree, alignment)
    assert set(module.coverage_check(
        pruned_tree, alignment, allow_alignment_superset=True
    )) == {"query_A", "ref_B"}

    missing = tmp_path / "missing.fasta"
    missing.write_text(">query_A\nAAAA\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ALIGNMENT_COVERAGE"):
        module.coverage_check(pruned_tree, missing, allow_alignment_superset=True)
