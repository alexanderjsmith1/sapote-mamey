"""The phylo manifest templates that live docs tell users to copy ship, and each tool reads its own template."""
from __future__ import annotations

import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_phylo_panel  # noqa: E402
import check_dangling_refs  # noqa: E402
import rank_clusterblast_phylo_candidates  # noqa: E402

PANEL = ROOT / "examples" / "phylo_panel_candidates.template.tsv"
SOURCES = ROOT / "examples" / "clusterblast_phylo_sources.template.tsv"


def test_templates_ship():
    assert PANEL.is_file() and SOURCES.is_file()


def test_panel_template_is_read_by_build_phylo_panel():
    rows = build_phylo_panel.read_manifest(PANEL)
    roles = {c.role for c in rows}
    assert roles == {"QUERY", "REFERENCE", "OUTGROUP"}
    anchors = [c for c in rows if c.type_anchor]
    assert len(anchors) == 1 and anchors[0].assembly_fromtype == "assembly from type material"


def test_sources_template_is_read_by_the_clusterblast_ranker():
    rows = rank_clusterblast_phylo_candidates.read_manifest(SOURCES)
    assert [r.strain_id for r in rows] == ["QUERY_001", "QUERY_002"]


def test_templates_use_placeholder_ids_only():
    for path in (PANEL, SOURCES):
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                first = next(iter(row.values()))
                assert first.startswith(("QUERY_", "REF_", "OUTGROUP_")), first
                assert "AS-" not in "\t".join(v or "" for v in row.values())


def test_dangling_scan_covers_tsv_templates():
    assert check_dangling_refs.REF.search("examples/phylo_panel_candidates.template.tsv")
    assert not check_dangling_refs.scan(ROOT)
