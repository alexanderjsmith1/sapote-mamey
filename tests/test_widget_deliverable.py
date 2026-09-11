"""Regression tests for the post-seal interactive widget deliverable."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from mamey.cli import build_parser
from mamey.widget_deliverable import CLAIM_CEILING, render_widget_deliverable


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


@pytest.fixture()
def package(tmp_path: Path) -> Path:
    pkg = tmp_path / "AS-TEST" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({
        "strain_id": "AS-TEST", "workflow_version": "Mamey v1.9.119",
        "package_status": "MAMEY_COMPLETE", "claim_safety_status": "PASS",
    }), encoding="utf-8")
    (pkg / "AS-TEST_1_intake.json").write_text(json.dumps({
        "strain_id": "AS-TEST", "taxonomy": "Streptomyces sp.",
        "source": "test", "release": "PUBLIC", "antismash_version": "8.0.4",
    }), encoding="utf-8")
    _write_csv(pkg / "AS-TEST_2_inventory.csv", [{
        "BGC_ID": "BGC001", "Contig": "NODE_1", "Region": "region001", "Products": "NRPS", "Boundary": "Interior",
        "Arch": "C", "Length_kb": "42", "KCB_top": "example comparator",
        "KCB_score": "123", "KCB_proteins": "4", "CCTT_triggers": "T43-HAL",
        "safe_claim": "NRPS-like capacity",
    }])
    inventory_path = pkg / "AS-TEST_2_inventory.csv"
    with inventory_path.open() as handle:
        inventory_rows = list(csv.DictReader(handle))
    second = dict(inventory_rows[0], BGC_ID="BGC002", Contig="NODE_2", Region="region001")
    _write_csv(inventory_path, inventory_rows + [second])
    _write_csv(pkg / "AS-TEST_4_triage_board.csv", [{
        "Rank": "1", "BGC_ID": "BGC001", "Products": "NRPS",
        "Boundary": "Interior", "Arch": "C", "AB_auto": "55",
        "AF_auto": "31", "Novelty_auto": "44", "Lead_tier_auto": "High",
        "KCB_top": "example comparator", "KCB_score": "123",
        "CCTT_triggers": "T43-HAL", "RGGMCI_support": "HIGH",
        "Standing_rule": "", "Misanchor_flag": "",
    }])
    _write_csv(pkg / "AS-TEST_gene_by_gene_all_bgcs.csv", [{
        "bgc_id": "BGC001", "rank": "1", "locus_tag": "ctg1_31",
        "contig": "NODE_1", "source_gbk": "NODE_1.region001.gbk",
        "bgc_start": "1000", "bgc_end": "43000", "cds_start": "15000", "cds_end": "16109",
        "strand": "+", "aa_length": "369", "bgc_products": "oligosaccharide; saccharide",
        "boundary_flag": "Interior", "gene_function_inference": "biosynthetic context",
        "product_qualifier": "DegT/DnrJ/EryC1/StrS aminotransferase",
        "sec_met_domains": "DegT_DnrJ_EryC1",
    }])
    _write_csv(pkg / "AS-TEST_3_mibig_per_gene.csv", [{
        "bgc_id": "BGC001", "query_gene": "ctg1_31", "subject_gene": "KijD2",
        "mibig_accession": "BGC0000082", "mibig_compound": "kijanimicin",
        "reference_type": "PKS", "pct_identity": "69", "pct_coverage": "101.1",
        "pct_coverage_interpretation": "100", "coverage_qc_flag": "SOURCE_GT100_CAPPED_FOR_INTERPRETATION",
        "evalue": "4.81e-182", "reference_rank": "4",
    }])
    _write_csv(pkg / "AS-TEST_4A2_ClusterBlast_per_gene.csv", [{
        "bgc_id": "BGC001", "query_gene": "ctg1_31", "subject_gene": "REF_31",
        "pct_identity": "85", "pct_coverage": "100", "evalue": "1e-220",
        "reference": "NZ_TEST", "reference_source": "Streptomyces test chromosome",
        "reference_rank": "1",
    }])
    nr = pkg / "blastp_nr"; nr.mkdir()
    _write_csv(nr / "BGC001_top10.csv", [{
        "strain": "AS-TEST", "bgc_id": "BGC001", "gene": "ctg1_31",
        "aa_length": "369", "hit_rank": "1", "subject_acc": "WP_TEST",
        "subject_organism": "Streptomyces test", "subject_def": "DegT/DnrJ family aminotransferase",
        "pct_identity": "87", "pct_positives": "93", "query_coverage": "99",
        "evalue": "0", "bitscore": "675",
    }])
    swiss = pkg / "blastp_swissprot"; swiss.mkdir()
    _write_csv(swiss / "BGC001_top10.csv", [{
        "strain": "AS-TEST", "bgc_id": "BGC001", "gene": "ctg1_31",
        "aa_length": "369", "hit_rank": "1", "subject_acc": "Q9F837",
        "subject_organism": "Micromonospora megalomicea", "subject_def": "dTDP-amino-deoxysugar transaminase",
        "pct_identity": "65.8", "pct_positives": "78.9", "query_coverage": "100",
        "evalue": "1.36e-178", "bitscore": "503",
    }])
    online = pkg / "blastp_online"; online.mkdir()
    _write_csv(online / "BGC001_online_blastp.csv", [{
        "locus_tag": "ctg1_31", "aa_length": "369", "blastp_top_def": "legacy row without strain/BGC",
        "blastp_accession": "LEGACY", "blastp_organism": "unknown", "pct_identity": "99",
        "query_coverage": "100", "evalue": "0", "bitscore": "999", "channel": "nr",
    }])
    _write_csv(pkg / "AS-TEST_4A_RGGMCI_ranked_pairs.csv", [{
        "pair": "BGC001+BGC002", "bgc_a": "BGC001", "bgc_b": "BGC002",
        "rggmci_score": "7.5", "rggmci_confidence": "HIGH",
        "reference_support_count": "3", "shared_reference_count": "2",
        "geometry_class": "cross-contig", "geometry_support_count": "1",
        "functional_rescue_class": "candidate", "tiling_verdict": "review",
        "flags": "", "best_sources": "KCB", "interpretation_guard": "not physical linkage",
    }])
    gold = pkg / "gold_figures"; gold.mkdir()
    _write_csv(gold / "F01_AS-TEST_perBGC_domain_heatmap_data.csv", [{
        "bgc_id": "BGC001", "PKS_KS": "0", "PKS_AT": "0", "PKS_KR": "0",
        "PKS_DH": "0", "NRPS_C": "2", "NRPS_A": "2", "NRPS_T_PCP": "2",
        "TE_release": "1",
    }])
    _write_csv(pkg / "AS-TEST_7_missing_data_worklist.csv", [{
        "priority": "P1", "status": "OPEN", "item": "resolve accession",
    }])
    (pkg / "gate_validation.json").write_text(json.dumps({
        "status": "MAMEY_COMPLETE", "checksum_integrity": "PASS",
        "gold_completeness": "JUDGMENT_PENDING",
    }), encoding="utf-8")
    (pkg / "claim_safety_status.json").write_text(json.dumps({"claim_safety_status": "PASS"}), encoding="utf-8")
    (pkg / "package_status.json").write_text(json.dumps({"package_status": "MAMEY_COMPLETE"}), encoding="utf-8")
    return pkg


def _tree_fingerprint(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(path.relative_to(root).as_posix().encode()); h.update(path.read_bytes())
    return h.hexdigest()


def test_directory_render_is_sibling_and_does_not_mutate_source(package: Path, tmp_path: Path):
    before = _tree_fingerprint(package)
    out = tmp_path / "widgets"
    result = render_widget_deliverable(package, out)
    assert result["status"] == "PASS"
    assert _tree_fingerprint(package) == before
    assert result["counts"] == {"bgcs": 1, "gene_rows": 1, "domain_rows": 1, "rggmci_pairs": 1, "missing_worklist_rows": 1, "widgets": 7}
    for name in ["OPEN_WIDGETS.html", "priority.html", "domains.html", "evidence.html",
                 "genes.html", "gene.html",
                 "rggmci.html", "completeness.html", "widget_data.json",
                 "PUBLICATION_HANDOFF.md", "publication_metadata.json",
                 "WIDGET_MANIFEST.json", "SHA256SUMS.txt"]:
        assert (out / name).is_file(), name


def test_complete_package_zip_is_read_without_extraction(package: Path, tmp_path: Path):
    zpath = tmp_path / "AS-TEST_Complete_Package.zip"
    with ZipFile(zpath, "w", ZIP_DEFLATED) as zf:
        for path in sorted(p for p in package.rglob("*") if p.is_file()):
            zf.write(path, "package/" + path.relative_to(package).as_posix())
    before = hashlib.sha256(zpath.read_bytes()).hexdigest()
    result = render_widget_deliverable(zpath, tmp_path / "zip_widgets")
    assert result["source"]["kind"] == "zip"
    assert result["counts"]["bgcs"] == 1
    assert hashlib.sha256(zpath.read_bytes()).hexdigest() == before


def test_pages_are_self_contained_and_claim_safe(package: Path, tmp_path: Path):
    out = tmp_path / "widgets"
    render_widget_deliverable(package, out)
    priority = (out / "priority.html").read_text(encoding="utf-8")
    rggmci = (out / "rggmci.html").read_text(encoding="utf-8")
    assert "window.WIDGET_DATA" in priority
    assert 'src="http://' not in priority and 'src="https://' not in priority
    assert "routing priors" in priority
    assert "not proof" in rggmci.lower() and "physical" in rggmci.lower()
    assert CLAIM_CEILING in json.loads((out / "WIDGET_MANIFEST.json").read_text())["claim_ceiling"]
    data = json.loads((out / "widget_data.json").read_text())
    assert data["meta"]["source_release"] == "PUBLIC"
    assert data["meta"]["release"] == "PRIVATE"
    assert data["meta"]["release_guard"] == "PRIVATE_PREFIX_OVERRIDE"
    assert "post-seal widget deliverable · PRIVATE" in priority


def test_missing_domain_layer_stays_empty_not_zero_filled(package: Path, tmp_path: Path):
    (package / "gold_figures" / "F01_AS-TEST_perBGC_domain_heatmap_data.csv").unlink()
    out = tmp_path / "widgets"
    result = render_widget_deliverable(package, out)
    assert result["counts"]["domain_rows"] == 0
    data = json.loads((out / "widget_data.json").read_text())
    assert data["domains"] == []


def test_gene_page_joins_exact_current_evidence_and_holds_legacy_online(package: Path, tmp_path: Path):
    out = tmp_path / "widgets"
    result = render_widget_deliverable(package, out)
    data = json.loads((out / "widget_data.json").read_text())
    assert result["counts"]["gene_rows"] == 1
    gene = data["genes"][0]
    assert (gene["strain"], gene["bgc_id"], gene["locus_tag"], gene["aa_length"]) == (
        "AS-TEST", "BGC001", "ctg1_31", 369,
    )
    assert gene["products"] == "oligosaccharide; saccharide"
    assert (gene["bgc_start"], gene["bgc_end"], gene["cds_start"], gene["cds_end"]) == (
        1000, 43000, 15000, 16109,
    )
    assert gene["reaction_family"] == "PLP-dependent nucleotide-deoxysugar aminotransferase"
    assert "amino group" in gene["reaction_hint"] and "HOLD" in gene["reaction_hint"]
    assert gene["mibig_hits"][0]["mibig_compound"] == "kijanimicin"
    assert gene["clusterblast_hits"][0]["reference_source"] == "Streptomyces test chromosome"
    assert set(gene["blastp"]) == {"nr", "swissprot"}
    assert gene["blastp_channel_status"]["online"].startswith("HOLD")
    receipt = data["gene_evidence_receipt"]["channels"]["online"]
    assert receipt["rows_admitted"] == 0 and receipt["rows_quarantined_or_held"] == 1
    page = (out / "genes.html").read_text(encoding="utf-8")
    assert "MIBiG/KnownCluster compound anchors" in page
    assert "BLASTP channels kept separate" in page
    assert 'id="geneMap"' in page and 'id="geneSimilarity"' in page
    assert "Marker area scales with protein length" in page
    assert "adjacent labels show the selected locus" in page
    assert 'id="themeToggle"' in page and "mamey-widget-theme" in page
    assert ':root[data-theme="dark"]' in page
    assert 'id="geneMap" viewBox="0 0 1120 220"' in page
    assert "svgText(geneMap,R,46" in page
    assert "window.addEventListener('mamey-theme-change',draw)" in page
    assert 'src="http://' not in page and 'src="https://' not in page


def test_output_inside_package_is_rejected(package: Path):
    with pytest.raises(ValueError, match="outside the sealed package"):
        render_widget_deliverable(package, package / "widgets")


def test_outputs_are_deterministic_and_checksum_manifest_verifies(package: Path, tmp_path: Path):
    out_a, out_b = tmp_path / "widgets_a", tmp_path / "widgets_b"
    render_widget_deliverable(package, out_a)
    render_widget_deliverable(package, out_b)
    files_a = {p.name: p.read_bytes() for p in out_a.iterdir() if p.is_file()}
    files_b = {p.name: p.read_bytes() for p in out_b.iterdir() if p.is_file()}
    assert files_a == files_b
    for line in (out_a / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((out_a / name).read_bytes()).hexdigest() == digest


def test_cli_parser_registers_render_widgets():
    args = build_parser().parse_args(["render-widgets", "--package", "x.zip", "--outdir", "widgets"])
    assert args.command == "render-widgets"
    assert args.package == "x.zip"


# --- v9.7.347 NC-037: locate() must match only at a path/basename boundary ---
def test_nc037_locate_rejects_non_boundary_suffix_collision(tmp_path):
    from mamey.widget_deliverable import PackageSource
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_text("{}", encoding="utf-8")
    (pkg / "AS-1_4_triage_board.csv").write_text("x", encoding="utf-8")
    (pkg / "decoy_scoreboard.csv").write_text("y", encoding="utf-8")
    src = PackageSource(pkg)
    try:
        # positive: full basename + strain-prefixed "_<token>" resolve correctly
        assert src.locate("manifest.json") == "manifest.json"
        assert src.locate("_4_triage_board.csv") == "AS-1_4_triage_board.csv"
        assert src.locate("decoy_scoreboard.csv") == "decoy_scoreboard.csv"
        # NC-037: a bare token that only *ends* other names must NOT resolve (old endswith() bug):
        # "board.csv" used to match both AS-1_4_triage_board.csv and decoy_scoreboard.csv.
        assert src.locate("board.csv") is None
    finally:
        src.close()
def test_widget_csv_export_uses_shared_string_only_leader_policy():
    """Widget CSV remains a presentation layer while sharing Python's leaders AND its
    sign-leader exemption (v9.7.410 CLAUDE_410_csv_writer_coverage: lone strand signs and plain
    ASCII signed numbers pass through; both constants are injected from mamey.csv_safety)."""
    from mamey.csv_safety import CSV_LEADER_CLASS_JS, CSV_NUMERIC_TOKEN, csv_safe_cell
    from mamey.widget_deliverable import _COMMON_JS

    assert f"const CSV_LEADER=/^[{CSV_LEADER_CLASS_JS}]/,CSV_NUMERIC=/{CSV_NUMERIC_TOKEN}/;" in _COMMON_JS
    assert "csvSafeCell(String(v??''))" in _COMMON_JS
    assert csv_safe_cell(-1.5) == -1.5
    assert csv_safe_cell("-1.5") == "-1.5"
    assert csv_safe_cell("-") == "-" and csv_safe_cell("+") == "+"
    assert csv_safe_cell("-1.5+SUM(1)") == "'-1.5+SUM(1)"
    assert csv_safe_cell("-١") == "'-١"  # non-ASCII digit is NOT a numeric token (JS \\d parity)
    assert csv_safe_cell("\t=1") == "'\t=1"
    assert csv_safe_cell("\xa0=1") == "\xa0=1"

