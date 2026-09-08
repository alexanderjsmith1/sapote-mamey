import csv
import json
from pathlib import Path

from mamey.activity_lead_genes import build_gene_anchor_report, run, select_gene_anchors


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _lead(package: Path, **overrides):
    row = {
        "strain": "TYPE-001",
        "exact_locus": "TYPE-001 / CONTIG_full_name / region001 / BGC007",
        "full_node_or_contig": "CONTIG_full_name",
        "region": "region001",
        "bgc_alias": "BGC007",
        "source_local_bgc_alias": "BGC002",
        "Products": "NRPS; T1PKS; lanthipeptide-class-i",
        "source_triage_board": str(package / "TYPE-001_4_triage_board.csv"),
    }
    row.update(overrides)
    return row


def _gene(tag: str, start: int, domains: str, role: str = "biosynthetic context"):
    return {
        "bgc_id": "BGC002", "locus_tag": tag, "contig": "CONTIG_full_name",
        "bgc_start": "100", "bgc_end": "9000", "cds_start": str(start),
        "cds_end": str(start + 900), "strand": "+", "aa_length": "300",
        "product_qualifier": "", "gene_function_inference": role,
        "sec_met_domains": domains, "source_gbk": "CONTIG_full_name.region001.gbk",
    }


def _fixture(tmp_path: Path, gene_rows: list[dict[str, object]]):
    package = tmp_path / "TYPE-001" / "package"
    package.mkdir(parents=True)
    (package / "TYPE-001_4_triage_board.csv").write_text("BGC_ID\nBGC002\n")
    _write_csv(package / "TYPE-001_gene_by_gene_all_bgcs.csv", gene_rows)
    leads = tmp_path / "PER_STRAIN_ACTIVITY_LEADS.csv"
    _write_csv(leads, [_lead(package)])
    return package, leads


def test_hybrid_selection_preserves_distinct_class_foundations(tmp_path):
    _, leads = _fixture(tmp_path, [
        _gene("core_nrps", 100, "AMP-binding; Condensation"),
        _gene("core_pks", 1200, "PKS_KS; PKS_AT"),
        _gene("lan_c", 2300, "LanC"),
        _gene("tailor", 3400, "methyltransferase"),
        _gene("transport", 4500, "ABC_transporter", "transport"),
        _gene("context", 5600, "DUF0000"),
    ])
    anchors, loci, holds, meta = build_gene_anchor_report(str(leads), top_n=5)
    assert not holds
    assert {row["locus_tag"] for row in anchors} >= {"core_nrps", "core_pks", "lan_c"}
    assert loci[0]["gene_logic_strength"] == "STRONG_GENE_LOGIC"
    assert loci[0]["supported_classes"] == "NRPS; PKS; RiPP"
    assert meta["gene_anchor_rows"] == 5


def test_thioesterase_alone_is_not_an_nrps_core():
    selected, summary = select_gene_anchors([
        _gene("te", 100, "Thioesterase"),
        _gene("context", 1200, "DUF0000"),
    ], "NRPS", top_n=2)
    assert "NRPS" not in {vote for row in selected for vote in row["_votes"]}
    assert summary["gene_logic_strength"] == "WEAK_ACCESSORY_ONLY"
    assert summary["unresolved_source_labels"] == ["NRPS"]


def test_fewer_than_five_genes_returns_only_governed_rows(tmp_path):
    _, leads = _fixture(tmp_path, [
        _gene("core_nrps", 100, "AMP-binding"),
        _gene("core_pks", 1200, "PKS_KS"),
    ])
    anchors, loci, holds, _ = build_gene_anchor_report(str(leads), top_n=5)
    assert not holds
    assert len(anchors) == 2
    assert loci[0]["governed_gene_count"] == 2
    assert loci[0]["anchor_count"] == 2


def test_complete_exact_locus_mismatch_fails_closed(tmp_path):
    package, leads = _fixture(tmp_path, [_gene("core_nrps", 100, "AMP-binding")])
    _write_csv(leads, [_lead(package, exact_locus="TYPE-001 / WRONG / region001 / BGC007")])
    anchors, loci, holds, _ = build_gene_anchor_report(str(leads))
    assert anchors == []
    assert loci == []
    assert holds[0]["state"] == "INCOMPLETE_OR_CONTRADICTORY_EXACT_LOCUS_NOT_ADMITTED"


def test_source_alias_or_region_transfer_is_refused(tmp_path):
    package, leads = _fixture(tmp_path, [_gene("core_nrps", 100, "AMP-binding")])
    _write_csv(leads, [_lead(package, source_local_bgc_alias="BGC999")])
    anchors, loci, holds, _ = build_gene_anchor_report(str(leads))
    assert anchors == [] and loci == []
    assert holds[0]["state"] == "PHYSICAL_GENE_ROSTER_NOT_BOUND"


def test_run_writes_machine_readable_outputs(tmp_path):
    _, leads = _fixture(tmp_path, [_gene("core_nrps", 100, "AMP-binding")])
    out = tmp_path / "out"
    meta = run(str(leads), str(out), top_n=5)
    assert meta["loci_with_gene_profiles"] == 1
    assert Path(meta["paths"]["anchors_csv"]).exists()
    payload = json.loads(Path(meta["paths"]["metadata_json"]).read_text())
    assert payload["claim_safety"].startswith("Class-level biosynthetic logic only")
