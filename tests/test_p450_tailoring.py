"""Tests for the P450-tailoring classifier (roadmap #11). Freeze-safe report layer."""
import csv

try:
    from mamey import p450_tailoring as p4
except ImportError:
    import p450_tailoring as p4


def _write_gene_table(path, rows, products="NRPS; PKS"):
    cols = ["bgc_id", "locus_tag", "cds_start", "cds_end", "product_qualifier",
            "gene_function_inference", "sec_met_domains", "bgc_products", "af_score", "ab_score"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            d = {c: "" for c in cols}
            d.update(r)
            d.setdefault("bgc_products", products)
            w.writerow(d)


def _p450_row(bgc, tag):
    return {"bgc_id": bgc, "locus_tag": tag, "sec_met_domains": "p450 SMCOG1007: cytochrome P450",
            "product_qualifier": "biosynthetic-additional", "bgc_products": "NRPS; PKS"}


def test_three_clustered_p450_is_crosslinker(tmp_path):
    tbl = tmp_path / "SYN-1_gene_by_gene_all_bgcs.csv"
    _write_gene_table(tbl, [_p450_row("BGC010", f"ctg1_{i}") for i in range(3)])
    res = p4.run(str(tmp_path), out_dir=str(tmp_path))
    assert res["status"] == "ok"
    assert res["p450_genes"] == 3 and res["cassette_bgcs"] == 1


def test_two_p450_is_oxidative_tailoring(tmp_path):
    tbl = tmp_path / "SYN-2_gene_by_gene_all_bgcs.csv"
    _write_gene_table(tbl, [_p450_row("BGC020", f"ctg2_{i}") for i in range(2)])
    p4.run(str(tmp_path), out_dir=str(tmp_path))
    with open(tmp_path / "P450_TAILORING" / "P450_BY_BGC.tsv") as fh:
        rows = [r for r in csv.DictReader((l for l in fh if not l.startswith("#")), delimiter="\t")]
    assert rows[0]["role_prior"] == "oxidative-tailoring"


def test_gpa_sharpening_needs_glycopeptide_anchor(tmp_path):
    # a >=3-P450 NRPS cassette WITHOUT a glycopeptide anchor is NOT a GPA call (real cohort P450-cassette lesson)
    tbl = tmp_path / "SYN-3_gene_by_gene_all_bgcs.csv"
    _write_gene_table(tbl, [_p450_row("BGC030", f"ctg3_{i}") for i in range(4)], products="NRPS")
    p4.run(str(tmp_path), out_dir=str(tmp_path))
    with open(tmp_path / "P450_TAILORING" / "P450_BY_BGC.tsv") as fh:
        rows = [r for r in csv.DictReader((l for l in fh if not l.startswith("#")), delimiter="\t")]
    assert rows[0]["role_prior"] == "crosslinker-candidate"  # NOT "(GPA)"


def test_gpa_call_with_balhimycin_anchor(tmp_path):
    # same cassette + a glycopeptide KCB anchor on the triage board -> sharpened to GPA
    tbl = tmp_path / "SYN-4_gene_by_gene_all_bgcs.csv"
    _write_gene_table(tbl, [_p450_row("BGC040", f"ctg4_{i}") for i in range(5)], products="NRPS; PKS")
    board = tmp_path / "SYN-4_4_triage_board.csv"
    with open(board, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "KCB_top"])
        w.writerow(["BGC040", "BGC0000311.6 | balhimycin | knownclusterblast #1"])
    p4.run(str(tmp_path), out_dir=str(tmp_path))
    with open(tmp_path / "P450_TAILORING" / "P450_BY_BGC.tsv") as fh:
        rows = [r for r in csv.DictReader((l for l in fh if not l.startswith("#")), delimiter="\t")]
    assert rows[0]["role_prior"] == "crosslinker-candidate (GPA)"


def test_non_p450_genes_ignored(tmp_path):
    tbl = tmp_path / "SYN-5_gene_by_gene_all_bgcs.csv"
    _write_gene_table(tbl, [{"bgc_id": "BGC050", "locus_tag": "ctg5_1",
                             "sec_met_domains": "PKS_KS PKS_AT", "product_qualifier": "biosynthetic"}])
    res = p4.run(str(tmp_path), out_dir=str(tmp_path))
    assert res["p450_genes"] == 0
