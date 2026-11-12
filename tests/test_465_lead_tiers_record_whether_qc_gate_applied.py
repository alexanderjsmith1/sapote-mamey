"""Lead tiers say whether the assembly-QC gate applied.

build_lead_tiers.py holds FLAG strains only when <banked-dir>/assembly_qc.json exists. Without it no
strain was held and nothing said so: a strain with no QC record could be proposed Class A.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "build_lead_tiers.py"


def _bank(tmp_path, qc=None):
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "bgc_data.json").write_text(json.dumps({"strains": {}, "bgcs": []}), encoding="utf-8")
    (bank / "tfbs_coupling.json").write_text(json.dumps({"S1": {"BGC001": ["SARP"]}}), encoding="utf-8")
    with open(bank / "modeb_verdicts.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["strain", "bgc", "status", "modeb_class", "note"])
        w.writeheader()
        w.writerow({"strain": "S1", "bgc": "BGC001", "status": "CONFIRM", "modeb_class": "NRPS", "note": ""})
    if qc is not None:
        (bank / "assembly_qc.json").write_text(json.dumps(qc), encoding="utf-8")
    return bank


def _run(bank, out):
    return subprocess.run([sys.executable, str(TOOL), "--banked-dir", str(bank), "--out", str(out)],
                          capture_output=True, text=True, cwd=str(ROOT), timeout=120)


def _rows(out):
    with open(out, newline="") as fh:
        return list(csv.DictReader(fh))


def test_without_qc_file_rows_say_not_recorded(tmp_path):
    out = tmp_path / "tiers.csv"
    r = _run(_bank(tmp_path), out)
    assert r.returncode == 0, r.stderr
    rows = _rows(out)
    assert rows and all(x["assembly_qc"] == "not recorded" for x in rows)
    assert "assembly_qc.json not found" in r.stdout


def test_with_qc_file_rows_say_held_or_not_flagged(tmp_path):
    out = tmp_path / "tiers.csv"
    r = _run(_bank(tmp_path, {"held_qc": ["S9"]}), out)
    assert r.returncode == 0, r.stderr
    assert {x["assembly_qc"] for x in _rows(out)} == {"not flagged"}
    assert "assembly_qc.json not found" not in r.stdout
    out2 = tmp_path / "tiers2.csv"
    (tmp_path / "bank" / "assembly_qc.json").write_text(json.dumps({"held_qc": ["S1"]}), encoding="utf-8")
    assert _run(tmp_path / "bank", out2).returncode == 0
    assert {x["assembly_qc"] for x in _rows(out2)} == {"held"}
