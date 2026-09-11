#!/usr/bin/env python3
"""verify_blastp.py — the per-gene BLASTp verify gate (SKILL.md / references/blastp.md).

Why this exists (real failure): the async harness once had two writers to one results path;
a status `poll` (HTML/QBlastInfo stub) silently overwrote real hits from an XML `fetch`, and
nothing checked that a results file had rows — so cards cited numbers whose on-disk artifact
was a 62-byte stub. This gate asserts the artifact-of-record is real BEFORE anything cites it.

It exits NONZERO on:
  HTML_STUB  — a results file is an NCBI HTML / QBlastInfo error stub, not a HitTable
  EMPTY      — a results file parses to zero real hit rows
  MISSING    — an --expect gene has no hit at all
  PARTIAL    — only some of the --expect genes are covered

Reuses the pipeline's OWN stub-guard (mamey.blastp_ingest.parse_hit_table), so "real rows"
means exactly what ingest means by it — no second, drifting definition.

Usage:
  # one combined -outfmt 10 / pipe-query HitTable:
  python scripts/verify_blastp.py --hit-table AS-XXX_wave2_blastp_hittable.csv
  # a directory of per-gene result CSVs:
  python scripts/verify_blastp.py --results-dir path/to/csvs/
  # assert coverage of an expected gene set (query ids or a FASTA of them):
  python scripts/verify_blastp.py --hit-table ht.csv --expect ctg10_68,ctg11_3
  python scripts/verify_blastp.py --hit-table ht.csv --expect-fasta cores.faa

Exit 0 = PASS (green gate — the precondition for a BLASTp claim). Nonzero = FAIL.
"""
from __future__ import annotations
import argparse, csv, os, re, sys
from pathlib import Path

# Force the local mamey/ package to take precedence over any installed/older copy BEFORE
# importing it (mirrors mamey_run.py's shadow guard). A pip-installed mamey may lack
# blastp_ingest or predate its stub-guard; importing that first and only fixing sys.path in
# an except clause is too late — the wrong parent `mamey` is already cached in sys.modules,
# so the retry re-fails and this verify gate breaks on exactly the drift-prone machines it
# is meant to protect.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Use the pipeline's own parser+stub-guard so this gate can never drift from ingest.
from mamey.blastp_ingest import parse_hit_table, parse_bgc_id  # type: ignore

_CTG_RE = re.compile(r"(ctg\d+_\d+)")


def _is_stub(path: Path) -> bool:
    head = path.read_text(encoding="utf-8", errors="replace")[:400].lstrip()
    return head.startswith("<") or "QBlastInfo" in head


def _gene_of(query_id: str) -> str:
    # The gene locus is a ctgN_M token that pipe-query deflines carry as a `gene=ctgN_M`
    # KEY in the middle of the id (…|gene=ctg13_21|node=…|reason=…), not the last field.
    # Extract it explicitly (gene= key, else the ctg token anywhere) before falling back to
    # the last pipe field — otherwise every row collapses to the constant trailing field.
    m_kv = re.search(r"gene=([^|]+)", query_id)
    if m_kv:
        return m_kv.group(1)
    m = _CTG_RE.search(query_id)
    if m:
        return m.group(1)
    if "|" in query_id:
        return query_id.rsplit("|", 1)[-1]
    return query_id


def _load_expect(args) -> set[str]:
    genes: set[str] = set()
    if args.expect:
        genes |= {g.strip() for g in args.expect.split(",") if g.strip()}
    if args.expect_fasta:
        for line in Path(args.expect_fasta).read_text(encoding="utf-8").splitlines():
            if line.startswith(">"):
                genes.add(_gene_of(line[1:].split()[0]))
    return genes


def verify(args) -> tuple[bool, list[str], dict]:
    findings: list[str] = []
    covered: set[str] = set()
    n_rows = 0
    files: list[Path] = []
    if args.hit_table:
        files = [Path(args.hit_table)]
    if args.results_dir:
        files += sorted(Path(args.results_dir).glob("*.csv"))
    if not files:
        return False, ["no --hit-table or --results-dir *.csv supplied"], {}

    for f in files:
        if not f.exists():
            findings.append(f"MISSING: {f} does not exist")
            continue
        if _is_stub(f):
            findings.append(f"HTML_STUB: {f.name} is an HTML/QBlastInfo stub, not a HitTable")
            continue
        rows = parse_hit_table(str(f))  # pipeline's own parser (returns [] for a stub)
        real = [r for r in rows if r.get("subject_acc") and r.get("pct_identity")]
        if not real:
            findings.append(f"EMPTY: {f.name} has zero real hit rows")
            continue
        n_rows += len(real)
        for r in real:
            covered.add(_gene_of(r.get("query_id", "")))

    expect = _load_expect(args)
    if expect:
        missing = sorted(expect - covered)
        if missing:
            frac = len(covered & expect)
            if frac == 0:
                findings.append(f"MISSING: none of the {len(expect)} expected genes have hits")
            else:
                findings.append(f"PARTIAL: {len(missing)}/{len(expect)} expected genes have no hit: {missing[:8]}")

    stats = {"files": len(files), "real_rows": n_rows, "genes_covered": len(covered),
             "expected": len(expect)}
    return (not findings), findings, stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify per-gene BLASTp results are real before citing.")
    ap.add_argument("--hit-table", help="combined -outfmt 10 / pipe-query HitTable CSV")
    ap.add_argument("--results-dir", help="directory of per-gene result CSVs")
    ap.add_argument("--expect", help="comma-separated expected gene ids (coverage check)")
    ap.add_argument("--expect-fasta", help="FASTA whose headers are the expected genes")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    ok, findings, stats = verify(a)
    if a.json:
        import json
        print(json.dumps({"pass": ok, **stats, "findings": findings}, indent=2))
    else:
        print(f"verify_blastp — {'PASS' if ok else 'FAIL'}  "
              f"({stats.get('real_rows',0)} real rows, {stats.get('genes_covered',0)} genes)")
        for f in findings:
            print(f"  \u2717 {f}")
        if ok:
            print("  \u2713 all result files carry real hit rows; no HTML_STUB/EMPTY/MISSING/PARTIAL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
