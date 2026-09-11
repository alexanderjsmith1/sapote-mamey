"""v9.7.289: the .277 cohort-precompute gap is closed — COHORT_resistance_signals populates from
the manifest.json resistance_gene_summary fallback, and COHORT_BGC_FULL_TALLY from the *_4_triage_board.csv
fallback, when the standalone primary sources aren't gold-package artifacts. Fixture test."""
from __future__ import annotations
import csv, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "build_cohort_precompute.py"


def _mini_pkg(root: Path, sid: str):
    pk = root / sid / "package"; pk.mkdir(parents=True)
    with open(pk / f"{sid}_2_inventory.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["BGC_ID", "Products", "Length_kb", "Arch", "Boundary", "KCB_top", "KCB_score"])
        w.writerow(["BGC001", "NRPS", "40.0", "A", "Interior", "hit", "0"])
    # triage board -> BGC_FULL_TALLY fallback source
    with open(pk / f"{sid}_4_triage_board.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Strain", "Rank", "Assembly_Locator", "BGC_ID", "User_Label", "Contig", "Node_ID",
                    "antiSMASH_Region", "Products", "Boundary", "Arch", "Arch_Capacity", "Class_Conf"])
        w.writerow([sid, "1", "NODE_1_length_40000.region001", "BGC001", "", "NODE_1_length_40000", "NODE_1_length_40000", "region001",
                    "NRPS", "Interior", "A", "high", "high"])
    # manifest.json resistance_gene_summary -> resistance_signals fallback source
    (pk / "manifest.json").write_text(json.dumps({
        "resistance_gene_summary": {
            "counts": {"Beta_lactamase_fold": 1},
            "bgc_coupling": {"BGC001": ["Beta_lactamase_fold"]},
            "tier_counts": {"T2_RESISTANCE_LIKE": 1},
        }
    }), encoding="utf-8")


def test_resistance_and_tally_populate_from_package(tmp_path):
    runs = tmp_path / "runs"; _mini_pkg(runs, "AS-001")
    out = tmp_path / "out"; out.mkdir()
    r = subprocess.run([sys.executable, str(TOOL), "--runs-dir", str(runs), "--out", str(out)],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    res = out / "COHORT_resistance_signals_by_bgc.csv"
    tally = out / "COHORT_BGC_FULL_TALLY.csv"
    assert res.exists() and sum(1 for _ in open(res)) > 1, f"resistance_signals empty (.277 gap):\n{r.stderr}"
    assert tally.exists() and sum(1 for _ in open(tally)) > 1, f"BGC_FULL_TALLY empty (.277 gap):\n{r.stderr}"
