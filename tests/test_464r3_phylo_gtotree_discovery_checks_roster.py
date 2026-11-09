"""plan_gtotree_iqtree discover (direct route): the nominated alignment's labels must equal the
Genomes_summary_info.tsv roster of genomes with in_final_tree=Yes, named by `label` when the run used a
label map and by `assembly_id` otherwise. Layout copied from real GToTree 1.8 outputs; values synthetic."""
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

TOOL = Path(__file__).resolve().parents[1] / "tools" / "plan_gtotree_iqtree.py"
sys.path.insert(0, str(TOOL.parents[1]))
SPEC = importlib.util.spec_from_file_location("plan_gtotree_roster_464r3", TOOL)
tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tool
SPEC.loader.exec_module(tool)

COLS = "assembly_id\tlabel\tlabel_source\ttaxid\tnum_SCG_hits\tuniq_SCG_hits\tperc_comp\tperc_redund\tnum_SCG_hits_after_len_filt\tin_final_tree\n"
COLS_NOLABEL = "assembly_id\ttaxid\tnum_SCG_hits\tuniq_SCG_hits\tperc_comp\tperc_redund\tnum_SCG_hits_after_len_filt\tin_final_tree\n"


def _run(tmp_path, summary, alignment, admitted=3):
    run = tmp_path / "run"
    out = run / "outputs/gtotree_alignment"
    out.mkdir(parents=True)
    (run / "RUN_MANIFEST.json").write_text(json.dumps({"run_id": "x", "panel_policy": {"admitted_unique_assemblies": admitted}}))
    (out / "Genomes_summary_info.tsv").write_text(summary)
    (out / "Aligned_SCGs_mod_names.faa").write_text(alignment)
    receipt = tmp_path / "receipt.json"
    rc = tool.discover_outputs(SimpleNamespace(run_dir=str(run), receipt=str(receipt)))
    return rc, json.loads(receipt.read_text())


def _row(asm, label, final):
    return f"{asm}\t{label}\tuser_map\tNA\t136\t130\t98.55\t4.35\t126\t{final}\n"


def test_labels_matching_final_roster_pass_and_dropped_genome_is_not_counted(tmp_path):
    summary = COLS + _row("h1", "EXAMPLE-1", "Yes") + _row("h2", "Genus_b_GCF_1_OUTGROUP", "Yes") + _row("h3", "Genus_c_GCF_2", "No")
    rc, data = _run(tmp_path, summary, ">EXAMPLE-1\nAAAA\n>Genus_b_GCF_1_OUTGROUP\nAAAA\n")
    assert rc == 0 and data["status"] == "PASS_UNIQUE_ALIGNMENT"
    assert data["retained_taxa_from_summary"] == 2 and data["retained_roster_column"] == "label"


def test_label_mismatch_is_held(tmp_path):
    summary = COLS + _row("h1", "EXAMPLE-1", "Yes") + _row("h2", "Genus_b_GCF_1_OUTGROUP", "Yes")
    rc, data = _run(tmp_path, summary, ">EXAMPLE-1\nAAAA\n>Genus_b_GCF_9\nAAAA\n")
    assert rc == 2 and data["status"] == "HOLD_ROSTER_MISMATCH"
    row = next(r for r in data["observed_files"] if r["relative_path"].endswith(".faa"))
    assert row["alignment_problem"].startswith("ROSTER_MISMATCH")
    assert "Genus_b_GCF_1_OUTGROUP" in row["alignment_problem"] and "Genus_b_GCF_9" in row["alignment_problem"]


def test_unlabelled_run_uses_assembly_id(tmp_path):
    summary = COLS_NOLABEL + "GCF_1.1_genomic\tNA\t1\t1\t99\t0\t1\tYes\nGCF_2.1_genomic\tNA\t1\t1\t99\t0\t1\tYes\n"
    rc, data = _run(tmp_path, summary, ">GCF_1.1_genomic\nAA\n>GCF_2.1_genomic\nAA\n")
    assert rc == 0 and data["retained_roster_column"] == "assembly_id"
