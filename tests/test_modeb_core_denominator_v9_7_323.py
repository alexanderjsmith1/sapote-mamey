"""v9.7.323 item 5 — package rule-based core count feeds §4_BLASTP_COVERAGE as its denominator.

authored_verify counts 'core biosynthetic' rows for the BGC into ctx['n_core_genes']; the coverage
gate then uses max(package cores, card cores), so a §4 that OMITS cores (lists 2 of 10) is caught,
not just one that under-covers the cores it lists.
"""
import csv
import mamey.modeb_structure_gate as G
from mamey.authored_verify import _bgc_context_from_package

CARD_2_COVERED = ("## §4\n| Locus | BLASTp (nr) | %id | Recon |\n|---|---|---|---|\n"
                  "| ctg1_1 ● | PKS [Streptomyces] | 88.1% | CONFIRM |\n"
                  "| ctg1_2 ● | PKS [Streptomyces] | 91.0% | CONFIRM |\n## §5\n")


def test_gate_uses_package_core_count_to_catch_omission():
    assert not G._section4_blastp_coverage_findings(CARD_2_COVERED)  # clean on its own (2/2)
    codes = [f["code"] for f in G._section4_blastp_coverage_findings(CARD_2_COVERED, {"n_core_genes": 10})]
    assert "BLASTP_THIN" in codes  # 2 of 10 package cores covered -> thin


def test_authored_verify_counts_core_biosynthetic_rows(tmp_path):
    with open(tmp_path / "AS-999_gene_by_gene_all_bgcs.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["locus_tag", "bgc_id", "gene_function_inference"])
        w.writeheader()
        for lt, bg, fn in [("ctg1_1", "BGC001", "core biosynthetic (rule-based)"),
                           ("ctg1_2", "BGC001", "core biosynthetic"),
                           ("ctg1_3", "BGC001", "transport-related"),
                           ("ctg1_9", "BGC002", "core biosynthetic")]:
            w.writerow({"locus_tag": lt, "bgc_id": bg, "gene_function_inference": fn})
    ctx = _bgc_context_from_package(str(tmp_path), "BGC001")
    assert ctx is not None and ctx.get("n_core_genes") == 2  # 2 core rows in BGC001, BGC002's not counted
