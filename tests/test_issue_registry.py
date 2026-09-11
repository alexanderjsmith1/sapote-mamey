import csv
import json

import pytest

from mamey.issue_registry import (
    IssueEvent,
    proposed_convention_issue,
    write_issue_surfaces,
)


def test_typed_issue_surfaces_are_synchronized_and_user_visible(tmp_path):
    event = proposed_convention_issue(
        "A local point-label convention was proposed.",
        stage="FIGURE_DESIGN",
        impact="Could be mistaken for an established statistical term.",
        correction="Removed after review.",
        status="CORRECTED",
    )
    receipt = write_issue_surfaces(tmp_path, [event], terminal_status="MAMEY_COMPLETE_WITH_ISSUES")

    assert receipt["event_count"] == 1
    row = json.loads((tmp_path / "issue_log.jsonl").read_text().strip())
    assert row["event_id"] == "ISSUE-0001"
    assert row["origin_class"] == "CODEX_PROPOSED"
    assert row["status"] == "CORRECTED"

    with (tmp_path / "issue_log.tsv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["summary"] == row["summary"]
    markdown = (tmp_path / "issue_log.md").read_text(encoding="utf-8")
    assert "CODEX_PROPOSED" in markdown
    assert "locally proposed convention" in markdown


def test_legacy_strings_are_preserved_without_inventing_detail(tmp_path):
    write_issue_surfaces(tmp_path, ["[WARN] optional renderer skipped: dependency unavailable"])
    row = json.loads((tmp_path / "issue_log.jsonl").read_text().strip())
    assert row["category"] == "DEGRADATION"
    assert row["origin_class"] == "SOFTWARE_REPORTED"
    assert "dependency unavailable" in row["summary"]


def test_invalid_provenance_class_fails_closed():
    with pytest.raises(ValueError, match="origin_class"):
        IssueEvent(
            severity="WARN",
            category="OTHER",
            summary="test",
            origin_class="SECRETLY_INVENTED",
        ).validated()
