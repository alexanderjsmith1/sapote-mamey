"""Decision import undoes the spreadsheet formula guard.

The queue TSV is written with a leading apostrophe on any cell that starts with =, +, -
or @ (not a lone sign or a plain signed number). Feeding that TSV back as `--decisions`
used to treat "'=FS001" as a different, unknown ID. Import now removes exactly the
apostrophe the guard added, in the figure_id and decision_note columns.
"""
import csv
import json
import shutil
from pathlib import Path

import pytest

from mamey.csv_safety import csv_safe_cell
from mamey.figure_review_queue import build_review_queue
from tests.test_figure_review_queue import _fixture, _queue


@pytest.mark.parametrize("raw", ["=SUM(A1)", "+cmd", "-cmd", "@x", "\tx", "=", "-1.5x", "-FS001"])
def test_unsafe_is_inverse_of_safe_for_guarded_cells(raw):
    from mamey.csv_safety import csv_unsafe_cell
    guarded = csv_safe_cell(raw)
    assert guarded != raw
    assert csv_unsafe_cell(guarded) == raw


@pytest.mark.parametrize("cell", ["FS001", "'quoted", "'plain", "-1.5", "+3", "-", "+", "'-1.5", "'-", "", None, 7])
def test_unsafe_leaves_everything_else_alone(cell):
    from mamey.csv_safety import csv_unsafe_cell
    assert csv_unsafe_cell(cell) == cell


def _manifest_with_id(root, new_id):
    manifest = _fixture(root, count=2)
    data = json.loads(manifest.read_text())
    data["figures"][0]["figure_set_id"] = new_id
    manifest.write_text(json.dumps(data))
    return manifest


def test_guarded_id_and_note_rejoin_on_rebuild(tmp_path):
    root = tmp_path / "atlas"
    manifest = _manifest_with_id(root, "=FS001")
    first = root / "owner_review_1"
    build_review_queue(manifest, root, first, page_size=2)
    queue = first / "FIGURE_REVIEW_QUEUE.tsv"
    assert _queue(queue)[0]["figure_id"] == "'=FS001"  # the guard is in the file
    # The owner records a decision and a note that itself starts with a formula leader.
    rows = _queue(queue)
    rows[0]["decision"] = "KEEP"
    rows[0]["decision_note"] = "=check scale bar"
    edited = root / "OWNER_DECISIONS.tsv"
    with edited.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)  # plain writer: what a spreadsheet save of the queue gives back
    second = root / "owner_review_2"
    receipt = build_review_queue(manifest, root, second, decisions=edited, page_size=2)
    assert receipt["status"] == "PASS"
    kept = _queue(second / "FIGURE_REVIEW_QUEUE.tsv")[0]
    assert kept["decision"] == "KEEP"
    # Round trip is stable: the note is guarded again on write, and reads back unchanged.
    assert kept["decision_note"] == csv_safe_cell("=check scale bar")
    third = root / "owner_review_3"
    shutil.copyfile(second / "FIGURE_REVIEW_QUEUE.tsv", root / "AGAIN.tsv")
    build_review_queue(manifest, root, third, decisions=root / "AGAIN.tsv", page_size=2)
    assert _queue(third / "FIGURE_REVIEW_QUEUE.tsv")[0]["decision"] == "KEEP"


def _decide(root, queue, name, decision="KEEP"):
    rows = _queue(queue)
    rows[0]["decision"] = decision
    edited = root / name
    with edited.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return edited, rows


def test_id_that_really_starts_with_an_apostrophe_rejoins(tmp_path):
    # A manifest ID typed with its own apostrophe is written unguarded and must not lose it on import.
    root = tmp_path / "atlas"
    manifest = _manifest_with_id(root, "'=FS001")
    first = root / "owner_review_1"
    build_review_queue(manifest, root, first, page_size=2)
    assert _queue(first / "FIGURE_REVIEW_QUEUE.tsv")[0]["figure_id"] == "'=FS001"
    edited, _ = _decide(root, first / "FIGURE_REVIEW_QUEUE.tsv", "OWNER_DECISIONS.tsv")
    second = root / "owner_review_2"
    assert build_review_queue(manifest, root, second, decisions=edited, page_size=2)["status"] == "PASS"
    assert _queue(second / "FIGURE_REVIEW_QUEUE.tsv")[0]["decision"] == "KEEP"


def test_unguarded_hand_typed_id_still_rejoins(tmp_path):
    root = tmp_path / "atlas"
    manifest = _manifest_with_id(root, "=FS001")
    first = root / "owner_review_1"
    build_review_queue(manifest, root, first, page_size=2)
    edited, rows = _decide(root, first / "FIGURE_REVIEW_QUEUE.tsv", "OWNER_DECISIONS.tsv")
    rows[0]["figure_id"] = "=FS001"  # typed without the guard
    with edited.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    second = root / "owner_review_2"
    build_review_queue(manifest, root, second, decisions=edited, page_size=2)
    assert _queue(second / "FIGURE_REVIEW_QUEUE.tsv")[0]["decision"] == "KEEP"


def test_both_forms_of_one_id_are_a_duplicate(tmp_path):
    from mamey.figure_review_queue import FigureReviewQueueError
    root = tmp_path / "atlas"
    manifest = _manifest_with_id(root, "=FS001")
    first = root / "owner_review_1"
    build_review_queue(manifest, root, first, page_size=2)
    edited, rows = _decide(root, first / "FIGURE_REVIEW_QUEUE.tsv", "OWNER_DECISIONS.tsv")
    extra = dict(rows[0], figure_id="=FS001", decision="DROP")
    with edited.open("a", newline="") as handle:
        csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t").writerow(extra)
    with pytest.raises(FigureReviewQueueError) as caught:
        build_review_queue(manifest, root, root / "owner_review_2", decisions=edited, page_size=2)
    assert "DUPLICATE" in str(caught.value) or "DUPLICATE" in getattr(caught.value, "code", "")
