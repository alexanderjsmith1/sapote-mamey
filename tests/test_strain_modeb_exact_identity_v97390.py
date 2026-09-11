from __future__ import annotations

import csv
import json
from pathlib import Path

from mamey.strain_modeb import build_strain_sapote


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_strain_modeb_primary_surfaces_use_exact_four_part_identity(tmp_path):
    package = tmp_path / "TEST-01" / "package"
    package.mkdir(parents=True)
    manifest = {
        "strain_id": "TEST-01", "workflow_version": "1.9.test", "mode": "gold",
        "taxonomy": "Testomyces sp.", "source": "generic fixture",
        "assembly": {}, "bgc_counts": {"raw": 1, "assembly_tier": "A"},
        "bgcs": [{"bgc_id": "BGC001", "products": ["RiPP-like"]}],
        "split_pathway_candidates": [], "recommended_next_steps": [],
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (package / "TEST-01_1_intake.json").write_text(json.dumps({"release": "PRIVATE"}), encoding="utf-8")
    row = {
        "BGC_ID": "BGC001", "Node_ID": "NODE_1_length_12345_cov_20.5",
        "antiSMASH_Region": "region001", "Products": "RiPP-like",
        "Corrected_rank": "1", "Lead_tier_auto": "High", "Boundary": "Interior",
        "Arch_Capacity": "1", "KCB_top": "none", "AB_auto": "0", "AF_auto": "0",
    }
    _write_csv(package / "TEST-01_4_triage_board.csv", [row])
    markdown, _meta = build_strain_sapote(package)
    identity = "TEST-01 / NODE_1_length_12345_cov_20.5 / region001 / BGC001"
    assert identity in markdown
    assert f"**{identity}**" in markdown
    assert "Lab Quest 🧫" not in markdown
