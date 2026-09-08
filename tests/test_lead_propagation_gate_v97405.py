"""v9.7.405 — lead-propagation gate: a triage-board lead must reach every lead-listing surface."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from mamey.lead_propagation import LEAD_TIERS, audit_package, write_receipt

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "lead_propagation_gate.py"


def _package(tmp_path: Path, *, leads=("AS-XXX_BGC001", "AS-XXX_BGC002"), drop_from=()):
    pkg = tmp_path / "pkg"; pkg.mkdir()
    rows = [{"Rank": "1", "BGC_ID": leads[0], "Lead_tier_auto": "Exceptional"},
            {"Rank": "2", "BGC_ID": leads[1], "Lead_tier_auto": "High"},
            {"Rank": "3", "BGC_ID": "AS-XXX_BGC009", "Lead_tier_auto": "Inventory"}]
    with (pkg / "AS-XXX_4_triage_board.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["Rank", "BGC_ID", "Lead_tier_auto"]); w.writeheader(); w.writerows(rows)
    surfaces = {"manifest.json": lambda ids: json.dumps({"bgcs": ids}),
                "AS-XXX_2_inventory.csv": lambda ids: "BGC_ID\n" + "\n".join(ids),
                "AS-XXX_compiled_report.md": lambda ids: "# report\n" + "\n".join(f"- {i}" for i in ids),
                "OPEN_ME_FIRST.html": lambda ids: "<ul>" + "".join(f"<li>{i}</li>" for i in ids) + "</ul>"}
    for name, render in surfaces.items():
        ids = [l for l in leads if not (name in drop_from and l == leads[1])]
        (pkg / name).write_text(render(ids), encoding="utf-8")
    return pkg


def test_all_leads_propagated_passes(tmp_path):
    r = audit_package(_package(tmp_path))
    assert r["status"] == "PASS" and r["lead_count"] == 2 and r["failed_count"] == 0
    # the Inventory row is NOT a lead and is not audited
    assert {l["bgc_id"] for l in r["leads"]} == {"AS-XXX_BGC001", "AS-XXX_BGC002"}
    assert LEAD_TIERS == ("Exceptional", "High")


def test_lead_missing_from_a_surface_fails_and_names_it(tmp_path):
    r = audit_package(_package(tmp_path, drop_from=("AS-XXX_compiled_report.md", "OPEN_ME_FIRST.html")))
    assert r["status"] == "FAIL" and r["failed_count"] == 1
    bad = [l for l in r["leads"] if l["gate_status"] == "FAIL"][0]
    assert bad["bgc_id"] == "AS-XXX_BGC002"
    assert set(bad["missing_destinations"]) == {"compiled_report", "open_me_first"}
    assert "manifest" in bad["present_destinations"]


def test_missing_required_surface_fails_even_when_leads_agree(tmp_path):
    pkg = _package(tmp_path); (pkg / "manifest.json").unlink()
    r = audit_package(pkg)
    assert r["status"] == "FAIL" and r["missing_required_surfaces"] == ["manifest"]


def test_no_board_is_typed_not_a_crash(tmp_path):
    empty = tmp_path / "e"; empty.mkdir()
    assert audit_package(empty)["status"] == "NO_BOARD"


def test_receipt_and_front_door_exit_codes(tmp_path):
    pkg = _package(tmp_path, drop_from=("AS-XXX_compiled_report.md",))
    out = write_receipt(pkg, audit_package(pkg)); assert out.name == "lead_propagation.json"
    env = {"PYTHONDONTWRITEBYTECODE": "1"}
    ok = subprocess.run([sys.executable, str(TOOL), str(pkg)], capture_output=True, text=True, env=env)
    assert ok.returncode == 0 and json.loads(ok.stdout)["status"] == "FAIL"
    strict = subprocess.run([sys.executable, str(TOOL), str(pkg), "--strict"], capture_output=True, text=True, env=env)
    assert strict.returncode == 2
    nob = subprocess.run([sys.executable, str(TOOL), str(tmp_path)], capture_output=True, text=True, env=env)
    assert nob.returncode == 3 and json.loads(nob.stdout)["status"] == "NO_BOARD"


def test_inventory_edge_fragment_is_audited_even_when_not_a_lead(tmp_path):
    pkg = _package(tmp_path)
    inventory = pkg / "AS-XXX_2_inventory.csv"
    with inventory.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "BGC_ID", "Node_ID", "antiSMASH_Region", "Boundary",
        ])
        writer.writeheader()
        writer.writerows([
            {"BGC_ID": "AS-XXX_BGC001", "Node_ID": "NODE_1", "antiSMASH_Region": "region001", "Boundary": "Interior"},
            {"BGC_ID": "AS-XXX_BGC009", "Node_ID": "NODE_9", "antiSMASH_Region": "region009", "Boundary": "Edge"},
        ])
    # The inventory-tier fragment is intentionally absent from the manifest.
    result = audit_package(pkg)
    assert result["status"] == "FAIL"
    assert result["fragment_count"] == 1 and result["fragment_failed_count"] == 1
    assert result["fragments"][0]["full_identity"] == (
        "AS-XXX / NODE_9 / region009 / AS-XXX_BGC009"
    )
    assert result["fragments"][0]["missing_destinations"] == ["manifest"]


def test_edge_fragment_with_incomplete_identity_fails_closed(tmp_path):
    pkg = _package(tmp_path)
    inventory = pkg / "AS-XXX_2_inventory.csv"
    inventory.write_text("BGC_ID,Boundary\nAS-XXX_BGC009,Edge\n", encoding="utf-8")
    result = audit_package(pkg)
    assert result["status"] == "FAIL"
    assert result["fragment_identity_holds"] == [
        {"kind": "FRAGMENT_EXACT_IDENTITY_INCOMPLETE", "inventory_row": "2"}
    ]
