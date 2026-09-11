"""realistic_bgc_count.py — corrected-denominator BGC count (advisory). Hermetic synthetic package.

Verifies: (1) context-only regions are dropped as marginal, (2) a HIGH RG-GMCI pair collapses two
REAL regions into one, (3) a region with biosynthetic machinery but a bare 'other' class still
counts (fragment-surfacing), (4) MODERATE RG-GMCI pairs do NOT merge."""
import csv
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import realistic_bgc_count as R  # noqa: E402


def _pkg(root, sid, inv_rows, gbg_rows, rggmci_rows):
    d = os.path.join(root, sid, "package")
    os.makedirs(d)
    json.dump({"strain_id": sid}, open(os.path.join(d, "manifest.json"), "w"))
    with open(os.path.join(d, f"{sid}_2_inventory.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["BGC_ID", "Products", "Length_kb", "Boundary"])
        w.writeheader()
        w.writerows(inv_rows)
    with open(os.path.join(d, f"{sid}_gene_by_gene_all_bgcs.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["bgc_id", "gene_function_inference", "resistance_tier"])
        w.writeheader()
        w.writerows(gbg_rows)
    with open(os.path.join(d, f"{sid}_4A_RGGMCI_ranked_pairs.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["bgc_a", "bgc_b", "rggmci_confidence"])
        w.writeheader()
        w.writerows(rggmci_rows)
    return d


def test_marginal_merge_and_fragment_surfacing():
    with tempfile.TemporaryDirectory() as root:
        inv = [
            {"BGC_ID": "BGC001", "Products": "T1PKS", "Length_kb": 40, "Boundary": "Interior"},
            {"BGC_ID": "BGC002", "Products": "NRPS", "Length_kb": 30, "Boundary": "Edge"},
            # context-only: bare 'other' class, no machinery -> marginal
            {"BGC_ID": "BGC003", "Products": "other", "Length_kb": 5, "Boundary": "Edge"},
            # fragment (<10 kb) but has core machinery + bare class -> still REAL (surfaced)
            {"BGC_ID": "BGC004", "Products": "other", "Length_kb": 6, "Boundary": "Edge"},
        ]
        gbg = [
            {"bgc_id": "BGC001", "gene_function_inference": "core biosynthetic", "resistance_tier": ""},
            {"bgc_id": "BGC002", "gene_function_inference": "core biosynthetic", "resistance_tier": ""},
            {"bgc_id": "BGC003", "gene_function_inference": "biosynthetic context", "resistance_tier": ""},
            {"bgc_id": "BGC004", "gene_function_inference": "core biosynthetic", "resistance_tier": ""},
        ]
        # HIGH pair BGC001+BGC002 -> one biological cluster; a MODERATE pair must NOT merge
        rggmci = [
            {"bgc_a": "BGC001", "bgc_b": "BGC002", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE"},
            {"bgc_a": "BGC001", "bgc_b": "BGC004", "rggmci_confidence": "MODERATE_RG_GMCI"},
        ]
        pkg = _pkg(root, "AS-T", inv, gbg, rggmci)
        s = R.score_package(pkg)
        assert s["Raw_regions"] == 4
        assert s["Marginal_dropped"] == 1          # BGC003 dropped
        assert s["n_high_rggmci_merges"] == 1      # only the HIGH pair merged
        assert s["Merged_away"] == 1               # BGC001+BGC002 collapse to one
        # 4 raw - 1 marginal(BGC003) - 1 merged = 2 realistic (BGC001+2 as one, BGC004 alone)
        assert s["Realistic_count"] == 2
        assert s["Inflation_pct"] == 50


def test_resistance_tier_counts_as_machinery():
    with tempfile.TemporaryDirectory() as root:
        inv = [{"BGC_ID": "BGC001", "Products": "other", "Length_kb": 8, "Boundary": "Edge"}]
        # no core/tailoring role, but a T1 resistance tier -> machinery present -> REAL
        gbg = [{"bgc_id": "BGC001", "gene_function_inference": "biosynthetic context",
                "resistance_tier": "T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED"}]
        pkg = _pkg(root, "AS-T", inv, gbg, [])
        s = R.score_package(pkg)
        assert s["Realistic_count"] == 1 and s["Marginal_dropped"] == 0


def test_cli_writes_csv_and_summary():
    with tempfile.TemporaryDirectory() as root:
        inv = [{"BGC_ID": "BGC001", "Products": "T1PKS", "Length_kb": 40, "Boundary": "Interior"}]
        gbg = [{"bgc_id": "BGC001", "gene_function_inference": "core biosynthetic", "resistance_tier": ""}]
        pkg = _pkg(root, "AS-T", inv, gbg, [])
        with tempfile.TemporaryDirectory() as out:
            rc = R.main(["--package", pkg, "--out", out])
            assert rc == 0
            rows = list(csv.DictReader(open(os.path.join(out, "realistic_bgc_count.csv"))))
            assert rows[0]["Realistic_count"] == "1"
            summ = json.load(open(os.path.join(out, "realistic_bgc_count_summary.json")))
            # claim-safety statement is present in the emitted summary
            assert "Advisory" in summ["claim_safety"]


# --- v9.7.409 F2 (realistic_count_two_denominators): the two "corrected" denominators are made
# explicit and single-sourced. These fail on the sealed .408 base (no Corrected_count_bw field,
# no BOUNDARY_WEIGHT constant) and pass after CLAUDE_409_scoring.

import build_cohort_html as BCH  # noqa: E402  (tools/ already on sys.path)


def test_boundary_weight_table_single_sourced():
    """The boundary-weight table (Rule A) must be byte-equal in both tools — the drift guard that
    keeps the SSOT 'corrected count' constant from re-forking."""
    assert R.BOUNDARY_WEIGHT == BCH.BOUNDARY_WEIGHT


def test_both_denominators_emitted_and_agree_with_rule_a():
    """score_package now surfaces BOTH denominators; the boundary-weighted one reproduces Rule A
    (build_cohort_html.py) exactly, and is a *different* number from the distinct-loci count."""
    with tempfile.TemporaryDirectory() as root:
        inv = [
            {"BGC_ID": "BGC001", "Products": "T1PKS", "Length_kb": 40, "Boundary": "Interior"},
            {"BGC_ID": "BGC002", "Products": "NRPS", "Length_kb": 30, "Boundary": "Edge"},
            {"BGC_ID": "BGC003", "Products": "other", "Length_kb": 5, "Boundary": "Edge"},   # marginal
            {"BGC_ID": "BGC004", "Products": "other", "Length_kb": 6, "Boundary": "Edge"},   # REAL fragment
        ]
        gbg = [
            {"bgc_id": "BGC001", "gene_function_inference": "core biosynthetic", "resistance_tier": ""},
            {"bgc_id": "BGC002", "gene_function_inference": "core biosynthetic", "resistance_tier": ""},
            {"bgc_id": "BGC003", "gene_function_inference": "biosynthetic context", "resistance_tier": ""},
            {"bgc_id": "BGC004", "gene_function_inference": "core biosynthetic", "resistance_tier": ""},
        ]
        rggmci = [{"bgc_a": "BGC001", "bgc_b": "BGC002", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE"}]
        pkg = _pkg(root, "AS-T", inv, gbg, rggmci)
        s = R.score_package(pkg)
        # Rule A computed the way build_cohort_html.py does: weight EVERY region by its boundary.
        rule_a = sum(BCH.BOUNDARY_WEIGHT.get((r["Boundary"] or "").strip(), 0.0) for r in inv)
        assert rule_a == 2.5                       # 1.0(Interior) + 3*0.5(Edge)
        assert s["Corrected_count_bw"] == rule_a   # the two code paths now AGREE on Rule A
        # ...and it is genuinely a different denominator from the distinct-loci count.
        assert s["Realistic_count"] == 2
        assert s["Corrected_count_bw"] != s["Realistic_count"]


def test_cli_csv_and_summary_carry_both_denominators():
    with tempfile.TemporaryDirectory() as root:
        inv = [{"BGC_ID": "BGC001", "Products": "T1PKS", "Length_kb": 40, "Boundary": "Interior"},
               {"BGC_ID": "BGC002", "Products": "NRPS", "Length_kb": 30, "Boundary": "Edge"}]
        gbg = [{"bgc_id": "BGC001", "gene_function_inference": "core biosynthetic", "resistance_tier": ""},
               {"bgc_id": "BGC002", "gene_function_inference": "core biosynthetic", "resistance_tier": ""}]
        pkg = _pkg(root, "AS-T", inv, gbg, [])
        with tempfile.TemporaryDirectory() as out:
            assert R.main(["--package", pkg, "--out", out]) == 0
            rows = list(csv.DictReader(open(os.path.join(out, "realistic_bgc_count.csv"))))
            assert "Corrected_count_bw" in rows[0]
            assert rows[0]["Corrected_count_bw"] == "1.5"   # 1.0 + 0.5
            summ = json.load(open(os.path.join(out, "realistic_bgc_count_summary.json")))
            assert summ["total_corrected_count_bw"] == 1.5
            # the note names both denominators so they are never silently compared
            assert "distinct" in summ["denominator_note"].lower()
            assert "boundary-weighted" in summ["denominator_note"].lower()
