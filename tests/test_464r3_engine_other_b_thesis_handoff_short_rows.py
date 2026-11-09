# Synthetic regression inputs only.
"""A handoff index row with missing trailing cells is refused, not read as the text "None"."""
from __future__ import annotations

import json

import pytest

from mamey.thesis_handoff import ThesisHandoffError, build_thesis_handoff

ID = {"strain": "SYNTHETIC-001", "full_node_or_contig": "contig_demo_0001_complete",
      "region": "region001", "bgc_alias": "BGC007"}
COLS = ["strain", "full_node_or_contig", "region", "bgc_alias", "report_receipt",
        "report_markdown", "locus_map", "activity_tree", "claim_ceiling", "gaps"]


def _inputs(tmp_path):
    root = tmp_path / "inputs"
    root.mkdir()
    (root / "report.md").write_text("# report\n")
    (root / "map.svg").write_text("<svg/>\n")
    (root / "receipt.json").write_text(json.dumps({"identity": ID}))
    return root


def _write(tmp_path, cells):
    index = tmp_path / "index.tsv"
    index.write_text("\t".join(COLS) + "\n" + "\t".join(cells) + "\n", encoding="utf-8")
    return index


BASE = [ID["strain"], ID["full_node_or_contig"], ID["region"], ID["bgc_alias"],
        "receipt.json", "report.md", "map.svg", ""]


def test_full_row_builds(tmp_path):
    root = _inputs(tmp_path)
    index = _write(tmp_path, BASE + ["Class-level hypothesis only", "No BLASTp run"])
    assert build_thesis_handoff(index, root, tmp_path / "out")["locus_count"] == 1


@pytest.mark.parametrize("tail", [[], ["Class-level hypothesis only"]])
def test_short_row_is_refused_before_output(tmp_path, tail):
    root = _inputs(tmp_path)
    index = _write(tmp_path, BASE + tail)
    with pytest.raises(ThesisHandoffError, match="wrong number of cells"):
        build_thesis_handoff(index, root, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_extra_cells_are_refused(tmp_path):
    root = _inputs(tmp_path)
    index = _write(tmp_path, BASE + ["Class-level hypothesis only", "No BLASTp run", "stray"])
    with pytest.raises(ThesisHandoffError, match="wrong number of cells"):
        build_thesis_handoff(index, root, tmp_path / "out")


@pytest.mark.parametrize("gaps", ["NA", "None", "-"])
def test_placeholder_gaps_are_missing(tmp_path, gaps):
    root = _inputs(tmp_path)
    index = _write(tmp_path, BASE + ["Class-level hypothesis only", gaps])
    with pytest.raises(ThesisHandoffError, match="mandatory"):
        build_thesis_handoff(index, root, tmp_path / "out")
