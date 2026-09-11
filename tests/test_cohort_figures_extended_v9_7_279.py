"""v9.7.279: the extended figure suite (11 cross-strain / per-BGC figures) is fused into the
cohort-figures auto-emit path and is regenerable standalone from the module. Never blocks a run."""
from __future__ import annotations
import csv
from pathlib import Path
import pytest

from mamey.cohort_figures_extended import (
    _discover_strains,
    _strain_bar_width,
    generate_extended,
)

# Measured slow on the v9.7.417 seal (>=2s for this file alone; see the INDIGO_418 timing table).
# Marked explicitly rather than inferred from the filename, so the fast partition is defined by
# measurement and a rename cannot silently change what runs.
pytestmark = pytest.mark.slow

ARCH_HEADER = ["Strain", "Rank", "BGC_ID", "Assembly_Locator", "Products",
               "architecture_archetype", "archetype_note", "n_domains", "domain_architecture_string"]
GENE_HEADER = ["bgc_id", "rank", "locus_tag", "contig", "bgc_start", "bgc_end", "cds_start", "cds_end",
               "strand", "length_bp", "aa_length", "product_qualifier", "gene_function_inference",
               "sec_met_domains", "run_depth_mode", "cctt_triggers", "bldA_tta_tier", "resistance_tier",
               "boundary_flag", "edge_core_overlap"]


def _mini_package(root: Path, sid: str):
    pk = root / sid / "package"; pk.mkdir(parents=True)
    with open(pk / f"{sid}_2_inventory.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["BGC_ID", "Products", "Length_kb", "Arch", "Boundary", "KCB_top", "KCB_score"])
        w.writerow(["BGC001", "NRPS; PKS; T1PKS", "40.0", "A", "Interior", "hit", "0"])
        w.writerow(["BGC002", "terpene", "20.0", "C", "Edge", "known", "500"])
    with open(pk / f"{sid}_gene_by_gene_all_bgcs.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(GENE_HEADER)
        w.writerow(["BGC001", "1", "ctg1_1", "NODE_1", "0", "40000", "100", "3000", "+", "2900", "966",
                    "", "core biosynthetic", "PP-binding; PKS_KS", "full_mode_b", "", "T1", "T1_X", "Interior", ""])
        w.writerow(["BGC001", "1", "ctg1_2", "NODE_1", "0", "40000", "3200", "5000", "-", "1800", "600",
                    "", "biosynthetic context", "ABC_tran", "full_mode_b", "T43-HAL_x", "T2", "T3_X", "Interior", ""])


def test_generate_extended_produces_figures(tmp_path):
    root = tmp_path / "runs"
    for sid in ("AS-001", "AS-002"):
        _mini_package(root, sid)
    assert set(_discover_strains(str(root))) == {"AS-001", "AS-002"}
    r = generate_extended(str(root), str(tmp_path / "figs"))
    assert r["figures"] >= 8, f"expected most figures to render, got {r['figures']}: {r['errors']}"
    assert (tmp_path / "figs" / "fig9_domain_cooccur.png").exists()


def test_generate_extended_never_raises_on_empty(tmp_path):
    r = generate_extended(str(tmp_path / "empty"), str(tmp_path / "figs"))
    assert r["figures"] == 0 and r["errors"]  # returns cleanly, does not raise


def test_strain_bar_width_scales_for_dense_cohort_without_dropping_members():
    assert _strain_bar_width(["AS-001", "AS-002"]) == 9.0
    dense = [f"AS-{i:03d}" for i in range(50)]
    assert _strain_bar_width(dense) == pytest.approx(20.5)
