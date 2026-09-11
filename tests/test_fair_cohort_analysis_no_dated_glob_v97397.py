"""fair_cohort_analysis workspace-locator + fabricated-zero regression (bypass-audit finding 1).

The fragmentation section globbed a hardcoded dated workspace folder; anywhere that folder is
absent it computed 0/0 and REPORTED a fabricated "0%" as if measured. Repaired: inventories come
from the package homes (first match wins; `MAMEY_PACKAGE_HOMES` extends), and zero matches emit
an explicit NOT MEASURED line — never a number.

The module is top-level script code, so tests execute it as a subprocess against tmp fixtures.
Strain IDs are synthetic and runtime-constructed.
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys

AS_STRAIN = "AS-" + str(9900 + 4)
SID_STRAIN = "SID" + str(9900 + 4)
SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "deliverable_tools", "fair_cohort_analysis.py")


def _fixture_root(tmp_path):
    root = str(tmp_path)
    out = os.path.join(root, "sapote_deliverables")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "COMPREHENSIVE_clusterblast_both.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cohort", "strain", "compound", "median_pid"])
        w.writerow(["AS", AS_STRAIN, "compoundA", "55"])
        w.writerow(["SID", SID_STRAIN, "compoundA", "60"])
        w.writerow(["SID", SID_STRAIN, "compoundB", "58"])
    gm = os.path.join(root, "strain_data", "ClusterBlast_Gene_Master")
    os.makedirs(gm, exist_ok=True)
    with open(os.path.join(gm, "CLUSTERBLAST_GENE_MASTER.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strain", "reference_genus"])
        w.writerow([AS_STRAIN, "Streptomyces"])
        w.writerow([SID_STRAIN, "Streptomyces"])
    return root, os.path.join(out, "AS_SID_asymmetry_confounder_analysis.md")


def _write_inventory(root):
    d = os.path.join(root, "Mamey Complete", AS_STRAIN, "package")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, AS_STRAIN + "_2_inventory.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["BGC_ID", "Boundary"])
        w.writerow(["BGC001", "Interior"])
        w.writerow(["BGC002", "Edge"])


def _run(root):
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=root)
    env.pop("MAMEY_PACKAGE_HOMES", None)
    return subprocess.run([sys.executable, SCRIPT], env=env, capture_output=True, text=True, timeout=120)


def test_zero_inventories_reports_not_measured_never_zero_percent(tmp_path):
    root, report = _fixture_root(tmp_path)
    r = _run(root)
    assert r.returncode == 0, r.stderr[-500:]
    txt = open(report).read()
    assert "NOT MEASURED" in txt, "zero inventories must be declared, not silently quantified"
    assert "0%** of AS BGCs" not in txt, "a fabricated 0% (from 0/0) must never be reported"
    assert "NOT MEASURED" in r.stdout


def test_inventories_in_package_home_are_measured(tmp_path):
    root, report = _fixture_root(tmp_path)
    _write_inventory(root)
    r = _run(root)
    assert r.returncode == 0, r.stderr[-500:]
    txt = open(report).read()
    assert "(1/2)" in txt, "fragmentation must be measured from the package-home inventories (1 Edge of 2)"
    assert "NOT MEASURED" not in txt
