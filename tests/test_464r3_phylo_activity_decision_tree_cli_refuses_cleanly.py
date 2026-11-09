"""build_activity_decision_trees.py reports a refusal as one line on stderr with exit 2, not a traceback."""
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_activity_decision_trees.py"


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], text=True, capture_output=True)


def test_existing_output_directory_is_a_clean_refusal(tmp_path):
    leads = tmp_path / "leads.tsv"
    leads.write_text("strain\tfull_node_or_contig\tregion\tbgc_alias\tclaim_ceiling\treport_receipt\n"
                     "EXAMPLE-1\tNODE_1_length_9000_cov_10.0\tregion001\tBGC001\tcapacity only\tr.json\n")
    (tmp_path / "rr").mkdir()
    (tmp_path / "rr" / "r.json").write_text('{"identity": {"strain": "EXAMPLE-1", "full_node_or_contig": '
                                            '"NODE_1_length_9000_cov_10.0", "region": "region001", "bgc_alias": "BGC001"}}')
    out = tmp_path / "out"
    out.mkdir()
    r = _run("--leads-tsv", leads, "--receipt-root", tmp_path / "rr", "--output-dir", out)
    assert r.returncode == 2
    assert "refused: output directory already exists" in r.stderr
    assert "Traceback" not in r.stderr


def test_empty_lead_table_is_a_clean_refusal(tmp_path):
    leads = tmp_path / "leads.tsv"
    leads.write_text("strain\n")
    r = _run("--leads-tsv", leads, "--receipt-root", tmp_path, "--output-dir", tmp_path / "out")
    assert r.returncode == 2 and "lead table is empty" in r.stderr and "Traceback" not in r.stderr


def _receipt_root(tmp_path):
    (tmp_path / "rr").mkdir()
    (tmp_path / "rr" / "r.json").write_text('{"identity": {"strain": "TST-1", "full_node_or_contig": '
                                            '"NODE_1_length_9000_cov_10.0", "region": "region001", "bgc_alias": "BGC001"}}')
    return tmp_path / "rr"


def test_short_row_without_claim_ceiling_is_refused(tmp_path):
    leads = tmp_path / "leads.tsv"
    leads.write_text("strain\tfull_node_or_contig\tregion\tbgc_alias\treport_receipt\tclaim_ceiling\n"
                     "TST-1\tNODE_1_length_9000_cov_10.0\tregion001\tBGC001\tr.json\n")
    r = _run("--leads-tsv", leads, "--receipt-root", _receipt_root(tmp_path), "--output-dir", tmp_path / "out")
    assert r.returncode == 2 and "missing claim ceiling" in r.stderr
    assert not (tmp_path / "out").exists()


def test_row_with_extra_cells_is_refused(tmp_path):
    leads = tmp_path / "leads.tsv"
    leads.write_text("strain\tfull_node_or_contig\tregion\tbgc_alias\treport_receipt\tclaim_ceiling\n"
                     "TST-1\tNODE_1_length_9000_cov_10.0\tregion001\tBGC001\tr.json\tcapacity only\textra\n")
    r = _run("--leads-tsv", leads, "--receipt-root", _receipt_root(tmp_path), "--output-dir", tmp_path / "out")
    assert r.returncode == 2 and "more cells than the header" in r.stderr


def test_short_hypothesis_cell_is_blank_not_none(tmp_path):
    leads = tmp_path / "leads.tsv"
    leads.write_text("strain\tfull_node_or_contig\tregion\tbgc_alias\treport_receipt\tclaim_ceiling\thypothesis\n"
                     "TST-1\tNODE_1_length_9000_cov_10.0\tregion001\tBGC001\tr.json\tcapacity only\n")
    r = _run("--leads-tsv", leads, "--receipt-root", _receipt_root(tmp_path), "--output-dir", tmp_path / "out")
    assert r.returncode == 0, r.stderr
    md = (tmp_path / "out" / "ACTIVITY_DECISION_TREES.md").read_text()
    assert "Hypothesis: \n" in md and "None" not in md
