"""v9.7.160: post-seal figure images are excluded from checksums_sha256.txt.

Regression for the gold-into-existing-smoke-dir checksum FAIL: matplotlib re-emits
byte-different PNGs on every render, and figures render AFTER the checksum seal, so
including figure images in the checksum set caused a deterministic validate FAIL on
any re-run into a populated package dir. The fig_*_data.csv companions (the numbers)
stay checksummed; only the rendered images are excluded.
"""
from mamey.packaging import is_checksum_excluded


def test_figure_images_excluded():
    assert is_checksum_excluded("smoke_figures/fig_assembly_tier.png") is True
    assert is_checksum_excluded("gold_figures/F01_perBGC_domain_heatmap.png") is True
    assert is_checksum_excluded("locus_maps/BGC001_locus_map.svg") is True


def test_figure_data_csvs_NOT_excluded():
    """The companion data CSVs carry the numbers and don't get re-rendered — keep them checksummed."""
    assert is_checksum_excluded("smoke_figures/fig_assembly_tier_data.csv") is False
    assert is_checksum_excluded("gold_figures/F01_perBGC_domain_heatmap_data.csv") is False
    assert is_checksum_excluded("locus_maps/BGC001_locus_map_data.csv") is False


def test_core_artifacts_NOT_excluded():
    """Non-figure artifacts must stay in the checksum set (the gate keeps its teeth)."""
    for rel in ["manifest.json", "S_X_2_inventory.csv", "deep_data.json",
                "S_X_gene_context.jsonl", "S_X_4_triage_board.csv"]:
        assert is_checksum_excluded(rel) is False


def test_windows_style_separators_handled():
    assert is_checksum_excluded("smoke_figures\\fig_x.png") is True
