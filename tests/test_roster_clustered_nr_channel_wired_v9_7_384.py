"""v9.7.384: build_gene_roster() must surface the clustered_nr channel.

Regression guard for a wiring gap in the sealed .383 base: roster_v2 defined
_CHANNEL_STORES["clustered_nr"] and _read_channel_store() handled it, but the
public build_gene_roster() only read nr/swissprot/ebi — so a package's
ClusteredNR store was invisible in every roster model's channels_present and
per-gene channels, under either store-name spelling.

Fail-before / pass-after: on the sealed base the two assertions below fail
(channels_present lacks 'clustered_nr'; the clustered_nr-only gene never
appears because build_gene_roster's gene-set union omitted the cnr store).
"""
from __future__ import annotations

import csv
from pathlib import Path

from mamey import roster_v2


FIELDS = [
    "strain", "bgc_id", "gene", "aa_length", "hit_rank", "subject_acc",
    "subject_organism", "subject_def", "pct_identity", "pct_positives",
    "query_coverage", "evalue", "bitscore", "channel",
]


def _write_hit(path: Path, *, gene: str, subject: str, pid: str,
               bgc: str, channel: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow({
            "strain": "TEST-1", "bgc_id": bgc, "gene": gene,
            "aa_length": "300", "hit_rank": "1", "subject_acc": subject,
            "subject_organism": "Reference bacterium", "subject_def": subject,
            "pct_identity": pid, "pct_positives": "80", "query_coverage": "99",
            "evalue": "1e-50", "bitscore": "250", "channel": channel,
        })


def test_clustered_nr_channel_is_surfaced_in_roster(tmp_path: Path):
    # A package whose ONLY per-gene homology evidence is a ClusteredNR store
    # (canonical spelling). Nothing in nr/swissprot/ebi/locus_maps.
    _write_hit(tmp_path / "blastp_clustered_nr" / "BGC001_top10.csv",
               gene="ctg1_1", subject="CLUSTERED_HIT", pid="73",
               bgc="BGC001", channel="clustered_nr")

    model = roster_v2.build_gene_roster(tmp_path, strain_id="TEST-1")

    # 1. the channel must be advertised at the model level
    assert "clustered_nr" in model["channels_present"], model["channels_present"]

    # 2. the clustered_nr-only gene must appear, with its channel populated
    genes = [g for b in model["bgcs"] for g in b["genes"]]
    assert genes, "clustered_nr-only gene did not surface in the roster"
    cnr = genes[0]["channels"].get("clustered_nr")
    assert cnr and cnr["pid"] == 73.0, genes[0]["channels"]


def test_legacy_cluster_nr_spelling_also_surfaces(tmp_path: Path):
    # The legacy store-name spelling must reach the roster too (interop).
    _write_hit(tmp_path / "blastp_cluster_nr" / "BGC001_top10.csv",
               gene="ctg1_1", subject="LEGACY_HIT", pid="66",
               bgc="BGC001", channel="clustered_nr")

    model = roster_v2.build_gene_roster(tmp_path, strain_id="TEST-1")
    assert "clustered_nr" in model["channels_present"], model["channels_present"]


def test_nr_and_clustered_nr_are_independent_channels(tmp_path: Path):
    # nr and clustered_nr must be reported as SEPARATE channels, not merged.
    _write_hit(tmp_path / "blastp_nr" / "BGC001_top10.csv",
               gene="ctg1_1", subject="NR_HIT", pid="80",
               bgc="BGC001", channel="nr")
    _write_hit(tmp_path / "blastp_clustered_nr" / "BGC001_top10.csv",
               gene="ctg1_1", subject="CLUSTERED_HIT", pid="73",
               bgc="BGC001", channel="clustered_nr")

    model = roster_v2.build_gene_roster(tmp_path, strain_id="TEST-1")
    present = model["channels_present"]
    assert "nr" in present and "clustered_nr" in present, present
    ch = [g for b in model["bgcs"] for g in b["genes"]][0]["channels"]
    assert ch["nr"]["pid"] == 80.0 and ch["clustered_nr"]["pid"] == 73.0, ch
