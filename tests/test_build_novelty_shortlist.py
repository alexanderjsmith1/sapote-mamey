"""build_novelty_shortlist.py — composite multi-signal novelty shortlist (advisory).

Hermetic synthetic packages. Verifies each signal fires (KCB-dark, low per-gene recognizability,
RG-GMCI linkage, cohort-unique biosynthetic domain) and that fragments are surfaced (flagged +
down-weighted) rather than excluded."""
import csv
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import build_novelty_shortlist as N  # noqa: E402


def _pkg(root, sid, inv, tri, conv, domains):
    d = os.path.join(root, sid, "package")
    os.makedirs(d)
    with open(os.path.join(d, f"{sid}_2_inventory.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["BGC_ID", "Products", "Length_kb", "KCB_top"])
        w.writeheader()
        w.writerows(inv)
    with open(os.path.join(d, f"{sid}_4_triage_board.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["BGC_ID", "Novelty_auto", "Lead_tier_auto", "RGGMCI_support"])
        w.writeheader()
        w.writerows(tri)
    with open(os.path.join(d, f"{sid}_3_mibig_convergence.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["bgc_id", "recognizable_gene_share"])
        w.writeheader()
        w.writerows(conv)
    with open(os.path.join(d, f"{sid}_domains.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["bgc_id", "domain", "pfam_acc"])
        w.writeheader()
        w.writerows(domains)
    return d


def test_signals_fire_single_package():
    with tempfile.TemporaryDirectory() as root:
        inv = [
            # KCB-dark, no convergence row -> low_recognizability
            {"BGC_ID": "BGC001", "Products": "RiPP", "Length_kb": 30, "KCB_top": ""},
            # has KCB anchor + high recognizability -> neither novelty signal
            {"BGC_ID": "BGC002", "Products": "T1PKS", "Length_kb": 40, "KCB_top": "BGC0001 | x #1"},
            # fragment (<10 kb): must be flagged, not excluded
            {"BGC_ID": "BGC003", "Products": "terpene", "Length_kb": 6, "KCB_top": ""},
        ]
        tri = [
            {"BGC_ID": "BGC001", "Novelty_auto": "50", "Lead_tier_auto": "High", "RGGMCI_support": "BGC001+BGC009"},
            {"BGC_ID": "BGC002", "Novelty_auto": "20", "Lead_tier_auto": "Inventory", "RGGMCI_support": ""},
            {"BGC_ID": "BGC003", "Novelty_auto": "40", "Lead_tier_auto": "Medium", "RGGMCI_support": ""},
        ]
        conv = [{"bgc_id": "BGC002", "recognizable_gene_share": "0.80"}]
        pkg = _pkg(root, "AS-T", inv, tri, conv, [])
        rows = {r["bgc_id"]: r for r in N.build([pkg])}
        assert rows["BGC001"]["kcb_dark"] == 1
        assert rows["BGC001"]["low_recognizability"] == 1
        assert rows["BGC001"]["rggmci_linked"] == 1
        assert rows["BGC002"]["kcb_dark"] == 0
        assert rows["BGC002"]["low_recognizability"] == 0   # 0.80 >= threshold
        assert rows["BGC002"]["best_recognizable_gene_share"] == 0.8
        # fragment surfaced (present in output) but flagged + down-weighted
        assert rows["BGC003"]["fragment_surfaced"] == 1
        assert len(rows) == 3


def test_cohort_unique_domain_signal_across_packages():
    with tempfile.TemporaryDirectory() as root:
        inv1 = [{"BGC_ID": "BGC001", "Products": "NRPS", "Length_kb": 30, "KCB_top": ""}]
        tri1 = [{"BGC_ID": "BGC001", "Novelty_auto": "40", "Lead_tier_auto": "High", "RGGMCI_support": ""}]
        # PKS_KS shared across both packages; Lasso_synth unique to package 1 (biosynthetic RiPP domain)
        dom1 = [{"bgc_id": "BGC001", "domain": "PKS_KS", "pfam_acc": "PF00109"},
                {"bgc_id": "BGC001", "domain": "Lasso_synth", "pfam_acc": "PF00000"}]
        p1 = _pkg(root, "AS-1", inv1, tri1, [], dom1)

        inv2 = [{"BGC_ID": "BGC001", "Products": "T1PKS", "Length_kb": 40, "KCB_top": ""}]
        tri2 = [{"BGC_ID": "BGC001", "Novelty_auto": "40", "Lead_tier_auto": "High", "RGGMCI_support": ""}]
        dom2 = [{"bgc_id": "BGC001", "domain": "PKS_KS", "pfam_acc": "PF00109"}]
        p2 = _pkg(root, "AS-2", inv2, tri2, [], dom2)

        rows = N.build([p1, p2])
        r1 = next(r for r in rows if r["strain"] == "AS-1")
        assert r1["n_cohort_unique_domains"] == 1
        assert "Lasso_synth" in r1["cohort_unique_domains"]
        # PKS_KS (in both packages) is NOT cohort-unique
        assert "PKS_KS" not in r1["cohort_unique_domains"]


def test_cli_writes_ranked_outputs():
    with tempfile.TemporaryDirectory() as root:
        inv = [{"BGC_ID": "BGC001", "Products": "RiPP", "Length_kb": 30, "KCB_top": ""}]
        tri = [{"BGC_ID": "BGC001", "Novelty_auto": "50", "Lead_tier_auto": "High", "RGGMCI_support": ""}]
        pkg = _pkg(root, "AS-T", inv, tri, [], [])
        with tempfile.TemporaryDirectory() as out:
            rc = N.main(["--package", pkg, "--out", out])
            assert rc == 0
            rows = list(csv.DictReader(open(os.path.join(out, "novelty_shortlist.csv"))))
            assert rows[0]["rank"] == "1"
            md = open(os.path.join(out, "novelty_shortlist.md")).read().lower()
            assert "priors, not proof" in md
