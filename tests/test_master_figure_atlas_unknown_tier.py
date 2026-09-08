"""COH-04: the dual-priority atlas must not silently drop UNKNOWN/blank assembly-tier strains.

Before the fix the scatter iterated a hardcoded ["GOOD","MODERATE","POOR","VERY_POOR"] list, so a
strain whose assembly_tier was blank/UNKNOWN got NO scatter marker yet still fed the medians, the
per-strain labels, and the sidecar CSV — a strain visible in every readout but invisible on the plot.
The fix iterates the tiers actually present (with an UNKNOWN bucket), mirroring cross_strain_figures.
"""
import csv
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

from mamey.master_figure_atlas import (  # noqa: E402
    MasterFigureInput, _fig_dual_priority_atlas, ASSEMBLY_COLORS,
)


def _input_with_unknown_tier():
    strain_summary = [
        {"strain_id": "AS-1", "assembly_tier": "GOOD",
         "top_antibacterial_score": 80, "top_antifungal_score": 40,
         "top_antibacterial_products": "RiPP", "top_antifungal_products": "NRPS",
         "top_antibacterial_locator": "NODE_1 (BGC001)", "top_antifungal_locator": "NODE_2 (BGC002)"},
        {"strain_id": "AS-2", "assembly_tier": "",   # <- blank tier == UNKNOWN bucket
         "top_antibacterial_score": 55, "top_antifungal_score": 70,
         "top_antibacterial_products": "PKS", "top_antifungal_products": "nucleoside",
         "top_antibacterial_locator": "NODE_3 (BGC003)", "top_antifungal_locator": "NODE_4 (BGC004)"},
    ]
    return MasterFigureInput(strain_summary=strain_summary, special_buckets=[],
                             top_antibacterial=[], top_antifungal=[], source_file="test")


def test_unknown_tier_strain_is_plotted_and_bucketed(tmp_path):
    data = _input_with_unknown_tier()
    entry = _fig_dual_priority_atlas(data, tmp_path)
    # the figure renders without error and produces its sidecar CSV
    csvs = list(Path(tmp_path).glob("*_cross_strain_dual_priority_node_first_data.csv"))
    assert csvs, "dual-priority sidecar CSV not written"
    # the sidecar's first line is a `# provenance` row; the real header follows
    with open(csvs[0]) as fh:
        lines = fh.read().splitlines()
    header = next(i for i, ln in enumerate(lines) if ln.startswith("strain_id"))
    rows = list(csv.DictReader(lines[header:]))
    tiers = {r["assembly_tier"] for r in rows}
    strains = {r["strain_id"] for r in rows}
    # both strains are in the CSV (they always were) ...
    assert strains == {"AS-1", "AS-2"}
    # ... and the blank tier is now normalized to an explicit UNKNOWN bucket, not left blank/dropped
    assert "UNKNOWN" in tiers
    assert "" not in tiers


def test_unknown_bucket_has_a_color():
    # the fix added an explicit UNKNOWN color so the scatter marker is drawn (not the empty-string key)
    assert "UNKNOWN" in ASSEMBLY_COLORS
