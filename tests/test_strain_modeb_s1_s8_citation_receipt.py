from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from mamey.strain_modeb import (
    StrainCitationReceiptError,
    build_strain_citation_receipt,
    build_strain_sapote,
)


def _package(tmp_path: Path) -> Path:
    strain = "TEST-01"
    package = tmp_path / strain / "package"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps({
        "strain_id": strain, "workflow_version": "1.9.test", "mode": "gold",
        "taxonomy": "Testomyces sp.", "source": "synthetic",
        "assembly": {}, "bgc_counts": {"raw": 1, "assembly_tier": "A"},
        "bgcs": [{"bgc_id": "BGC001", "products": ["RiPP-like"]}],
        "split_pathway_candidates": [], "recommended_next_steps": [],
    }), encoding="utf-8")
    (package / f"{strain}_1_intake.json").write_text('{"release":"PRIVATE"}', encoding="utf-8")
    row = {
        "BGC_ID": "BGC001", "Node_ID": "NODE_1_length_12345_cov_20.5",
        "antiSMASH_Region": "region001", "Products": "RiPP-like", "Corrected_rank": "1",
        "Lead_tier_auto": "High", "Boundary": "Interior", "Arch_Capacity": "1",
        "KCB_top": "none", "AB_auto": "0", "AF_auto": "0",
    }
    with (package / f"{strain}_4_triage_board.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader(); writer.writerow(row)
    with (package / f"{strain}_2b_bgc_crosswalk.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["bgc_id", "node_id", "antismash_region"])
        writer.writeheader(); writer.writerow({"bgc_id": "BGC001", "node_id": row["Node_ID"], "antismash_region": "region001"})
    return package


def test_s1_s8_receipt_binds_every_node_to_package_crosswalk(tmp_path: Path) -> None:
    package = _package(tmp_path)
    markdown, _ = build_strain_sapote(package)
    receipt = build_strain_citation_receipt(markdown, package)
    assert receipt["status"] == "PASS"
    assert [row["section"] for row in receipt["sections"]] == [f"S{i}" for i in range(1, 9)]
    assert receipt["citation_count"] >= 2
    assert all(row["state"] in {"CROSSWALK_BOUND", "NO_NODE_CITATIONS"} for row in receipt["sections"])
    assert {citation["node_id"] for row in receipt["sections"] for citation in row["citations"]} == {
        "NODE_1_length_12345_cov_20.5"
    }


def test_s1_s8_receipt_refuses_node_not_matching_crosswalk(tmp_path: Path) -> None:
    package = _package(tmp_path)
    markdown, _ = build_strain_sapote(package)
    changed = markdown.replace("NODE_1_length_12345_cov_20.5", "NODE_9_length_99999_cov_9.9", 1)
    with pytest.raises(StrainCitationReceiptError, match="CROSSWALK_MISMATCH"):
        build_strain_citation_receipt(changed, package)

    bare = markdown.replace("## S6", "Unbound node note: NODE_1_length_12345_cov_20.5\n\n## S6")
    with pytest.raises(StrainCitationReceiptError, match="INCOMPLETE_IDENTITY"):
        build_strain_citation_receipt(bare, package)


def test_native_crosswalk_full_contig_receipt(tmp_path):
    package = _package(tmp_path)
    path = package / 'TEST-01_2b_bgc_crosswalk.csv'
    row = {'bgc_id':'BGC001', 'contig':'NODE_1_length_12345_cov_20.5', 'node_id':'NODE_1_length_12345_cov_20', 'antismash_region':'region001'}
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
    markdown, _ = build_strain_sapote(package)
    assert build_strain_citation_receipt(markdown, package)['status']=='PASS'
    # Shared normalized prefix must not admit a different physical contig.
    wrong=markdown.replace('NODE_1_length_12345_cov_20.5','NODE_1_length_12345_cov_20.6')
    with pytest.raises(StrainCitationReceiptError):build_strain_citation_receipt(wrong,package)
    row['node_id']='NODE_2'
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
    with pytest.raises(StrainCitationReceiptError):build_strain_citation_receipt(markdown,package)
