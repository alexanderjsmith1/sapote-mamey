"""v9.7.416 — the dated BLASTp master rollup must MERGE, not replace.

`deliverable_tools/ingest_blastp.py` writes two homes. The per-BGC repository home always merged
(`load_existing`, honouring the file's own stated invariant: "new rows replace existing rows for
the SAME gene; every other gene in the BGC is preserved untouched"). The dated master rollup was
labelled `# ---- write master rollup (dated, additive) ----` but opened with mode "w" and wrote
only the current batch, so a SECOND ingest on the SAME DAY for the same strain+channel replaced
the first batch instead of adding to it. Separate dates were never at risk — they are separate
directories.

This matters downstream: `deliverable_tools/roster_v2.py` reads exactly these files
(`{ROOT}/strain_data/{strain}/blastp_nr_*/*_nr_top_hit_per_gene_*.csv`), and its `all_strains()`
derives the roster itself from that glob. A truncated rollup silently narrows the per-gene nr
evidence a roster is built on — a denominator that shrinks with no error anywhere.

The module is top-level script code with a `main()`, so this drives it as a subprocess against a
tmp fixture (the convention in test_fair_cohort_analysis_no_dated_glob_v97397.py). Strain IDs are
synthetic and runtime-constructed. No biological claim is made or admitted here.
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys

STRAIN = "AS-" + str(9000 + 16)
DATE = "2026-09-08"
SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "deliverable_tools", "ingest_blastp.py")


def _hittable(path, query, acc):
    """One NCBI HitTable row: col0 query title, col1 subject, col2 %id, col3 aln, col10 E, col11 bits."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([query, acc, "62.5", "310", "0", "0", "1", "310", "1", "310",
                    "1e-90", "300", "74.1"])


def _run(tmp_path, base, query, acc):
    raw = os.path.join(str(tmp_path), "BLASTp Repository", "_raw")
    os.makedirs(raw, exist_ok=True)
    for stale in os.listdir(raw):
        if stale.endswith("-Alignment-HitTable.csv"):
            os.remove(os.path.join(raw, stale))
    strain, alias, gene = query.split("__")
    query = f"{strain}__NODE_1_length_10000_cov_10__region001__{alias}__{gene}"
    _hittable(os.path.join(raw, base + "-Alignment-HitTable.csv"), query, acc)
    out = subprocess.run(
        [sys.executable, SCRIPT,
         "--raw", raw,
         "--repo", os.path.join(str(tmp_path), "BLASTp Repository"),
         "--master", os.path.join(str(tmp_path), "strain_data"),
         "--channel", "nr", "--date", DATE],
        capture_output=True, text=True, cwd=str(tmp_path))
    assert out.returncode == 0, out.stdout + out.stderr
    return out


def _rollup_rows(tmp_path, name):
    p = os.path.join(str(tmp_path), "strain_data", STRAIN, f"blastp_nr_{DATE}",
                     f"{STRAIN}_nr_{name}_{DATE}.csv")
    assert os.path.exists(p), f"rollup not written: {p}"
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def test_second_same_day_ingest_keeps_the_first_batch(tmp_path):
    """Two ingests, same strain, same channel, same date, different BGCs — both must survive."""
    _run(tmp_path, "b1", f"{STRAIN}__BGC001__geneA", "WP_000000001.1")
    assert {r["bgc_id"] for r in _rollup_rows(tmp_path, "top_hit_per_gene")} == {"BGC001"}

    _run(tmp_path, "b2", f"{STRAIN}__BGC002__geneB", "WP_000000002.1")
    rows = _rollup_rows(tmp_path, "top_hit_per_gene")
    assert {r["bgc_id"] for r in rows} == {"BGC001", "BGC002"}, (
        "the second same-day ingest replaced the first batch instead of merging into it; "
        f"rollup holds only {sorted({r['bgc_id'] for r in rows})}"
    )
    assert {(r["bgc_id"], r["gene"]) for r in rows} == {("BGC001", "geneA"), ("BGC002", "geneB")}


def test_top10_rollup_merges_too(tmp_path):
    """The top10 sibling is the same file family and must not silently drop the earlier batch."""
    _run(tmp_path, "b1", f"{STRAIN}__BGC001__geneA", "WP_000000001.1")
    _run(tmp_path, "b2", f"{STRAIN}__BGC002__geneB", "WP_000000002.1")
    assert {r["bgc_id"] for r in _rollup_rows(tmp_path, "top10")} == {"BGC001", "BGC002"}


def test_re_ingesting_the_same_gene_replaces_only_that_gene(tmp_path):
    """Merge semantics must match the repository home: same gene replaced, siblings untouched."""
    _run(tmp_path, "b1", f"{STRAIN}__BGC001__geneA", "WP_000000001.1")
    _run(tmp_path, "b2", f"{STRAIN}__BGC001__geneB", "WP_000000002.1")
    _run(tmp_path, "b3", f"{STRAIN}__BGC001__geneA", "WP_000000009.9")
    rows = _rollup_rows(tmp_path, "top_hit_per_gene")
    by_gene = {r["gene"]: r for r in rows}
    assert set(by_gene) == {"geneA", "geneB"}, "a sibling gene was clobbered by a same-gene re-ingest"
    assert by_gene["geneA"]["subject_acc"] == "WP_000000009.9", "the re-ingested gene was not replaced"
    assert by_gene["geneB"]["subject_acc"] == "WP_000000002.1"


def test_rollup_comment_and_code_agree():
    """The block comment claimed 'additive' while the writer truncated. Keep them honest."""
    src = open(SCRIPT, encoding="utf-8").read()
    assert "load_existing_roll(" in src, "rollup no longer merges existing rows"
    assert "(dated, additive)" not in src, (
        "the rollup block still calls itself 'additive'; either merge or stop claiming it")
