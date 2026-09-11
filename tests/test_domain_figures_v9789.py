"""v9.7.89 domain-level figures: render, nonzero dims, manifest rows match files."""
from __future__ import annotations
import csv, json, os, tempfile
import pytest

pytest.importorskip("matplotlib")
from mamey.domain_figures import render_domain_figures


def _write_min_domain_level(d):
    """Write a minimal domain_level/ dir with the three input CSVs."""
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "domain_role_counts_by_bgc.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["Strain", "BGC_ID", "Assembly_Locator",
                                           "domain_role_category", "count"])
        w.writeheader()
        for role, n in [("PKS ketosynthase", 3), ("NRPS A-domain / loading", 2),
                        ("Other accessory/domain", 8), ("Redox tailoring", 1)]:
            w.writerow({"Strain": "AS-901", "BGC_ID": "BGC001",
                        "Assembly_Locator": "NODE_1_length_5000 region001",
                        "domain_role_category": role, "count": n})
        w.writerow({"Strain": "AS-901", "BGC_ID": "BGC002",
                    "Assembly_Locator": "NODE_2_length_3000 region001",
                    "domain_role_category": "Lanthipeptide maturation", "count": 4})
    with open(os.path.join(d, "domain_complexity_metrics_by_bgc.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["Strain", "Rank", "BGC_ID", "Assembly_Locator",
                                           "Products", "Domain_total", "Unique_domain_names",
                                           "Domain_CDS_count", "Biosynthetic_core_domain_count",
                                           "Tailoring_domain_count", "Transport_domain_count",
                                           "Regulatory_domain_count"])
        w.writeheader()
        w.writerow({"Strain": "AS-901", "Rank": 1, "BGC_ID": "BGC001",
                    "Assembly_Locator": "NODE_1_length_5000 region001", "Products": "NRPS; PKS",
                    "Domain_total": 14, "Unique_domain_names": 10, "Domain_CDS_count": 5,
                    "Biosynthetic_core_domain_count": 5, "Tailoring_domain_count": 1,
                    "Transport_domain_count": 0, "Regulatory_domain_count": 0})
        w.writerow({"Strain": "AS-901", "Rank": 2, "BGC_ID": "BGC002",
                    "Assembly_Locator": "NODE_2_length_3000 region001", "Products": "RiPP",
                    "Domain_total": 4, "Unique_domain_names": 3, "Domain_CDS_count": 2,
                    "Biosynthetic_core_domain_count": 4, "Tailoring_domain_count": 0,
                    "Transport_domain_count": 0, "Regulatory_domain_count": 0})
    with open(os.path.join(d, "domain_rows_long.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["Strain", "Rank", "BGC_ID", "Assembly_Locator",
                                           "locus_tag", "cds_start", "cds_end", "strand",
                                           "domain_name", "domain_description", "evalue",
                                           "domain_role_category", "BGC_products", "KCB_top",
                                           "AB_score", "AF_score"])
        w.writeheader()
        for i, (dom, role, strand) in enumerate([
                ("PKS_KS", "PKS ketosynthase", 1), ("PKS_AT", "PKS acyltransferase/loading", 1),
                ("AMP-binding", "NRPS A-domain / loading", -1), ("PCP", "Carrier protein / PP-binding", 1)]):
            w.writerow({"Strain": "AS-901", "Rank": 1, "BGC_ID": "BGC001",
                        "Assembly_Locator": "NODE_1_length_5000 region001",
                        "locus_tag": f"ctg1_{i}", "cds_start": 100 + i * 500,
                        "cds_end": 400 + i * 500, "strand": strand, "domain_name": dom,
                        "domain_description": "", "evalue": "1e-20",
                        "domain_role_category": role, "BGC_products": "NRPS; PKS",
                        "KCB_top": "", "AB_score": 50, "AF_score": 40})
        for i, (dom, role) in enumerate([("LANC_like", "Lanthipeptide maturation"),
                                          ("DUF4135", "Lanthipeptide maturation")]):
            w.writerow({"Strain": "AS-901", "Rank": 2, "BGC_ID": "BGC002",
                        "Assembly_Locator": "NODE_2_length_3000 region001",
                        "locus_tag": f"ctg2_{i}", "cds_start": 100 + i * 500,
                        "cds_end": 400 + i * 500, "strand": 1, "domain_name": dom,
                        "domain_description": "", "evalue": "1e-30",
                        "domain_role_category": role, "BGC_products": "RiPP",
                        "KCB_top": "", "AB_score": 30, "AF_score": 20})


def test_figures_render_with_nonzero_dims_and_manifest(tmp_path):
    dl = str(tmp_path / "domain_level")
    _write_min_domain_level(dl)
    res = render_domain_figures(dl)
    assert res["status"] == "OK", res["warnings"]
    # at least the heatmap, core burden, and 2 strips
    assert len(res["figures"]) >= 4
    figdir = os.path.join(dl, "figures")
    # every figure file exists and is nonzero
    for f in res["figures"]:
        p = os.path.join(figdir, f)
        assert os.path.exists(p) and os.path.getsize(p) > 0, f
        assert os.path.exists(os.path.splitext(p)[0] + ".svg"), f
    receipts = [json.loads(line) for line in open(os.path.join(figdir, "figure_receipts.jsonl"))]
    assert {row["figure_id"] + ".png" for row in receipts} == set(res["figures"])
    # manifest rows match the produced files 1:1
    man = os.path.join(figdir, "figure_manifest.csv")
    assert os.path.exists(man)
    with open(man, newline="") as fh:
        man_files = {r["filename"] for r in csv.DictReader(fh)}
    assert man_files == set(res["figures"])
    # companion data CSVs for the two summary figures
    assert os.path.exists(os.path.join(figdir, "domain_role_burden_heatmap_data.csv"))
    assert os.path.exists(os.path.join(figdir, "core_biosynthetic_domain_burden_data.csv"))


def test_figures_skip_card_when_no_tables(tmp_path):
    dl = str(tmp_path / "empty_domain_level")
    os.makedirs(dl)
    res = render_domain_figures(dl)
    assert res["status"] == "SKIPPED"
    assert os.path.exists(os.path.join(dl, "figures",
                                       "DOMAIN_LEVEL_FIGURES_SKIPPED_NO_TABLE.md"))
