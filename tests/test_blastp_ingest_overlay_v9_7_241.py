"""Regression tests for the v9.7.241 patch set — `ingest-blastp` overlay + B5 append.

v9.7.239 added `ingest-blastp --package`, which mirrors ingested nr hits into
`<package>/blastp_online/<BGC>_online_blastp.csv` so that `authored_verify` and
`genome_explore` can compute `conservation_median_id` from nr rather than falling back
to ClusterBlast. Three defects in that write path, all observed on a real 35-round
AS-421 BLASTp campaign (1,002 query genes across 46 BGCs):

  P7a  write_nr_overlay() opened the per-BGC CSV with mode "w", so each round TRUNCATED
       the previous round's file. The documented workflow splits a strain into rounds
       (`bgc-blastp-panel` emits one FASTA per round; NCBI returns one Hit Table per
       round), so a campaign calls `ingest-blastp` once per round. Last round wins.
       Measured: 557 of 1,002 genes retained; BGC017 kept 23 of 48, dropping its
       4,071 aa megasynthase `ctg2_360` entirely.

  P7b  The overlay's `antismash_domains` column was hardcoded to "". Therefore
       `reconcile("", hit_def)` could only ever return REVIEW, and the `agreement`
       column was a constant rather than a reconciliation. The sealed package already
       carries the domains in `*_gene_context.jsonl`; join on the panel defline's
       `gene=` token.

  P7c  B5_BLASTp_Hits append was not idempotent. Re-ingesting the same Hit Table
       duplicated every row (150 -> 300 -> 450 on a real round). A 35-round campaign
       re-run after a partial failure silently doubled the sheet, and nothing
       downstream deduplicates.

Hermetic: no network, no NCBI, no antiSMASH ZIP. Fixtures are the minimum each unit
reads.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _pkg(tmp_path: Path) -> Path:
    pkg = tmp_path / "package"
    pkg.mkdir()
    gc = pkg / "AS-421_gene_context.jsonl"
    gc.write_text(
        json.dumps({"bgc_id": "BGC017", "cds": [
            {"locus_tag": "ctg2_360", "sec_met_domains": ["AMP-binding", "Condensation", "PCP"]},
            {"locus_tag": "ctg2_359", "sec_met_domains": ["Beta-lactamase"]},
            {"locus_tag": "ctg2_347", "sec_met_domains": []},
        ]}) + "\n"
        + json.dumps({"bgc_id": "BGC028", "cds": [
            {"locus_tag": "ctg4_197", "sec_met_domains": ["PKS_KS", "Ketoacyl-synt_C"]},
        ]}) + "\n",
        encoding="utf-8",
    )
    return pkg


def _row(bgc, gene, aa, acc, desc, pid, bits="500", rank="1", qs="1", qe="100"):
    """A B5 row as build_b5_rows() emits it."""
    return {
        "strain": "AS-421", "BGC_ID": bgc, "contig": gene.split("_")[0],
        "query_locus": f"AS-421|{bgc}|slot=1|role=core|gene={gene}|aa={aa}|reason=x",
        "query_len": "", "hit_rank": rank, "subject_acc": acc, "subject_desc": desc,
        "sciname": "Streptosporangium saharense", "pct_identity": pid,
        "positives_pct": "", "align_len": "100", "mismatches": "", "gap_opens": "",
        "q_start": qs, "q_end": qe, "s_start": "1", "s_end": "100",
        "evalue": "0.0", "bitscore": bits, "subject_len": "", "source": "nr", "ingest_date": "",
    }


def _overlay(pkg: Path, bgc: str) -> list[dict]:
    return list(csv.DictReader((pkg / "blastp_online" / f"{bgc}_online_blastp.csv").open()))


# ---------------------------------------------------------------------------
# P7a — the overlay must MERGE across rounds, not truncate
# ---------------------------------------------------------------------------

def test_p7a_overlay_merges_across_rounds(tmp_path):
    """Round 2 must not erase round 1. This is the AS-421 defect exactly."""
    from mamey.blastp_ingest import write_nr_overlay
    pkg = _pkg(tmp_path)

    r1 = write_nr_overlay(pkg, [_row("BGC017", "ctg2_347", 386, "WP_1", "MppP", "97.9")])
    assert r1["genes"] == 1

    r2 = write_nr_overlay(pkg, [_row("BGC017", "ctg2_360", 4071, "WP_2", "NRPS", "96.5")])
    assert r2["genes"] == 2, "round 2 must merge with round 1, not replace it"

    got = {x["locus_tag"] for x in _overlay(pkg, "BGC017")}
    assert got == {"ctg2_347", "ctg2_360"}, got


def test_p7a_higher_bitscore_wins_on_collision(tmp_path):
    from mamey.blastp_ingest import write_nr_overlay
    pkg = _pkg(tmp_path)
    write_nr_overlay(pkg, [_row("BGC017", "ctg2_360", 4071, "WP_LOW", "old", "50.0", bits="100")])
    write_nr_overlay(pkg, [_row("BGC017", "ctg2_360", 4071, "WP_HIGH", "new", "96.5", bits="7714")])
    rows = _overlay(pkg, "BGC017")
    assert len(rows) == 1
    assert rows[0]["blastp_accession"] == "WP_HIGH"


def test_p7a_a_later_round_does_not_lose_a_different_bgc(tmp_path):
    from mamey.blastp_ingest import write_nr_overlay
    pkg = _pkg(tmp_path)
    write_nr_overlay(pkg, [_row("BGC017", "ctg2_347", 386, "WP_1", "MppP", "97.9")])
    write_nr_overlay(pkg, [_row("BGC028", "ctg4_197", 423, "WP_3", "KS", "97.6")])
    assert len(_overlay(pkg, "BGC017")) == 1
    assert len(_overlay(pkg, "BGC028")) == 1


def test_p7a_only_rank_1_hits_enter_the_overlay(tmp_path):
    from mamey.blastp_ingest import write_nr_overlay
    pkg = _pkg(tmp_path)
    write_nr_overlay(pkg, [
        _row("BGC017", "ctg2_360", 4071, "WP_A", "best", "96.5", rank="1"),
        _row("BGC017", "ctg2_360", 4071, "WP_B", "second", "75.6", rank="2"),
    ])
    rows = _overlay(pkg, "BGC017")
    assert len(rows) == 1 and rows[0]["blastp_accession"] == "WP_A"


# ---------------------------------------------------------------------------
# P7b — antismash_domains must be backfilled, so `agreement` is a real call
# ---------------------------------------------------------------------------

def test_p7b_domains_backfilled_from_gene_context(tmp_path):
    from mamey.blastp_ingest import write_nr_overlay
    pkg = _pkg(tmp_path)
    write_nr_overlay(pkg, [
        _row("BGC017", "ctg2_360", 4071, "WP_2",
             "amino acid adenylation domain-containing protein [Streptosporangium saharense]", "96.5"),
        _row("BGC017", "ctg2_359", 445, "WP_9",
             "serine hydrolase domain-containing protein [Streptosporangium saharense]", "95.5"),
    ])
    by = {x["locus_tag"]: x for x in _overlay(pkg, "BGC017")}
    assert by["ctg2_360"]["antismash_domains"] == "AMP-binding; Condensation; PCP"
    assert by["ctg2_359"]["antismash_domains"] == "Beta-lactamase"


def test_p7b_agreement_is_a_reconciliation_not_a_constant(tmp_path):
    """Pre-patch, `agreement` was "" on every row because domains were "".
    reconcile("", hit_def) can only return REVIEW."""
    from mamey.blastp_ingest import write_nr_overlay
    pkg = _pkg(tmp_path)
    write_nr_overlay(pkg, [
        # domain token 'condensation' appears in the hit definition -> CONFIRM
        _row("BGC017", "ctg2_360", 4071, "WP_2", "condensation domain-containing protein", "96.5"),
        # no shared >=4-char token -> REVIEW
        _row("BGC017", "ctg2_359", 445, "WP_9", "serine hydrolase domain-containing protein", "95.5"),
        # gene with no domains at all -> REVIEW (not a crash, not CONFIRM)
        _row("BGC017", "ctg2_347", 386, "WP_1", "enduracididine biosynthesis enzyme MppP", "97.9"),
    ])
    by = {x["locus_tag"]: x["agreement"] for x in _overlay(pkg, "BGC017")}
    assert by["ctg2_360"] == "CONFIRM"
    assert by["ctg2_359"] == "REVIEW"
    assert by["ctg2_347"] == "REVIEW"


def test_p7b_missing_gene_context_is_fail_open(tmp_path):
    """No gene_context.jsonl: the column stays blank, nothing raises."""
    from mamey.blastp_ingest import write_nr_overlay
    pkg = tmp_path / "bare"
    pkg.mkdir()
    write_nr_overlay(pkg, [_row("BGC017", "ctg2_360", 4071, "WP_2", "some protein", "96.5")])
    rows = _overlay(pkg, "BGC017")
    assert rows[0]["antismash_domains"] == ""


# ---------------------------------------------------------------------------
# P7c — B5 append must be idempotent
# ---------------------------------------------------------------------------

def _master(tmp_path: Path) -> Path:
    from mamey.master_workbook import CANONICAL_V1_HEADERS
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "B5_BLASTp_Hits"
    ws.append(CANONICAL_V1_HEADERS["B5_BLASTp_Hits"])
    p = tmp_path / "master.xlsx"
    wb.save(p)
    return p


def _hit_table(tmp_path: Path, name="hits.csv") -> Path:
    """Headerless NCBI -outfmt 10 Hit Table, 13 columns."""
    q = "AS-421|BGC017|slot=1|role=core|gene=ctg2_347|aa=386|reason=x"
    p = tmp_path / name
    p.write_text(
        f"{q},WP_1.1,97.927,386,8,0,1,386,1,386,0.0,780,98.4\n"
        f"{q},WP_2.1,80.000,386,77,0,1,386,1,386,1e-90,600,85.0\n",
        encoding="utf-8",
    )
    return p


def test_p7c_reingesting_the_same_hit_table_is_a_no_op(tmp_path):
    from mamey.blastp_ingest import ingest_blastp
    m, ht = _master(tmp_path), _hit_table(tmp_path)

    first = ingest_blastp(m, "AS-421", ht, top_n=5)
    assert first["rows"] == 2
    assert first.get("duplicates_skipped", 0) == 0

    second = ingest_blastp(m, "AS-421", ht, top_n=5)
    assert second["rows"] == 0, "re-ingesting the same table must append nothing"
    assert second["duplicates_skipped"] == 2

    ws = openpyxl.load_workbook(m, read_only=True)["B5_BLASTp_Hits"]
    assert ws.max_row == 3, f"header + 2 rows, got {ws.max_row}"


def test_p7c_a_distinct_hit_table_still_appends(tmp_path):
    """Dedupe must not blind B5 to genuinely new rounds."""
    from mamey.blastp_ingest import ingest_blastp
    m = _master(tmp_path)
    ht1 = _hit_table(tmp_path, "r1.csv")
    q2 = "AS-421|BGC017|slot=2|role=core|gene=ctg2_360|aa=4071|reason=x"
    ht2 = tmp_path / "r2.csv"
    ht2.write_text(f"{q2},WP_9.1,96.491,4075,140,3,1,4071,1,4075,0.0,7714,97.2\n", encoding="utf-8")

    ingest_blastp(m, "AS-421", ht1, top_n=5)
    out = ingest_blastp(m, "AS-421", ht2, top_n=5)
    assert out["rows"] == 1 and out["duplicates_skipped"] == 0
    ws = openpyxl.load_workbook(m, read_only=True)["B5_BLASTp_Hits"]
    assert ws.max_row == 4


def test_p7c_headerless_or_odd_sheet_falls_back_to_append(tmp_path):
    """Fail-open: an unreadable B5 must not drop rows."""
    from mamey.blastp_ingest import _existing_b5_keys
    wb = openpyxl.Workbook()
    ws = wb.active
    assert _existing_b5_keys(ws) == set()          # empty sheet
    ws.append(["not", "the", "b5", "header"])
    assert _existing_b5_keys(ws) == set()          # header without the key columns
