"""Atlas refresh: an unrecognized rank heading is held, and every generated report is hash-bound."""
import csv
import hashlib
from pathlib import Path
from tests.test_literature_atlas_current_evidence_refresh import run_tool


def _index(output):
    with (output / "REFRESH_INDEX.tsv").open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def test_unrecognized_rank_heading_withholds_the_report(tmp_path):
    completed, output = run_tool(tmp_path, "# Legacy\n\n## Rank 1 - a heading in another layout\n\nText.\n")
    assert completed.returncode == 0, completed.stderr
    row = _index(output)[0]
    assert row["status"] == "WITHHELD"
    with (output / "UNBOUND_REPORT_HOLDS.tsv").open() as f:
        hold = list(csv.DictReader(f, delimiter="\t"))[0]
    assert hold["unresolved_reasons"] == "UNRECOGNIZED_RANK_HEADING"
    assert not list((output).rglob("*CURRENT_EVIDENCE_LITERATURE_ATLAS*.md"))


def test_report_without_rank_headings_is_withheld(tmp_path):
    completed, output = run_tool(tmp_path, "# Legacy\n\nNo ranked records.\n")
    assert completed.returncode == 0, completed.stderr
    assert _index(output)[0]["status"] == "WITHHELD"


def test_generated_report_states_recognized_denominator_and_is_hashed(tmp_path):
    completed, output = run_tool(tmp_path, "# Legacy\n\n## Rank 1: AS-1 BGC001 - comparator family\n\nText.\n")
    assert completed.returncode == 0, completed.stderr
    row = _index(output)[0]
    text = Path(row["markdown"]).read_text()
    assert "each of the 1 recognized ranked loci" in text
    assert "binds every ranked locus" not in text
    assert row["markdown_sha256"] == hashlib.sha256(Path(row["markdown"]).read_bytes()).hexdigest()
