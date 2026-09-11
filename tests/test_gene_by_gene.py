"""test_gene_by_gene.py — gene-by-gene top-leads table tests (v9.7.81)."""
import csv
import json
from pathlib import Path

import pytest

from mamey.gene_by_gene import build_gene_by_gene_table, _infer_role, _edge_overlap_flag


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------

def test_infer_role_core_biosynthetic():
    assert _infer_role("ketosynthase domain protein", []) == "core biosynthetic"


def test_infer_role_halogenation():
    assert _infer_role("flavin-dependent halogenase", []) == "halogenation"


def test_infer_role_resistance():
    assert _infer_role("MFS efflux transporter", []) == "self-resistance / export"


def test_infer_role_fallback():
    assert _infer_role("", []) == "biosynthetic context"


def test_edge_overlap_interior():
    assert _edge_overlap_flag("Interior", 1000, 5000, 1500, 4000, 100000) == "core"


def test_edge_overlap_full_contig():
    flag = _edge_overlap_flag("Full-contig", 0, 10000, 0, 10000, 10000)
    assert "full-contig" in flag.lower()


def test_edge_overlap_edge_proximal():
    # CDS within 5 kb of start
    flag = _edge_overlap_flag("Edge", 500, 10000, 500, 2000, 50000)
    assert "edge" in flag.lower()


# ---------------------------------------------------------------------------
# Integration: build from synthetic package
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_package(tmp_path):
    """Minimal package with triage board and manifest but no GBK files."""
    pkg = tmp_path / "MINPKG" / "package"
    pkg.mkdir(parents=True)

    manifest = {
        "strain": {"strain_id": "MINPKG"},
        "bgcs": [
            {"bgc_id": "BGC001", "contig": "NODE_1_length_80000", "products": ["NRPS"],
             "antismash_region": "region001", "edge_status": "Interior",
             "start": 10000, "end": 45000, "contig_length": 80000,
             "architecture_confidence": "A", "kcb_top": "vancomycin",
             "kcb_cumulative": 55000, "kcb_protein_hits": 18,
             "length_kb": 35.0, "cctt_triggers": ["T43-HAL"], "node_id": "NODE_1",
             "source_gbk": ""},
            {"bgc_id": "BGC002", "contig": "NODE_2_length_30000", "products": ["T1PKS"],
             "antismash_region": "region001", "edge_status": "Edge",
             "start": 0, "end": 30000, "contig_length": 30000,
             "architecture_confidence": "C", "kcb_top": "nystatin",
             "kcb_cumulative": 80268, "kcb_protein_hits": 5,
             "length_kb": 30.0, "cctt_triggers": [], "node_id": "NODE_2",
             "source_gbk": ""},
        ],
        "source_scans": {
            "blda_tta": {"per_bgc": {
                "BGC001": {"bldA_tier": "T2", "tta_codons": 2},
                "BGC002": {"bldA_tier": "T1", "tta_codons": 0},
            }},
            "resistance_tiers": {"per_bgc": {
                "BGC001": {"tier": "T3"},
                "BGC002": {"tier": "none"},
            }},
        },
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Triage board
    tb = pkg / "MINPKG_4_triage_board.csv"
    rows = [
        {"BGC_ID": "BGC001", "Contig": "NODE_1", "Products": "NRPS",
         "Standing_rule": "", "Primary_metab_flag": "",
         "AB_auto": "65", "AF_auto": "40", "Novelty_auto": "45",
         "Arch": "A", "Boundary": "Interior", "Depth_floor": "full_mode_b",
         "CCTT_triggers": "T43-HAL", "KCB_top": "vancomycin", "KCB_score": "55000"},
        {"BGC_ID": "BGC002", "Contig": "NODE_2", "Products": "T1PKS",
         "Standing_rule": "", "Primary_metab_flag": "",
         "AB_auto": "30", "AF_auto": "50", "Novelty_auto": "35",
         "Arch": "C", "Boundary": "Edge", "Depth_floor": "full_mode_b",
         "CCTT_triggers": "", "KCB_top": "nystatin", "KCB_score": "80268"},
    ]
    import csv as _csv
    with open(tb, "w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    (pkg / "MINPKG_4A_RGGMCI_ranked_pairs.csv").write_text(
        "bgc_a,bgc_b,rggmci_confidence,Score\n", encoding="utf-8"
    )
    return pkg


def test_build_writes_csv(minimal_package, tmp_path):
    result = build_gene_by_gene_table(minimal_package, top_n=5, outdir=tmp_path)
    assert Path(result["csv_path"]).exists()


def test_build_returns_correct_bgcs_covered(minimal_package, tmp_path):
    result = build_gene_by_gene_table(minimal_package, top_n=5, outdir=tmp_path)
    assert result["bgcs_covered"] == 2


def test_build_csv_has_required_columns(minimal_package, tmp_path):
    build_gene_by_gene_table(minimal_package, top_n=5, outdir=tmp_path)
    csv_path = tmp_path / "MINPKG_gene_by_gene_top_leads.csv"
    rows = list(csv.DictReader(open(csv_path)))
    required_cols = {
        "bgc_id", "locus_tag", "contig", "strand", "product_qualifier",
        "aa_length", "sec_met_domains", "run_depth_mode",
        "boundary_flag", "edge_core_overlap", "rggmci_adjacency",
        "source_gbk", "source_line_locator",
    }
    actual_cols = set(rows[0].keys()) if rows else set()
    missing = required_cols - actual_cols
    assert not missing, f"Missing required columns: {missing}"


def test_build_top_n_limits_bgcs(minimal_package, tmp_path):
    result = build_gene_by_gene_table(minimal_package, top_n=1, outdir=tmp_path)
    assert result["bgcs_covered"] == 1


def test_build_missing_triage_raises(tmp_path):
    """Missing triage board must raise FileNotFoundError."""
    pkg = tmp_path / "NOPKG" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({
        "strain": {"strain_id": "NOPKG"}, "bgcs": [], "source_scans": {}
    }), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        build_gene_by_gene_table(pkg, top_n=5, outdir=tmp_path)
