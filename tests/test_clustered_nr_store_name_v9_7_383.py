"""v9.7.383: one canonical ClusteredNR store name with legacy read compatibility."""
from __future__ import annotations

import csv
from pathlib import Path

from mamey import blastp_ingest
from mamey import compile_report
from mamey import modeb_subsections
from mamey import roster_v2
from mamey import widget_deliverable


FIELDS = [
    "strain", "bgc_id", "gene", "aa_length", "hit_rank", "subject_acc",
    "subject_organism", "subject_def", "pct_identity", "pct_positives",
    "query_coverage", "evalue", "bitscore", "channel",
]


def _write_hit(path: Path, *, gene: str, subject: str, pid: str = "71",
               bgc: str = "BGC001") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow({
            "strain": "TEST-1", "bgc_id": bgc, "gene": gene,
            "aa_length": "300", "hit_rank": "1", "subject_acc": subject,
            "subject_organism": "Reference bacterium", "subject_def": subject,
            "pct_identity": pid, "pct_positives": "80", "query_coverage": "99",
            "evalue": "1e-50", "bitscore": "250", "channel": "clustered_nr",
        })


def test_new_clustered_nr_writes_use_canonical_explicit_name():
    assert blastp_ingest.CHANNEL_STORE["clustered_nr"] == "blastp_clustered_nr"


def test_roster_reads_canonical_and_legacy_and_canonical_wins(tmp_path: Path):
    _write_hit(tmp_path / "blastp_clustered_nr" / "BGC001_top10.csv",
               gene="ctg1_1", subject="CANONICAL")
    _write_hit(tmp_path / "blastp_cluster_nr" / "BGC001_top10.csv",
               gene="ctg1_1", subject="LEGACY_DUPLICATE", pid="99")
    _write_hit(tmp_path / "blastp_cluster_nr" / "BGC002_top10.csv",
               gene="ctg1_2", subject="LEGACY_ONLY", bgc="BGC002")

    rows = roster_v2._read_channel_store(tmp_path, "clustered_nr")
    assert rows[("BGC001", "ctg1_1")]["subject_acc"] == "CANONICAL"
    assert rows[("BGC002", "ctg1_2")]["subject_acc"] == "LEGACY_ONLY"


def test_modeb_subsection_reads_legacy_store(tmp_path: Path):
    _write_hit(tmp_path / "blastp_cluster_nr" / "BGC001_top10.csv",
               gene="ctg1_1", subject="LEGACY_ONLY")
    text = modeb_subsections.blastp_channel_evidence(tmp_path, "BGC001")
    assert "clustered-nr" in text
    assert "LEGACY_ONLY" in text
    assert "blastp_clustered_nr/" in text


def test_compiled_report_prefers_canonical_when_both_exist(tmp_path: Path):
    _write_hit(tmp_path / "blastp_clustered_nr" / "BGC001_top10.csv",
               gene="ctg1_1", subject="CANONICAL")
    _write_hit(tmp_path / "blastp_cluster_nr" / "BGC001_top10.csv",
               gene="ctg1_1", subject="LEGACY_DUPLICATE", pid="99")
    text = compile_report._blastp_from_channel_stores(tmp_path)
    assert "clustered_nr" in text
    assert "CANONICAL" in text
    assert "LEGACY_DUPLICATE" not in text


def test_widget_declares_canonical_then_legacy_read_order():
    assert widget_deliverable._BLASTP_CHANNEL_DIRS["clustered_nr"] == (
        "blastp_clustered_nr", "blastp_cluster_nr"
    )
