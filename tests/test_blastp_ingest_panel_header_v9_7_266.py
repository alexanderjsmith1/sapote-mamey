"""v9.7.266 — regression guard for the ingest parsing the *current* bgc-blastp-panel header format.

The panel emits FASTA headers like
  S_avermitilis|BGC042|slot=1|role=core|gene=ctg1_5461|node=BA000030.4|region=region042|coords=...|aa=590|reason=siderophore
and NCBI web BLASTp returns that whole string verbatim as the query id in both the Hit Table CSV
(column 1) and the XML2 query-title. Earlier ingest code expected a different header shape; this pins
that parse_bgc_id / parse_short_contig / build_b5_rows handle the pipe-delimited panel format and key
each hit to the right BGC. Reproduced from real returned files (RID 558R3023014)."""
import csv
from pathlib import Path
from mamey.blastp_ingest import parse_bgc_id, parse_short_contig, build_b5_rows

PANEL_QUERIES = [
    "S_avermitilis|BGC042|slot=1|role=core|gene=ctg1_5461|node=BA000030.4|region=region042|coords=6383181-6384953|aa=590|reason=siderophore",
    "S_amethystogenes|BGC008|slot=1|role=core|gene=ctg1_685|node=JBHTEE010000001.1|region=region008|coords=784412-787048|aa=878|reason=lanthipeptide",
    "S_amethystogenes|BGC008|slot=3|role=core|gene=ctg1_682|node=JBHTEE010000001.1|region=region008|coords=783914-784045|aa=43|reason=lanthipeptide",
]


def test_parse_bgc_and_contig_off_pipe_delimited_panel_header():
    assert parse_bgc_id(PANEL_QUERIES[0]) == "BGC042"
    assert parse_bgc_id(PANEL_QUERIES[1]) == "BGC008"
    assert parse_short_contig(PANEL_QUERIES[0]) == "ctg1"   # from gene=ctg1_5461
    assert parse_short_contig(PANEL_QUERIES[2]) == "ctg1"


def test_build_b5_rows_keys_hits_to_the_right_bgc(tmp_path):
    # a tiny two-query hit-table in NCBI -outfmt 10 shape with the panel header as query id
    csv_path = tmp_path / "hits.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        # query, subject, pid, alnlen, mm, gap, qs, qe, ss, se, evalue, bits
        w.writerow([PANEL_QUERIES[0], "WP_406477488.1", "90.816", "588", "54", "0", "1", "588", "1", "588", "0.0", "1110"])
        w.writerow([PANEL_QUERIES[1], "WP_364215112.1", "98.521", "878", "13", "0", "1", "878", "1", "878", "0.0", "1723"])
    rows = build_b5_rows("S_mixed", csv_path)
    bgcs = {r.get("BGC_ID") for r in rows}
    assert "BGC042" in bgcs and "BGC008" in bgcs   # both keyed correctly off the panel header
    # the panel header must not smear one query's BGC onto the other
    by_q = {}
    for r in rows:
        by_q.setdefault(r.get("BGC_ID"), set()).add(r.get("subject_acc") or r.get("Subject_acc"))
    assert "BGC042" in by_q and "BGC008" in by_q
