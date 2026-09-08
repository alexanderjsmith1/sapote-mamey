"""v9.7.405 — BGC alias history across re-runs: locus-overlap reconciliation, ids never renamed."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from mamey.bgc_alias_history import load_inventory, reconcile

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "bgc_alias_history.py"
HDR = ["BGC_ID", "Node_ID", "Start", "End", "Products"]


def _pkg(tmp_path, name, rows, strain="SYN-001"):
    d = tmp_path / name; d.mkdir()
    with (d / f"{strain}_2_inventory.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HDR); w.writeheader(); w.writerows(rows)
    return d


PRIOR = [{"BGC_ID": "BGC013", "Node_ID": "NODE_7", "Start": 1000, "End": 45000, "Products": "T1PKS"},
         {"BGC_ID": "BGC022", "Node_ID": "NODE_9", "Start": 100, "End": 8000, "Products": "terpene"},
         {"BGC_ID": "BGC001", "Node_ID": "NODE_1", "Start": 500, "End": 20500, "Products": "NRPS"}]
CURRENT = [{"BGC_ID": "BGC001", "Node_ID": "NODE_1", "Start": 500, "End": 20500, "Products": "NRPS"},
           {"BGC_ID": "BGC034", "Node_ID": "NODE_7", "Start": 1200, "End": 46000, "Products": "T1PKS"},
           {"BGC_ID": "BGC041", "Node_ID": "NODE_30", "Start": 10, "End": 9000, "Products": "RiPP"}]


def test_renumbered_same_and_new_are_typed(tmp_path):
    _, p = load_inventory(_pkg(tmp_path, "old", PRIOR)); _, c = load_inventory(_pkg(tmp_path, "new", CURRENT))
    h = reconcile(p, c)
    assert h["aliases"]["BGC034"]["match"] == "RENUMBERED" and h["aliases"]["BGC034"]["legacy_ids"] == ["BGC013"]
    assert h["aliases"]["BGC001"]["match"] == "SAME" and h["aliases"]["BGC001"]["legacy_ids"] == []
    assert h["aliases"]["BGC041"]["match"] == "NEW_OR_UNPLACED"
    assert h["renumbered"] == ["BGC034"] and h["unmatched_prior"] == ["BGC022"] and h["unmatched_current"] == ["BGC041"]
    # ids are NEVER renamed: every current id is present as a key exactly once
    assert sorted(h["aliases"]) == ["BGC001", "BGC034", "BGC041"]


def test_min_overlap_governs_matching(tmp_path):
    _, p = load_inventory(_pkg(tmp_path, "old", PRIOR)); _, c = load_inventory(_pkg(tmp_path, "new", CURRENT))
    assert reconcile(p, c, min_overlap=0.999)["aliases"]["BGC034"]["match"] == "NEW_OR_UNPLACED"


def test_front_door_refuses_strain_mismatch_and_writes_receipt(tmp_path):
    old = _pkg(tmp_path, "old", PRIOR); new = _pkg(tmp_path, "new", CURRENT); other = _pkg(tmp_path, "x", PRIOR, strain="SYN-002")
    env = {"PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run([sys.executable, str(TOOL), "--prior", str(old), "--current", str(other)], capture_output=True, text=True, env=env)
    assert r.returncode == 2 and json.loads(r.stderr)["error_code"] == "STRAIN_MISMATCH" and r.stdout == ""
    r = subprocess.run([sys.executable, str(TOOL), "--prior", str(old), "--current", str(new), "--write"], capture_output=True, text=True, env=env)
    assert r.returncode == 0
    out = json.loads(r.stdout); assert out["strain"] == "SYN-001" and out["renumbered"] == ["BGC034"]
    assert json.loads((new / "bgc_alias_history.json").read_text())["aliases"]["BGC034"]["legacy_ids"] == ["BGC013"]
