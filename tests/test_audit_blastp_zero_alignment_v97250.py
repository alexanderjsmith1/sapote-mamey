"""v9.7.250 — tools/audit_blastp_zero_alignment.py, the retrospective half of the P1 fix.

The guard stops NEW zero-alignment batches from being recorded as tested-negatives. Every overlay
BLASTed at `--batch-size > 10` since v9.7.240 may already carry them. This tool finds them.

Two modes, and the difference is the finding:

  --xml       AUTHORITATIVE. BLAST XML2 emits one <Search> per query even when it has no hits, so a
              tested-negative is RECORDED. A batch whose every <Search> has zero <Hit> is a
              zero-alignment batch.
  --overlay   HEURISTIC. An overlay CSV records `agreement=NO_HIT` and nothing more. It cannot
              distinguish "queried, no homolog" from "never came back". It reports SUSPECT, never
              GUILTY.

**Live receipt, real data.** Run against the 36-RID AS-705 evidence archive (2026-07-09, real NCBI nr):

    XML2 audit: 36 file(s), 479 queries, 55 with zero hits.
    No all-zero batches.

Five of those RIDs carried exactly 30 queries and returned 27-28 hits each. So batch-size 30 is not
universally broken -- which is why `MAX_BATCH` was NOT lowered, only the default. And all 55 zero-hit
queries are absent from the sibling HitTable CSVs: **the HitTable ingest path cannot mark a
tested-negative at all.** That gap is recorded, not fixed, here.
"""
from __future__ import annotations
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "audit_blastp_zero_alignment.py"

NS = 'xmlns="http://www.ncbi.nlm.nih.gov"'


def _xml2(searches):
    """searches: list of hit-counts, one per query."""
    body = []
    for n_hits in searches:
        hits = "".join(f"<Hit><num>{i}</num></Hit>" for i in range(n_hits))
        body.append(f"<Search><hits>{hits}</hits></Search>")
    return (f'<?xml version="1.0"?><BlastXML2 {NS}><BlastOutput2><report><Report>'
            f'<results><Results>{"".join(body)}</Results></results>'
            f"</Report></report></BlastOutput2></BlastXML2>")


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def test_all_zero_batch_is_reported_and_exits_1(tmp_path):
    (tmp_path / "bad-Alignment.xml").write_text(_xml2([0, 0, 0, 0]), encoding="utf-8")
    r = _run("--xml", str(tmp_path))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "ZERO-ALIGNMENT BATCHES" in r.stdout
    assert "all 4 queries" in r.stdout
    assert "batch-size 10" in r.stdout


def test_mixed_batch_with_some_zero_hit_queries_is_clean(tmp_path):
    """55 of 479 real queries had zero hits and were genuine negatives. Do not cry wolf."""
    (tmp_path / "ok-Alignment.xml").write_text(_xml2([3, 0, 3, 0, 2]), encoding="utf-8")
    r = _run("--xml", str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "No all-zero batches" in r.stdout
    assert "5 queries, 2 with zero hits" in r.stdout


def test_single_query_with_no_hits_is_not_an_all_zero_batch(tmp_path):
    """A solo giant with no homolog is a real negative."""
    (tmp_path / "solo-Alignment.xml").write_text(_xml2([0]), encoding="utf-8")
    r = _run("--xml", str(tmp_path))
    assert r.returncode == 0, r.stdout


def test_overlay_signature_is_suspect_not_guilty(tmp_path):
    csv = tmp_path / "BGC034_online_blastp.csv"
    hdr = "locus_tag,aa_length,antismash_domains,blastp_top_def,pct_identity,agreement\n"
    rows = ["ctg4_1,300,,SDR family,98.8,CONFIRM\n"]
    rows += [f"ctg4_{i},300,,,,NO_HIT\n" for i in range(2, 14)]      # 12 consecutive
    rows += ["ctg4_14,300,,glycosyltransferase,97.7,CONFIRM\n"]
    csv.write_text(hdr + "".join(rows), encoding="utf-8")
    r = _run("--overlay", str(tmp_path))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "SUSPECT" in r.stdout
    assert "HEURISTIC ONLY" in r.stdout
    assert "cannot distinguish" in r.stdout


def test_overlay_short_run_is_not_suspect(tmp_path):
    csv = tmp_path / "BGC001_online_blastp.csv"
    csv.write_text(
        "locus_tag,aa_length,antismash_domains,blastp_top_def,pct_identity,agreement\n"
        "ctg1_1,300,,SDR family,98.8,CONFIRM\n"
        "ctg1_2,300,,,,NO_HIT\n"
        "ctg1_3,300,,hydrolase,95.0,CONFIRM\n", encoding="utf-8")
    r = _run("--overlay", str(tmp_path))
    assert r.returncode == 0, r.stdout
    assert "No overlay carries the signature" in r.stdout


def test_bad_input_exits_2(tmp_path):
    r = _run("--xml", str(tmp_path))          # empty dir
    assert r.returncode == 2
