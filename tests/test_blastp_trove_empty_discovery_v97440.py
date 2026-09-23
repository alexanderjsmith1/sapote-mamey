"""No discovered source must not claim an immutable evidence-receipt slot."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from mamey.blastp_ingest import ingest_blastp_trove


def package(tmp_path):
    root = tmp_path / "package"
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps({"strain_id": "REF-TEST"}))
    locus = {"strain": "REF-TEST", "contig": "synthetic_contig", "region": "region001",
             "bgc_id": "BGC001", "locus_tag": "gene_1", "length_aa": "100"}
    with (root / "REF-TEST_cds_table.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(locus))
        writer.writeheader()
        writer.writerow(locus)
    record = {"bgc_id": "BGC001", "contig": "synthetic_contig", "region": "region001",
              "cds": [{"locus_tag": "gene_1", "aa_length": 100}]}
    (root / "REF-TEST_gene_context.jsonl").write_text(json.dumps(record) + "\n")
    return root


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def source(trove, *, rows=True):
    folder = trove / "REF-TEST" / "BGC001"
    folder.mkdir(parents=True)
    path = folder / "BGC001_top_hit_per_gene.csv"
    row = {"strain": "REF-TEST", "bgc_id": "BGC001", "gene": "gene_1",
           "aa_length": "100", "subject_acc": "WP_SYNTHETIC.1",
           "subject_organism": "Synthetic comparator", "pct_identity": "60",
           "query_coverage": "95"}
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        writer.writeheader()
        if rows:
            writer.writerow(row)
    return path


def test_wrong_layout_retries_leave_package_unchanged_then_valid_source_succeeds(tmp_path):
    pkg = package(tmp_path)
    trove = tmp_path / "trove"
    (trove / "REF-TEST" / "gap_panel").mkdir(parents=True)
    before = snapshot(pkg)
    for rekey in (False, True, False):
        result = ingest_blastp_trove(pkg, trove, "clustered_nr", rekey_by_locus=rekey)
        assert result["status"] == "NO_SOURCES_DISCOVERED"
        assert result["receipt"] is None and result["quarantine"] is None
        assert result["discovery"]["skipped_directory_count"] == 1
        assert result["discovery"]["skipped_directory_sample"] == ["REF-TEST/gap_panel"]
        assert snapshot(pkg) == before
    source(trove)
    result = ingest_blastp_trove(pkg, trove, "clustered_nr", rekey_by_locus=True)
    assert result["genes"] == 1
    assert Path(result["receipt"]).is_file()


def test_empty_root_and_old_empty_receipt_are_not_mutated(tmp_path):
    pkg = package(tmp_path)
    trove = tmp_path / "empty"
    trove.mkdir()
    receipt = pkg / "blastp_ingest_receipts" / "historical_empty_receipt.json"
    receipt.parent.mkdir()
    receipt.write_text('{"sources": [], "admitted_total": 0}\n')
    before = snapshot(pkg)
    result = ingest_blastp_trove(pkg, trove, "nr", rekey_by_locus=True)
    assert result["status"] == "NO_SOURCES_DISCOVERED"
    assert result["discovery"]["scanned_directories"] == []
    assert snapshot(pkg) == before


def test_header_only_discovered_source_still_gets_receipt(tmp_path):
    pkg = package(tmp_path)
    trove = tmp_path / "trove"
    path = source(trove, rows=False)
    result = ingest_blastp_trove(pkg, trove, "nr")
    receipt = json.loads(Path(result["receipt"]).read_text())
    assert receipt["sources"][0]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert receipt["admitted_total"] == 0


def test_no_matching_channel_files_explained_and_sample_bounded(tmp_path):
    pkg = package(tmp_path)
    trove = tmp_path / "trove"
    for i in range(12):
        (trove / "REF-TEST" / f"panel_{i:02d}").mkdir(parents=True)
    (trove / "REF-TEST" / "BGC001").mkdir()
    result = ingest_blastp_trove(pkg, trove, "nr")
    discovery = result["discovery"]
    assert discovery["skipped_directory_count"] == 12
    assert len(discovery["skipped_directory_sample"]) == 10
    assert discovery["bgc_directories_without_matching_files"] == 1
    assert discovery["accepted_filenames"]


def test_cli_explains_noop_without_success_shaped_output(tmp_path):
    pkg = package(tmp_path)
    trove = tmp_path / "trove"
    (trove / "REF-TEST" / "gap_panel").mkdir(parents=True)
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run([sys.executable, str(root / "mamey_run.py"), "ingest-blastp-trove",
                           "--package", str(pkg), "--trove", str(trove),
                           "--channel", "clustered_nr"], cwd=root, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "NO_SOURCES_DISCOVERED" in proc.stdout
    assert "ingest_blastp_rollups.py" in proc.stdout
    assert str(trove.resolve()) in proc.stdout
    assert "0 BGCs, 0 genes" not in proc.stdout


def test_nonempty_receipt_collision_remains_an_error(tmp_path):
    pkg = package(tmp_path)
    trove = tmp_path / "trove"
    source(trove)
    result = ingest_blastp_trove(pkg, trove, "nr")
    receipt = Path(result["receipt"])
    receipt.write_text('{"tampered": true}\n')
    with pytest.raises(ValueError, match="immutable BLASTP receipt collision"):
        ingest_blastp_trove(pkg, trove, "nr")
