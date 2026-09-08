"""AMBER_04 (v9.7.349): tests for the marker-BLAST comparator-discovery pure core
(tools/marker_candidate_search.py).

No network, no BLAST, no downloads (those are approval-gated and only PLANNED). What IS
tested is the offline core: accession extraction from messy BLAST subject ids, outfmt6
parsing, and hits->candidates (bitscore ranking, per-genome dedup, self-hit drop,
min-pident filter, max-hits cap, and the build_phylo_panel selection_basis).
"""
import os
import csv
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_M = os.path.join(ROOT, "tools", "marker_candidate_search.py")
spec = importlib.util.spec_from_file_location("marker_candidate_search", _M)
mcs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcs)


def test_accession_from_subject_handles_common_forms():
    assert mcs.accession_from_subject("ref|NZ_CP012345.1|") == "NZ_CP012345.1"
    assert mcs.accession_from_subject("gi|123|ref|NR_074327.1|") == "NR_074327.1"
    assert mcs.accession_from_subject("GCF_000009565.1") == "GCF_000009565.1"


def _hits_file(tmp_path, rows):
    p = tmp_path / "hits.tsv"
    with open(p, "w") as fh:
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")
    return str(p)


def test_parse_and_rank_dedup_and_cap(tmp_path):
    # cols: qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore
    rows = [
        ["AS-1_rpoB", "ref|NZ_A.1|", 98.0, 300, 0, 0, 1, 300, 1, 300, "0", 600],
        ["AS-1_rpoB", "ref|NZ_A.1|", 97.0, 280, 0, 0, 1, 280, 1, 280, "0", 550],  # dup genome
        ["AS-1_rpoB", "ref|NZ_B.1|", 95.0, 300, 0, 0, 1, 300, 1, 300, "0", 500],
        ["AS-1_rpoB", "ref|NZ_C.1|", 90.0, 300, 0, 0, 1, 300, 1, 300, "0", 400],
    ]
    hits = mcs.parse_outfmt6(_hits_file(tmp_path, rows))
    cands = mcs.hits_to_candidates(hits, query="AS-1", marker="rpoB", max_hits=2)
    ids = [c["candidate_id"] for c in cands]
    assert ids == ["NZ_A.1", "NZ_B.1"]                 # bitscore order, deduped, capped at 2
    assert cands[0]["selection_basis"] == "marker_blast_rpoB"
    assert cands[0]["related_query_ids"] == "AS-1"
    assert cands[0]["role"] == "REFERENCE"


def test_min_pident_filters(tmp_path):
    rows = [
        ["q", "ref|NZ_A.1|", 99.0, 300, 0, 0, 1, 300, 1, 300, "0", 600],
        ["q", "ref|NZ_B.1|", 80.0, 300, 0, 0, 1, 300, 1, 300, "0", 500],
    ]
    hits = mcs.parse_outfmt6(_hits_file(tmp_path, rows))
    cands = mcs.hits_to_candidates(hits, query="q", marker="16S", min_pident=90.0)
    assert [c["candidate_id"] for c in cands] == ["NZ_A.1"]


def test_self_hit_is_never_a_candidate(tmp_path):
    rows = [["AS-99", "AS-99_contig1", 100.0, 300, 0, 0, 1, 300, 1, 300, "0", 700],
            ["AS-99", "ref|NZ_X.1|", 96.0, 300, 0, 0, 1, 300, 1, 300, "0", 600]]
    hits = mcs.parse_outfmt6(_hits_file(tmp_path, rows))
    cands = mcs.hits_to_candidates(hits, query="AS-99", marker="rpoB")
    assert [c["candidate_id"] for c in cands] == ["NZ_X.1"]   # self dropped


def test_write_panel_has_query_and_columns(tmp_path):
    cands = mcs.hits_to_candidates(
        mcs.parse_outfmt6(_hits_file(tmp_path, [
            ["q", "ref|NZ_A.1|", 98.0, 300, 0, 0, 1, 300, 1, 300, "0", 600]])),
        query="AS-5", marker="rpoB")
    out = tmp_path / "panel.tsv"
    mcs.write_panel(cands, str(out), query="AS-5")
    rows = list(csv.DictReader(open(out), delimiter="\t"))
    assert list(rows[0].keys()) == mcs.PANEL_COLS
    assert rows[0]["candidate_id"] == "AS-5" and rows[0]["role"] == "QUERY"
    assert rows[1]["role"] == "REFERENCE" and rows[1]["selection_basis"] == "marker_blast_rpoB"


def test_help_and_seeds_present():
    # protein markers reuse the shipped MLSA seeds
    for m in ("rpoB", "gyrB"):
        assert os.path.isfile(os.path.join(mcs.SEEDS_DIR, mcs.MARKER_SEEDS[m]))
