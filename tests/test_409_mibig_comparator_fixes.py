"""Fail-before / pass-after for CLAUDE_409_mibig_comparator_fixes.

Two independent .408 defects, one lane:

MED-1  tools/comparator_discovery.py pools MIBiG KnownClusterBlast reference-cluster
       accessions (e.g. `BGC0001522.5`) into the genome comparator/fetch list. Their
       descriptions are METABOLITE names, so genus_species() mints bogus genera
       ("auroramycin", "coelichelin"), and fetch_<strain>_comparators.sh emits a dead
       `efetch -db nuccore -id BGC0001522.5` line (a MIBiG id is not a nuccore record).

MED-2  tools/cross_strain_denominator_audit.py hardwired the registry/BGC sheet names to
       a workbook TEMPLATE (A2_Strain_Registry / B1_BGC_Master). The cohort pipeline emits
       COHORT_MASTER.xlsx with sheets `strain_summary` / `bgc_inventory`, so the audit always
       fired "cannot establish cohort size" (exit 1) -- fail-SAFE but non-functional on real
       output.

Run against the tree under test (copy this file to the tree root; it imports tools/ from there):
    pytest test_409_mibig_comparator_fixes.py
Pristine .408 -> the MIBiG-split tests and the real-schema audit test FAIL. Patched -> all pass.
"""
import csv
import os
import sys

import openpyxl
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tree root
from tools import comparator_discovery as C  # noqa: E402
from tools import cross_strain_denominator_audit as D  # noqa: E402


# ============================================================ MED-1: comparator_discovery

def _mk_antismash(root):
    """A strain antiSMASH tree with two MIBiG KnownClusterBlast hits (BGC accessions, metabolite
    descriptions) and two ClusterBlast genome hits (NZ_ accessions, organism descriptions)."""
    kcb = os.path.join(root, "knownclusterblast"); os.makedirs(kcb)
    cb = os.path.join(root, "clusterblast"); os.makedirs(cb)
    with open(os.path.join(kcb, "RB68_region001.txt"), "w") as f:
        f.write("Significant hits: \n"
                "1. BGC0001522.5\tauroramycin biosynthetic gene cluster\n"
                "2. BGC0000325.5\tcoelichelin biosynthetic gene cluster\n"
                "Details:\n")
    with open(os.path.join(cb, "RB68_region001.txt"), "w") as f:
        f.write("Significant hits: \n"
                "1. NZ_CP012600.1\tStreptomyces coelicolor A3(2) chromosome\n"
                "2. NZ_WEGH01000001.1\tActinomadura macrotermitis strain RB68\n"
                "Details:\n")


def _run_comparator(tmp_path, monkeypatch):
    asdir = tmp_path / "as"; _mk_antismash(str(asdir))
    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv",
                        ["comparator_discovery.py", "--dir", str(asdir), "--strain", "RB68", "--out", str(out)])
    C.main()
    return out


def test_fetch_script_has_no_dead_mibig_efetch_lines(tmp_path, monkeypatch):
    out = _run_comparator(tmp_path, monkeypatch)
    fetch = (out / "fetch_RB68_comparators.sh").read_text()
    efetch_ids = [ln.split("-id", 1)[1].split()[0] for ln in fetch.splitlines() if "efetch" in ln and "-id" in ln]
    # Pristine .408: BGC0001522.5 / BGC0000325.5 appear as dead efetch lines (RED).
    assert not any(i.upper().startswith("BGC") for i in efetch_ids), efetch_ids
    # The genuine genome accessions are still fetched.
    assert "NZ_CP012600.1" in efetch_ids
    assert "NZ_WEGH01000001.1" in efetch_ids


def test_genera_rollup_has_no_metabolite_names(tmp_path, monkeypatch):
    out = _run_comparator(tmp_path, monkeypatch)
    genera = {r[0] for r in csv.reader((out / "RB68_comparator_genera.tsv").read_text().splitlines(), delimiter="\t")}
    # Pristine .408: metabolite names leak in as "genera" (RED).
    assert "auroramycin" not in genera
    assert "coelichelin" not in genera
    # Real genera survive.
    assert "Streptomyces" in genera
    assert "Actinomadura" in genera


def test_mibig_reference_clusters_split_into_own_table(tmp_path, monkeypatch):
    out = _run_comparator(tmp_path, monkeypatch)
    mib = out / "RB68_mibig_known_clusters.tsv"
    # Pristine .408 never writes this file (RED: FileNotFoundError).
    assert mib.exists(), "MIBiG known-cluster table not written"
    rows = list(csv.DictReader(mib.read_text().splitlines(), delimiter="\t"))
    accs = {r["mibig_accession"] for r in rows}
    assert accs == {"BGC0001522.5", "BGC0000325.5"}
    # The comparator table (genomes) must NOT contain the MIBiG accessions.
    comp_accs = {r["accession"] for r in
                 csv.DictReader((out / "RB68_comparators.tsv").read_text().splitlines(), delimiter="\t")}
    assert not any(a.upper().startswith("BGC") for a in comp_accs), comp_accs


# ============================================================ MED-2: cross_strain_denominator_audit

def _wb(path, sheets):
    """sheets: dict {name: list_of_rows}. First row of each is the header."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(list(r))
    wb.save(str(path))


def test_emitted_schema_audit_runs_and_passes(tmp_path):
    # Real COHORT_MASTER shape: strain_summary + bgc_inventory, no cross-strain findings sheet.
    p = tmp_path / "COHORT_MASTER.xlsx"
    _wb(p, {
        "strain_summary": [("strain", "taxonomy"), ("Actinomadura_RB68", "x"), ("Actinomadura_rifamycini", "y")],
        "bgc_inventory": [("strain", "BGC_ID")] + [(f"S{i}", f"BGC{i:03d}") for i in range(1, 6)],
        "class_by_strain": [("strain", "ectoine"), ("Actinomadura_RB68", 1)],
    })
    res = D.denominator_audit_result(str(p))
    # Pristine .408: registry sheet names not found -> "cannot establish cohort size" -> FAIL (RED).
    assert res["status"] == "PASS", res
    assert res["blocking_violation_count"] == 0
    # The generalized reader established cohort size from the emitted sheet.
    wb = openpyxl.load_workbook(str(p), read_only=True, data_only=True)
    assert D._registry_length(wb) == 2
    assert D._bgc_total(wb) == 5
    wb.close()


def test_emitted_schema_still_catches_stale_denominator(tmp_path):
    # The audit must still DO its job on the emitted registry: a stale cohort denominator on a
    # cross-strain sheet, with cohort size read from `strain_summary`, must FAIL.
    p = tmp_path / "master_stale.xlsx"
    _wb(p, {
        "strain_summary": [("strain",)] + [(f"S{i}",) for i in range(1, 45)],       # 44 strains
        "bgc_inventory": [("strain", "BGC_ID")] + [(f"S{i}", f"BGC{i:03d}") for i in range(1, 10)],
        "Cross_Strain_Findings": [("finding",), ("ectoine present 17/18",)],          # stale (was 18-cohort)
    })
    res = D.denominator_audit_result(str(p))
    # Pristine .408: n_reg=0 -> "cannot establish cohort size" (FAIL for the WRONG reason) (RED).
    assert res["status"] == "FAIL", res
    joined = " ".join(res["blocking_violations"])
    assert "17/18" in joined
    assert "cohort size is 44" in joined


def test_truly_empty_workbook_still_fails_closed(tmp_path):
    # Regression guard: neither registry schema present -> fail-closed, no false PASS (green both sides).
    p = tmp_path / "empty.xlsx"
    _wb(p, {"unrelated": [("a", "b"), (1, 2)]})
    res = D.denominator_audit_result(str(p))
    assert res["status"] == "FAIL"
    assert any("cannot establish cohort size" in v for v in res["blocking_violations"])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
