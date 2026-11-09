# Synthetic regression inputs only.
"""build_lead_tiers fails closed on a malformed QC hold set and on an unreadable label table."""
from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "build_lead_tiers.py"


def _bank(tmp_path, qc):
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "bgc_data.json").write_text(json.dumps({"strains": {}, "bgcs": [
        {"sid": "STRAIN_X", "bgc_id": "BGC001", "closest_kcb_product": "", "edge_status": "Interior",
         "length_kb": 40}]}), encoding="utf-8")
    (bank / "tfbs_coupling.json").write_text("{}", encoding="utf-8")
    with (bank / "modeb_verdicts.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=["strain", "bgc", "status", "modeb_class", "note"])
        w.writeheader()
        w.writerow({"strain": "STRAIN_X", "bgc": "BGC001", "status": "CONFIRM",
                    "modeb_class": "NRPS", "note": ""})
    if qc is not None:
        (bank / "assembly_qc.json").write_text(json.dumps(qc), encoding="utf-8")
    return bank


def _run(bank, out):
    return subprocess.run([sys.executable, str(TOOL), "--banked-dir", str(bank), "--out", str(out)],
                          cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120)


def test_valid_hold_list_holds_the_strain(tmp_path):
    out = tmp_path / "recall.csv"
    r = _run(_bank(tmp_path, {"held_qc": ["STRAIN_X"]}), out)
    assert r.returncode == 0, r.stderr
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert rows[0]["proposed_tier"] == "HOLD-QC"


@pytest.mark.parametrize("qc", [{}, {"held_qc": "STRAIN_X"}, {"held_qc": [""]}, ["STRAIN_X"]])
def test_malformed_hold_set_stops_the_run(tmp_path, qc):
    out = tmp_path / "recall.csv"
    r = _run(_bank(tmp_path, qc), out)
    assert r.returncode != 0
    assert "assembly_qc.json" in (r.stderr + r.stdout)
    assert not out.exists()


def _load_module():
    sys.path.insert(0, str(TOOL.parent))
    spec = importlib.util.spec_from_file_location("_blt_under_test", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_unreadable_axis_table_is_an_error(monkeypatch):
    mod = _load_module()
    mod._AXIS_TABLE = None

    def boom(*a, **k):
        raise OSError("missing")

    monkeypatch.setattr(mod, "_read_json", boom)
    with pytest.raises(SystemExit, match="activity-label table"):
        mod.axis("NRPS", "", "")


def test_empty_axis_table_is_an_error(monkeypatch):
    mod = _load_module()
    mod._AXIS_TABLE = None
    monkeypatch.setattr(mod, "_read_json", lambda *a, **k: {"axes_in_priority_order": []})
    with pytest.raises(SystemExit, match="axes_in_priority_order"):
        mod.axis("NRPS", "", "")


def test_shipped_axis_table_still_loads():
    mod = _load_module()
    mod._AXIS_TABLE = None
    assert isinstance(mod.axis("polyene", "", ""), str)
