import csv
from mamey.dualpass_ledger import merge

def test_missing_denominator_escalation_stays_in_review_queue(tmp_path):
    first = tmp_path / "first.tsv"
    second = tmp_path / "second.tsv"
    header = "task\tstrain\tbgc_id\tlocus_tag\tassertion_type\tvalue\tevidence\n"
    first.write_text(header + "t\tSYN-A\tBGC001\tg\tmetric\t70%\tunavailable\n")
    second.write_text(header + "t\tSYN-A\tBGC001\tg\tmetric\t80%\tunavailable\n")
    result = merge(first, second, tmp_path / "output", normalize=False)
    assert result["auto_resolved"] == 0
    assert result["needs_discussion"] == 1
    text = (tmp_path / "output/DIVERGENCE.tsv").read_text().splitlines()[1:]
    row = next(csv.DictReader(text, delimiter="\t"))
    assert row["auto_resolution"].startswith("ESCALATE:")
    assert row["needs_discussion"] == "yes"
