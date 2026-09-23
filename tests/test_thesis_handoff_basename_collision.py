"""Test that build_thesis_handoff refuses a basename collision among selected artifacts.

Two selected artifacts (e.g. the report and the locus map) that resolve to same-basename
files in different directories would be copied to the same target via shutil.copy2, silently
overwriting one another and dropping an artifact from the handoff while the checksum/ZIP still
report success. The guard fails closed instead.

v9.7.438 patch: claude-alex-2026-40. Target: sapote-mamey-v9.7.437 (engine 1.9.167).
"""
import csv
import json

import pytest

from mamey.thesis_handoff import ThesisHandoffError, build_thesis_handoff

ID = {
    "strain": "SYNTHETIC-001",
    "full_node_or_contig": "contig_demo_0001_complete",
    "region": "region001",
    "bgc_alias": "BGC007",
}


def _write_index(tmp_path, root, **overrides):
    row = dict(
        ID,
        report_receipt="receipt.json",
        report_markdown="report.md",
        locus_map="map.svg",
        activity_tree="",
        gaps="expression; metabolomics",
        claim_ceiling="Class-level hypothesis only",
    )
    row.update(overrides)
    (root / "receipt.json").write_text(json.dumps({"identity": ID}))
    index = tmp_path / "index.tsv"
    with index.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=row, delimiter="\t")
        writer.writeheader()
        writer.writerow(row)
    return index


def test_refuses_basename_collision(tmp_path):
    root = tmp_path / "inputs"
    root.mkdir()
    # report and locus map live in different directories but share a basename
    (root / "a").mkdir()
    (root / "a" / "dup.txt").write_text("# report\n")
    (root / "b").mkdir()
    (root / "b" / "dup.txt").write_text("<svg/>\n")
    index = _write_index(tmp_path, root, report_markdown="a/dup.txt", locus_map="b/dup.txt")
    with pytest.raises(ThesisHandoffError, match="basename collision"):
        build_thesis_handoff(index, root, tmp_path / "out")
    # fails closed: no partial output directory is left behind by the raise path
    assert not (tmp_path / "out").exists() or not (tmp_path / "out" / "THESIS_HANDOFF.zip").exists()


def test_distinct_basenames_still_build(tmp_path):
    # the guard is a no-op on the normal distinct-basename case
    root = tmp_path / "inputs"
    root.mkdir()
    (root / "report.md").write_text("# report\n")
    (root / "map.svg").write_text("<svg/>\n")
    index = _write_index(tmp_path, root)
    receipt = build_thesis_handoff(index, root, tmp_path / "out")
    assert receipt["zip_crc"] == "PASS"
